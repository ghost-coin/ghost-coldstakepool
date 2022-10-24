#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018-2020 The Particl Core developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

"""

Minimal example of starting a Ghost stake pool.

1. Download and verify a ghost-core release.

2. Create a ghost.conf that:
    - Starts 2 wallets
    - Enables zmqpubhashblock
    - Enables csindex and addressindex

3. Generate and import a recovery phrase for both wallets.
4. Generate the pool_stake_address from the staking wallet.
    - The address pool participants will set their outputs to stake with.
5. Generate the pool_reward_address from the reward wallet.
    - The address that will collect the rewards for blocks staked by the pool.
6. Disable staking on the reward wallet.
7. Set the reward address of the staking wallet.
8. Create the stakepool.json configuration file.


Install dependencies:
apt-get install wget gnupg

Run the prepare script:
coldstakepool-prepare.py -datadir=~/stakepoolDemoTest -testnet

Start the daemon:
~/ghost-binaries/ghostd -datadir=/home/$(id -u -n)/stakepoolDemoTest

Start the pool script:
coldstakepool-run.py -datadir=~/stakepoolDemoTest/stakepool -testnet


"""

import sys
import os
import mmap
import time
import json
import stat
import hashlib
import tarfile
import subprocess
import urllib.request
from coldstakepool.util import (
    callrpc_cli,
)


GHOST_BINDIR = os.path.expanduser(os.getenv('GHOST_BINDIR', '~/ghost-binaries'))
GHOSTD = os.getenv('GHOSTD', 'ghostd')
GHOST_TX = os.getenv('GHOST_TX', 'ghost-tx')
GHOST_CLI = os.getenv('GHOST_CLI', 'ghost-cli')

GHOST_VERSION = os.getenv('GHOST_VERSION', '0.22.1.0')
GHOST_VERSION_TAG = os.getenv('GHOST_VERSION_TAG', '')
GHOST_ARCH = os.getenv('GHOST_ARCH', 'x86_64-linux-gnu.tar.gz')
GHOST_REPO = os.getenv('GHOST_REPO', 'ghost-coin')


def startDaemon(nodeDir, bindir):
    command_cli = os.path.join(bindir, GHOSTD)

    args = [command_cli, '-daemon', '-noconnect', '-nostaking', '-nodnsseed', '-datadir=' + nodeDir]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.communicate()

    if len(out[1]) > 0:
        raise ValueError('Daemon error ' + str(out[1]))
    return out[0]


def downloadGhostCore():
    print('Download and verify Ghost core release.')

    if 'osx' in GHOST_ARCH:
        os_dir_name = 'osx-unsigned'
        os_name = 'osx'
    elif 'win32-setup' in GHOST_ARCH or 'win64-setup' in GHOST_ARCH:
        os_dir_name = 'win-signed'
        os_name = 'win-signer'
    elif 'win32' in GHOST_ARCH or 'win64' in GHOST_ARCH:
        os_dir_name = 'win-unsigned'
        os_name = 'win'
    else:
        os_dir_name = 'linux'
        os_name = 'linux'

    release_filename = 'ghost-{}-{}'.format(GHOST_VERSION, GHOST_ARCH)
    release_url = 'https://github.com/%s/ghost-core/releases/download/v%s/%s' % (GHOST_REPO, GHOST_VERSION + GHOST_VERSION_TAG, release_filename)

    packed_path = os.path.join(GHOST_BINDIR, release_filename)
    if not os.path.exists(packed_path):
        subprocess.check_call(['wget', release_url, '-P', GHOST_BINDIR])

    hasher = hashlib.sha256()
    with open(packed_path, 'rb') as fp:
        hasher.update(fp.read())
    release_hash = hasher.digest()

    print('Release hash:', release_hash.hex())

def extractGhostCore():
    packed_path = os.path.join(GHOST_BINDIR, 'ghost-{}-{}'.format(GHOST_VERSION, GHOST_ARCH))
    daemon_path = os.path.join(GHOST_BINDIR, GHOSTD)
    bin_prefix = GHOST_BINDIR

    bins = [GHOSTD, GHOST_CLI, GHOST_TX]
    with tarfile.open(packed_path) as ft:
        for b in bins:
            out_path = os.path.join(bin_prefix, b)
            fi = ft.extractfile('{}-{}/{}'.format('ghost', GHOST_VERSION, b))
            with open(out_path, 'wb') as fout:
                fout.write(fi.read())
            fi.close()
            os.chmod(out_path, stat.S_IRWXU | stat.S_IXGRP | stat.S_IXOTH)

    output = subprocess.check_output([daemon_path, '--version'])
    version = output.splitlines()[0].decode('utf-8')
    print('ghostd --version\n' + version)
    assert(GHOST_VERSION in version)


