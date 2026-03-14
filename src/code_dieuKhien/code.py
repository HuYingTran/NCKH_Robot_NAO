# -*- coding: utf-8 -*-
"""Ket noi NAO va thuc hien dong tac buoc chan len bac thang."""

import time

from naoqi import ALProxy


# Thong tin ket noi den robot
ROBOT_IP = "192.168.31.226"  # Thay bang IP NAO cua ban
ROBOT_PORT = 9559

# Thong so bac thang
STEP_FORWARD_M = 0.02  # Cach chan hien tai 2 cm
STEP_HEIGHT_M = 0.05   # Bac thang cao 5 cm


def connect_proxies(robot_ip, robot_port):
	motion_proxy = ALProxy("ALMotion", robot_ip, robot_port)
	posture_proxy = ALProxy("ALRobotPosture", robot_ip, robot_port)
	return motion_proxy, posture_proxy


def step_onto_stair(motion_proxy, posture_proxy, support_leg="LLeg", hold_seconds=1.5):
	"""
	support_leg:
		- "LLeg": dung tren chan trai, buoc chan phai len bac
		- "RLeg": dung tren chan phai, buoc chan trai len bac
	"""
	free_leg = "RLeg" if support_leg == "LLeg" else "LLeg"

	# Chuan bi robot o trang thai dung on dinh.
	motion_proxy.wakeUp()
	motion_proxy.setStiffnesses("Body", 1.0)
	posture_proxy.goToPosture("StandInit", 0.5)

	# Bat can bang toan than truoc khi di chuyen mot chan.
	motion_proxy.wbEnable(True)
	motion_proxy.wbFootState("Fixed", "Legs")
	motion_proxy.wbEnableBalanceConstraint(True, "Legs")

	# Chuyen trong tam ve chan tru.
	motion_proxy.wbGoToBalance(support_leg, 2.0)

	# Giai phong chan buoc va nang len theo cao do bac thang + do tien 2 cm.
	motion_proxy.wbFootState("Free", free_leg)
	target_up = [STEP_FORWARD_M, 0.0, STEP_HEIGHT_M, 0.0, 0.0, 0.0]
	motion_proxy.positionInterpolation(
		free_leg,
		2,   # FRAME_ROBOT
		target_up,
		63,
		2.0,
		False,
	)

	print(
		"Da dua {} len bac: tien {:.0f} cm, cao {:.0f} cm.".format(
			free_leg, STEP_FORWARD_M * 100.0, STEP_HEIGHT_M * 100.0
		)
	)
	time.sleep(hold_seconds)

	# Ha chan xuong vi tri moi (van tien 2 cm) de dat len mat bac.
	target_down_on_step = [STEP_FORWARD_M, 0.0, 0.0, 0.0, 0.0, 0.0]
	motion_proxy.positionInterpolation(
		free_leg,
		2,
		target_down_on_step,
		63,
		1.8,
		False,
	)

	# Co dinh lai hai chan va tat whole-body mode.
	motion_proxy.wbFootState("Fixed", free_leg)
	motion_proxy.wbGoToBalance("Legs", 1.5)
	motion_proxy.wbEnable(False)


def main():
	motion_proxy = None
	posture_proxy = None

	try:
		motion_proxy, posture_proxy = connect_proxies(ROBOT_IP, ROBOT_PORT)
		step_onto_stair(
			motion_proxy,
			posture_proxy,
			support_leg="LLeg",  # Doi "RLeg" neu muon buoc bang chan trai
			hold_seconds=1.5,
		)
		print("Hoan tat dong tac buoc len bac thang.")
	except Exception as exc:
		print("Loi khi dieu khien NAO: {}".format(exc))
	finally:
		if motion_proxy is not None:
			try:
				motion_proxy.wbEnable(False)
			except Exception:
				pass
			try:
				posture_proxy.goToPosture("StandInit", 0.5)
			except Exception:
				pass


if __name__ == "__main__":
	main()
