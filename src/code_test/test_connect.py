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
		description="Ket noi den robot NAO bang NAOqi SDK"
	)
	parser.add_argument(
		"--ip",
		default="tranvanhuynh20195053.local",
		help="IP cua robot NAO (mac dinh: tranvanhuynh20195053)",
	)
	parser.add_argument(
		"--port",
		type=int,
		default=9559,
		help="Port NAOqi (mac dinh: 9559)",
	)
	return parser.parse_args()


def create_proxy(module_name, ip, port):
	try:
		return ALProxy(module_name, ip, port)
	except Exception as exc:
		raise RuntimeError(
			"Khong tao duoc proxy '{}' tai {}:{} -> {}".format(
				module_name, ip, port, exc
			)
		)


def main():
	args = parse_args()

	if ALProxy is None:
		print(
			"Khong import duoc module 'naoqi'. "
			"Hay chay script bang Python di kem NAOqi SDK.",
			file=sys.stderr,
		)
		return 1

	print("Dang ket noi toi NAO tai {}:{} ...".format(args.ip, args.port))

	try:
		system_proxy = create_proxy("ALSystem", args.ip, args.port)
		motion_proxy = create_proxy("ALMotion", args.ip, args.port)
	except RuntimeError as exc:
		print(str(exc), file=sys.stderr)
		return 2

	try:
		robot_name = system_proxy.robotName()
	except Exception:
		robot_name = "Unknown"

	try:
		robot_version = system_proxy.systemVersion()
	except Exception:
		robot_version = "Unknown"

	try:
		body_stiffness = motion_proxy.getStiffnesses("Body")
	except Exception:
		body_stiffness = "Khong doc duoc"

	print("Ket noi thanh cong!")
	print("- Ten robot: {}".format(robot_name))
	print("- Version NAOqi: {}".format(robot_version))
	print("- Stiffness Body: {}".format(body_stiffness))

	return 0


if __name__ == "__main__":
	sys.exit(main())
