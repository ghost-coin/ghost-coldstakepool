# Upgrading ghostd daemon

This guide covers upgrading Ghost daemon, when a new version is available.

## 1. Preparation

Login to your machine, replace `stakepoolvps` with the IP address or url of your pool:

    $ ssh stakepooluser@stakepoolvps

Shut down the pool and daemon (second line applies if you're running testnet version as well):

    $ sudo systemctl stop stakepool_live.service ghostd_live.service
    $ sudo systemctl stop stakepool_test.service ghostd_test.service

## 2. Update `coldstakepool` & `ghostd` to latest version

Update the coldstakepool code:

    $ cd ~/ghost_stakepool
    $ git pull
    $ sudo pip3 install --upgrade .

Update Ghost Core:

    $ python3 bin/coldstakepool-prepare.py --update_core

Output should end (if successful) with lines similar to:

    ghostd --version
    Ghost Core Daemon version v0.19.1.9-ecea0356a

## 3. Restart the pool

Start the pool/s back up (second line applies if you're running testnet version as well):

    $ sudo systemctl start stakepool_live.service
    $ sudo systemctl start stakepool_test.service

Verify if everything is running correctly:

```
$ ~/ghost-binaries/ghost-cli -datadir=${HOME}/stakepoolDemoLive getnetworkinfo
{
  "version": 18010302,
  "subversion": "/Satoshi:0.19.1.9/",
(..)
```

```
$ tail -n 1000 ~/stakepoolDemoLive/stakepool/stakepool.log | grep version
20-03-25_13-58-46	coldstakepool-run, version: 0.0.15
20-03-25_13-58-56	Ghost Core version 18010302
```

In your browser, open `http://stakepoolvpsip:900/json/version`, you should see this:

    {"core": "18010302", "pool": "0.0.15"}


You can check blockheight with: 
 ```
 ~/ghost-binaries/ghost-cli -datadir=${HOME}/stakepoolDemoLive getblockcount
```
----

## Notes

You can select specific versions of Ghost Core and where to place them using the following environment variables:

    $ GHOST_BINDIR=~/ghost-alpha GHOST_VERSION=0.19.1.9 GHOST_VERSION_TAG=alpha coldstakepool-prepare --update_core