def printVersion():
    from coldstakepool import __version__
    print('Ghost coldstakepool version:', __version__)


def printHelp():
    print('Usage: coldstakepool-prepare ')
    print('\n--help, -h                 Print help.')
    print('--version, -v              Print version.')
    print('--update_core              Download, verify and extract Ghost core release and exit.')
    print('--download_core            Download and verify Ghost core release and exit.')
    print('--datadir=PATH             Path to Ghost data directory, default:~/.ghost.')
    print('--pooldir=PATH             Path to stakepool data directory, default:{datadir}/stakepool.')
    print('--mainnet                  Run Ghost in mainnet mode.')
    print('--testnet                  Run Ghost in testnet mode.')
    print('--regtest                  Run Ghost in regtest mode.')
    print('--stake_wallet_mnemonic=   Recovery phrase to use for the staking wallet, default is randomly generated.')
    print('--reward_wallet_mnemonic=  Recovery phrase to use for the reward wallet, default is randomly generated.')
    print('--mode=master/observer     Mode stakepool is initialised to. observer mode requires configurl to be specified, default:master.')
    print('--configurl=url            Url to pull the stakepool config file from when initialising for observer mode.')


def main():
    dataDir = None
    poolDir = None
    chain = 'mainnet'
    mode = 'master'
    configurl = None
    stake_wallet_mnemonic = None
    reward_wallet_mnemonic = None

    for v in sys.argv[1:]:
        if len(v) < 2 or v[0] != '-':
            print('Unknown argument', v)
            continue

        s = v.split('=')
        name = s[0].strip()

        for i in range(2):
            if name[0] == '-':
                name = name[1:]

        if name == 'v' or name == 'version':
            printVersion()
            return 0
        if name == 'h' or name == 'help':
            printHelp()
            return 0
        if name == 'update_core':
            downloadGhostCore()
            extractGhostCore()
            return 0
        if name == 'download_core':
            downloadGhostCore()
            return 0
        if name == 'mainnet':
            continue
        if name == 'testnet':
            chain = 'testnet'
            continue
        if name == 'regtest':
            chain = 'regtest'
            continue

        if len(s) == 2:
            if name == 'datadir':
                dataDir = os.path.expanduser(s[1])
                continue
            if name == 'pooldir':
                poolDir = os.path.expanduser(s[1])
                continue
            if name == 'stake_wallet_mnemonic':
                stake_wallet_mnemonic = s[1]
                continue
            if name == 'reward_wallet_mnemonic':
                reward_wallet_mnemonic = s[1]
                continue
            if name == 'mode':
                mode = s[1]
                if mode != 'master' and mode != 'observer':
                    sys.stderr.write('Unknown value for mode:' + mode)
                    exit(1)
                continue
            if name == 'configurl':
                configurl = s[1]
                continue

        print('Unknown argument', v)

    if mode == 'observer' and configurl is None:
        sys.stderr.write('observer mode requires configurl set\n')
        exit(1)

    if not os.path.exists(GHOST_BINDIR):
        os.makedirs(GHOST_BINDIR)

    # 1. Download and verify the specified version of ghost-core
    downloadGhostCore()
    extractGhostCore()

    dataDirWasNone = False
    if dataDir is None:
        dataDir = os.path.expanduser('~/.ghost')
        dataDirWasNone = True

    if poolDir is None:
        if dataDirWasNone:
            poolDir = os.path.join(os.path.expanduser(dataDir), ('' if chain == 'mainnet' else chain), 'stakepool')
        else:
            poolDir = os.path.join(os.path.expanduser(dataDir), 'stakepool')

    print('dataDir:', dataDir)
    print('poolDir:', poolDir)
    if chain != 'mainnet':
        print('chain:', chain)

    if not os.path.exists(dataDir):
        os.makedirs(dataDir)

    if not os.path.exists(poolDir):
        os.makedirs(poolDir)

    # 2. Create a ghost.conf
    daemonConfFile = os.path.join(dataDir, 'ghost.conf')
    if os.path.exists(daemonConfFile):
        sys.stderr.write('Error: %s exists, exiting.' % (daemonConfFile))
        exit(1)

    zmq_port = 207922 if chain == 'mainnet' else 208922
    with open(daemonConfFile, 'w') as fp:
        if chain != 'mainnet':
            fp.write(chain + '=1\n\n')

        fp.write('zmqpubhashblock=tcp://127.0.0.1:%d\n' % (zmq_port))

        chain_id = 'test.' if chain == 'testnet' else 'regtest.' if chain == 'regtest' else ''
        fp.write(chain_id + 'wallet=pool_stake\n')
        fp.write(chain_id + 'wallet=pool_reward\n')

        fp.write('csindex=1\n')
        fp.write('addressindex=1\n')

    startDaemon(dataDir, GHOST_BINDIR)

    # Delay until responding
    for k in range(10):
        try:
            callrpc_cli(GHOST_BINDIR, dataDir, chain, 'getblockchaininfo')
            break
        except Exception:
            time.sleep(0.5)

    try:
        if mode == 'observer':
            print('Preparing observer config.')

            settings = json.loads(urllib.request.urlopen(configurl).read().decode('utf-8'))

            settings['mode'] = 'observer'
            settings['ghostbindir'] = GHOST_BINDIR
            settings['ghostdatadir'] = dataDir
            pool_stake_address = settings['pooladdress']
            pool_reward_address = settings['rewardaddress']

            v = callrpc_cli(GHOST_BINDIR, dataDir, chain, 'validateaddress "%s"' % (pool_stake_address))
            assert('isvalid' in v)
            assert(v['isvalid'] is True)

            callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_stake importaddress "%s"' % (v['address']))
            callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_reward importaddress "%s"' % (pool_reward_address))

            poolConfFile = os.path.join(poolDir, 'stakepool.json')
            if os.path.exists(poolConfFile):
                sys.stderr.write('Error: %s exists, exiting.' % (poolConfFile))
                exit(1)
            with open(poolConfFile, 'w') as fp:
                json.dump(settings, fp, indent=4)

            print('Done.')
            return 0

        # 3. Generate and import a recovery phrase for both wallets.
        if stake_wallet_mnemonic is None:
            callrpc_cli(GHOST_BINDIR, dataDir, chain, 'createwallet "pool_stake"')
            stake_wallet_mnemonic = callrpc_cli(GHOST_BINDIR, dataDir, chain, 'mnemonic new')['mnemonic']

        if reward_wallet_mnemonic is None:
            callrpc_cli(GHOST_BINDIR, dataDir, chain, 'createwallet "pool_reward"')
            reward_wallet_mnemonic = callrpc_cli(GHOST_BINDIR, dataDir, chain, 'mnemonic new')['mnemonic']

        callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_stake extkeyimportmaster "%s"' % (stake_wallet_mnemonic))
        callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_reward extkeyimportmaster "%s"' % (reward_wallet_mnemonic))

        # 4. Generate the pool_stake_address from the staking wallet.
        pool_stake_address = callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_stake getnewaddress')
        pool_stake_address = callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_stake validateaddress %s true' % (pool_stake_address))['stakeonly_address']

        # 5. Generate the pool_reward_address from the reward wallet.
        pool_reward_address = callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_reward getnewaddress')

        # 6. Disable staking on the reward wallet.
        callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_reward walletsettings stakingoptions "{\\"enabled\\":\\"false\\"}"')

        # 7. Set the reward address of the staking wallet.
        callrpc_cli(GHOST_BINDIR, dataDir, chain, '-rpcwallet=pool_stake walletsettings stakingoptions "{\\"rewardaddress\\":\\"%s\\"}"' % (pool_reward_address))

    finally:
        callrpc_cli(GHOST_BINDIR, dataDir, chain, 'stop')

    # 8. Create the stakepool.json configuration file.
    html_port = 9000 if chain == 'mainnet' else 9001
    poolsettings = {
        'mode': 'master',
        'debug': True,
        'ghostbindir': GHOST_BINDIR,
        'ghostdatadir': dataDir,
        'startheight': 200000,  # Set to a block height before the pool begins operating
        'pooladdress': pool_stake_address,
        'rewardaddress': pool_reward_address,
        'zmqhost': 'tcp://127.0.0.1',
        'zmqport': zmq_port,
        'htmlhost': 'localhost',
        'htmlport': html_port,
        'parameters': [
            {
                'height': 0,
                'poolfeepercent': 3,
                'stakebonuspercent': 5,
                'payoutthreshold': 0.5,
                'minblocksbetweenpayments': 100,
                'minoutputvalue': 0.1,
            },
        ]
    }

    poolConfFile = os.path.join(poolDir, 'stakepool.json')
    if os.path.exists(poolConfFile):
        sys.stderr.write('Error: %s exists, exiting.' % (poolConfFile))
        exit(1)
    with open(poolConfFile, 'w') as fp:
        json.dump(poolsettings, fp, indent=4)

    print('NOTE: Save both the recovery phrases:')
    print('Stake wallet recovery phrase:', stake_wallet_mnemonic)
    print('Reward wallet recovery phrase:', reward_wallet_mnemonic)
    print('Stake address:', pool_stake_address)
    print('Reward address:', pool_reward_address)

    print('Done.')


if __name__ == '__main__':
    main()
