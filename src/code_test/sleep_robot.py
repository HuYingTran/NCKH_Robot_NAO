#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import sys

try:
    from naoqi import ALProxy
except ImportError:
    ALProxy = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Dua robot NAO ve trang thai nghi (sleep/rest)"
    )
    parser.add_argument(
        "--ip",
        default="tranvanhuynh20195053.local",
        help="IP/hostname cua robot NAO (mac dinh: tranvanhuynh20195053.local)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9559,
        help="Port NAOqi (mac dinh: 9559)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if ALProxy is None:
        print(
            "Khong import duoc module 'naoqi'. Hay chay bang Python di kem NAOqi SDK.",
            file=sys.stderr,
        )
        return 1

    print("Dang ket noi ALMotion tai {}:{} ...".format(args.ip, args.port))

    try:
        motion_proxy = ALProxy("ALMotion", args.ip, args.port)
    except Exception as exc:
        print("Khong tao duoc ALMotion proxy: {}".format(exc), file=sys.stderr)
        return 2

    try:
        print("Dang dua robot ve trang thai sleep/rest ...")
        motion_proxy.rest()
        print("Robot da vao trang thai nghi.")
    except Exception as exc:
        print("Khong the dua robot vao trang thai nghi: {}".format(exc), file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
