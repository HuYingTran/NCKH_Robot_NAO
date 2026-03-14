# -*- encoding: UTF-8 -*-

from __future__ import print_function

import argparse
import time

from naoqi import ALProxy


def _force_weight_shift(motion, support_leg, lean_roll=0.10):
    """Bias torso/ankles toward support leg so the swing leg unloads more."""
    roll = abs(lean_roll) if support_leg == "LLeg" else -abs(lean_roll)

    # Roll body toward support side: torso and ankle compensation.
    names = [
        "LHipRoll",
        "RHipRoll",
        "LAnkleRoll",
        "RAnkleRoll",
    ]
    angles = [
        roll,
        roll,
        -0.55 * roll,
        -0.55 * roll,
    ]
    motion.setAngles(names, angles, 0.12)
    time.sleep(0.8)


def lift_one_leg(
    robot_ip,
    port=9559,
    support_leg="LLeg",
    lift_height=0.04,
    hold_seconds=5.0,
    force_lift=False,
    lean_roll=0.10,
):
    """Lift one leg, keep balance on the support leg, then put the leg down."""
    motion = ALProxy("ALMotion", robot_ip, port)
    posture = ALProxy("ALRobotPosture", robot_ip, port)

    swing_leg = "RLeg" if support_leg == "LLeg" else "LLeg"

    motion.wakeUp()
    motion.setStiffnesses("Body", 1.0)
    posture.goToPosture("StandInit", 0.5)

    try:
        # Use NAO whole-body balance to keep COM over support leg.
        motion.wbEnable(True)
        motion.wbFootState("Fixed", "Legs")
        motion.wbEnableBalanceConstraint(True, "Legs")

        if force_lift:
            print("Force-lift: dang ep chuyen trong tam ve {}".format(support_leg))
            _force_weight_shift(motion, support_leg, lean_roll=lean_roll)

        motion.wbGoToBalance(support_leg, 2.0)

        motion.wbFootState("Free", swing_leg)
        x_step = 0.02 if force_lift else 0.015
        target_up = [x_step, 0.0, lift_height, 0.0, 0.0, 0.0]
        motion.positionInterpolation(swing_leg, 0, target_up, 63, 1.8, False)

        print("Da nhac {} len {:.1f} cm, giu trong {:.1f}s".format(swing_leg, lift_height * 100.0, hold_seconds))
        time.sleep(max(0.0, hold_seconds))

    finally:
        try:
            target_down = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            motion.positionInterpolation(swing_leg, 0, target_down, 63, 1.6, False)
        except Exception:
            pass

        try:

            
            motion.wbFootState("Fixed", swing_leg)
            motion.wbGoToBalance("Legs", 1.5)
            motion.wbEnable(False)
        except Exception:
            pass

        motion.stopMove()
        motion.setStiffnesses("Body", 0.8)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="Robot IP")
    parser.add_argument("--port", type=int, default=9559, help="Robot port")
    parser.add_argument("--support-leg", type=str, default="LLeg", choices=["LLeg", "RLeg"], help="Support leg")
    parser.add_argument("--lift-height", type=float, default=0.04, help="Lift height in meters")
    parser.add_argument("--hold-seconds", type=float, default=5.0, help="Hold time in seconds")
    parser.add_argument("--force-lift", action="store_true", help="Force stronger weight shift before lifting")
    parser.add_argument("--lean-roll", type=float, default=0.10, help="Hip roll bias (rad) used in force-lift")
    args = parser.parse_args()

    lift_one_leg(
        args.ip,
        args.port,
        args.support_leg,
        args.lift_height,
        args.hold_seconds,
        args.force_lift,
        args.lean_roll,
    )