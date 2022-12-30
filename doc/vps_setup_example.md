# Stakepool Setup on Ubuntu Bionic

## 1. Preparation

First login to your VPS, replace `vps-ip` with the correct IP address of your server.

	ssh root@vps-ip

Update and upgrade the system, install the dependencies:

	apt-get update && sudo apt-get upgrade
	apt-get install gnupg wget python3 git nginx tmux python3-zmq python3-pip lynx htop nano

The pool should be ran as a user named `stakepooluser`. 
Add user `stakepooluser`.

	useradd stakepooluser
	usermod -aG sudo stakepooluser
	passwd stakepooluser
	su stakepooluser
	
## 2. Installation

Clone the repository and install the prerequisites:

	cd && git clone https://github.com/ghost-coin/ghost-coldstakepool ghost_stakepool
	cd ghost_stakepool
	sudo pip3 install .

### Mainnet Pool

Stop the testnet pool if running:

	sudo systemctl stop ghostd_test.service stakepool_test.service

Prepare a cold staking pool:

	coldstakepool-prepare -datadir=~/stakepoolDemoLive

**NOTE**: Save both the recovery phrases.

Set the `"startheight"` parameter to the current block count minus 101.

	nano ~/stakepoolDemoLive/stakepool/stakepool.json

Add pool owner fee payout object to the stakepool.json.
```
    "poolownerwithdrawal": {
        "frequency": 720,
        "address": "...",
        "reserve": 2,
        "threshold": 5
    }
```
Change the address to your public address, frequency is in blocks.

Copy over `systemd` service files to your system:

	sudo cp ~/ghost_stakepool/doc/config/*.service /etc/systemd/system
	sudo systemctl daemon-reload

Start and enable the services, so they start automatically at system boot:

	sudo systemctl start ghostd_live.service stakepool_live.service
	sudo systemctl enable ghostd_live.service stakepool_live.service

Verify all is running:

	sudo tail -f /var/log/syslog
	~/ghost-binaries/ghost-cli -datadir=${HOME}/stakepoolDemoLive getblockchaininfo
	lynx localhost:9000

## 3. Set up webserver

	sudo rm /etc/nginx/sites-enabled/default
	sudo cp ~/ghost_stakepool/doc/config/nginx_stakepool_forward.conf /etc/nginx/conf.d/
	sudo nginx -t
	sudo systemctl stop nginx
	sudo systemctl start nginx
	sudo systemctl enable nginx

To test, browse to:

  - http://vpsip:900/ (mainnet pool)
  - http://vpsip:901/ (testnet)

### Production config

	mkdir /tmp/nginx
	sudo rm /etc/nginx/conf.d/nginx_stakepool_forward.conf
	sudo cp ~/ghost_stakepool/doc/config/nginx_stakepool_production.conf /etc/nginx/conf.d/
	sudo systemctl restart nginx

The production configuration enables:

  - caching (expires after 2 minutes)
  - uses port 80
  - HTTPS / TLS support

To test, browse to:

  - http://vpsip/api/
  - http://vpsip/api/testnet/

### Fancy frontend

Install NodeJS:

	wget -qO- https://raw.githubusercontent.com/creationix/nvm/v0.33.11/install.sh | bash
	nvm install node

Install yarn:

	curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
	echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
	sudo apt-get update && sudo apt-get install yarn

Clone & install fancy frontend

	git clone https://github.com/akshaynexus/ghost-coldstakepool-front
	cd ghost-coldstakepool-front
	yarn install
	yarn run build
	cp -R dist /var/www/html/pool

Setup a domain name: https://kerneltalks.com/howto/how-to-setup-domain-name-in-linux-server/

Setup TLS:

	sudo apt-get update && sudo apt-get upgrade
	sudo apt-get install software-properties-common certbot python3-certbot-nginx

Create the certificates, enter your domain name in the interactive wizard:

	sudo certbot --nginx certonly

Edit the `/etc/nginx/conf.d/nginx_stakepool_production.conf`, uncomment the 4 settings from the configuration that related to SSL & replace `example.com` with your domain name:

	nano /etc/nginx/conf.d/nginx_stakepool_production.conf
	sudo systemctl restart nginx

### Testnet Pool

```
$ coldstakepool-prepare -datadir=~/stakepoolDemoTest -testnet
NOTE: Save both recovery phrases:
Stake wallet recovery phrase: (...)
Reward wallet recovery phrase: (...)
Stake address: tpcs1mwk4e0z4ll8p6n6wl0hm8l9slyf2vcgjatzwxh
Reward address: poiXfkxxB5eeEgvL3MZN1pxPq9Bfwh7tEm
```

Adjust the startheight parameter to current block count - 101.  Earlier blocks won't be scanned by the pool:

    $ vi ~/stakepoolDemoTest/stakepool/stakepool.json

Add pool owner fee payout obj to the stakepool.json.
```
    "poolownerwithdrawal": {
        "frequency": 720,
        "address": "...",
        "reserve": 2,
        "threshold": 5
    }
```
Copy over `systemd` service files to your system:

```
$ sudo cp ~/ghost_stakepool/doc/config/*.service /etc/systemd/system
$ sudo systemctl daemon-reload
```

Start and enable the services, so they start automatically at system boot:

```
$ sudo systemctl start ghostd_test.service stakepool_test.service
$ sudo systemctl enable ghostd_test.service stakepool_test.service
```

#### Verify all is running

```
$ sudo tail -f /var/log/syslog
$ ~/ghost-binaries/ghost-cli -datadir=${HOME}/stakepoolDemoTest getblockchaininfo
$ lynx localhost:9001
```
