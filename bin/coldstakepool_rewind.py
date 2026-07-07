#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018-2020 The Particl Core developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

"""
Reset pool accounting state after chain rollback and prepare for rescan.

This tool rewinds by resetting volatile stakepooldb records and setting
current_height to startheight - 1.
"""

import os
import sys
import time
import json
import shutil
import struct

import plyvel

from coldstakepool import __version__

DBT_DATA = ord("d")
DBT_BAL = ord("b")
DBT_POOL_BAL = ord("p")
DBT_POOL_BLOCK = ord("B")
DBT_POOL_PAYOUT = ord("P")
DBT_POOL_PENDING_PAYOUT = ord("Q")
DBT_POOL_METRICS = ord("M")


def printVersion():
    print("Ghost coldstakepool version:", __version__)


def printHelp():
    print("Usage: coldstakepool-rewind [options]")
    print("")
    print("Options:")
    print("  --help, -h               Print help.")
    print("  --version, -v            Print version.")
    print("  --datadir=PATH           Path to stakepool data directory.")
    print("  --mainnet                Use mainnet path defaults.")
    print("  --testnet                Use testnet path defaults.")
    print("  --regtest                Use regtest path defaults.")
    print("  --nobackup               Skip creating stakepooldb backup.")
    print("  --yes                    Do not prompt for confirmation.")
    print("")
    print("Default behavior:")
    print("  1) Back up stakepooldb")
    print("  2) Clear derived accounting keys")
    print("  3) Set current_height to startheight - 1")


def defaultDataDir(chain):
    return os.path.join(
        os.path.expanduser("~/.ghost"),
        ("" if chain == "mainnet" else chain),
        "stakepool",
    )


def loadStartHeight(settings_path):
    with open(settings_path) as fs:
        settings = json.load(fs)
    return int(settings.get("startheight", 0))


def deletePrefix(db, batch, prefix):
    it = db.iterator(prefix=prefix)
    try:
        while True:
            key, _ = next(it)
            batch.delete(key)
    except StopIteration:
        pass
    finally:
        it.close()


def parseArgs():
    dataDir = None
    chain = "mainnet"
    make_backup = True
    assume_yes = False

    for v in sys.argv[1:]:
        if len(v) < 2 or v[0] != "-":
            print("Unknown argument", v)
            continue

        s = v.split("=", 1)
        name = s[0].strip()
        while len(name) > 0 and name[0] == "-":
            name = name[1:]

        if name in ("v", "version"):
            printVersion()
            sys.exit(0)
        if name in ("h", "help"):
            printHelp()
            sys.exit(0)
        if name == "mainnet":
            chain = "mainnet"
            continue
        if name == "testnet":
            chain = "testnet"
            continue
        if name == "regtest":
            chain = "regtest"
            continue
        if name == "nobackup":
            make_backup = False
            continue
        if name == "yes":
            assume_yes = True
            continue

        if len(s) == 2:
            if name == "datadir":
                dataDir = os.path.expanduser(s[1])
                continue

        print("Unknown argument", v)

    if dataDir is None:
        dataDir = defaultDataDir(chain)

    return dataDir, chain, make_backup, assume_yes


def main():
    dataDir, chain, make_backup, assume_yes = parseArgs()

    settings_path = os.path.join(dataDir, "stakepool.json")
    db_path = os.path.join(dataDir, "stakepooldb")

    print("dataDir:", dataDir)
    if chain != "mainnet":
        print("chain:", chain)

    if not os.path.exists(settings_path):
        raise ValueError("Settings file not found: " + settings_path)
    if not os.path.isdir(db_path):
        raise ValueError("Database path not found: " + db_path)

    start_height = loadStartHeight(settings_path)
    rewind_height = start_height - 1

    if rewind_height < -1:
        raise ValueError("Invalid rewind height: %d" % (rewind_height))

    print("Configured startheight:", start_height)
    print("Target current_height:", rewind_height)
    print("")
    print(
        "This will clear derived pool accounting and requires a rescan from current_height + 1."
    )

    if not assume_yes:
        answer = input("Continue? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return 1

    if make_backup:
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        backup_path = db_path + ".rewind-backup-" + ts
        print("Backing up database to:", backup_path)
        shutil.copytree(db_path, backup_path)

    db = plyvel.DB(db_path, create_if_missing=False)
    try:
        with db.write_batch(transaction=True) as b:
            deletePrefix(db, b, bytes([DBT_BAL]))
            deletePrefix(db, b, bytes([DBT_POOL_BAL]))
            deletePrefix(db, b, bytes([DBT_POOL_BLOCK]))
            deletePrefix(db, b, bytes([DBT_POOL_PAYOUT]))
            deletePrefix(db, b, bytes([DBT_POOL_PENDING_PAYOUT]))
            deletePrefix(db, b, bytes([DBT_POOL_METRICS]))

            volatile_data_keys = (
                b"blocks_found",
                b"pool_disbursed",
                b"pool_fees",
                b"pool_fees_detected",
                b"pool_withdrawn",
                b"last_payment_run",
                b"last_withdrawal_run",
            )
            for data_key in volatile_data_keys:
                b.delete(bytes([DBT_DATA]) + data_key)

            b.put(
                bytes([DBT_DATA]) + b"current_height", struct.pack(">i", rewind_height)
            )
    finally:
        db.close()

    print("Rewind complete.")
    print(
        "Next: start the pool; it will rebuild accounting from configured startheight."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
