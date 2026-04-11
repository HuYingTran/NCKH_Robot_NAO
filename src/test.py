# -*- encoding: UTF-8 -*-

from __future__ import print_function

import argparse
import time

from naoqi import ALProxy


def _force_weight_shift(motion, support_leg, lean_roll=0.10, speed=0.12, settle_seconds=0.8):
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
    motion.setAngles(names, angles, speed)
    time.sleep(settle_seconds)


def _release_weight_shift(motion):
    """Bring hip/ankle roll back to neutral after swing leg is closed."""
    names = [
        "LHipRoll",
        "RHipRoll",
        "LAnkleRoll",
        "RAnkleRoll",
    ]
    motion.setAngles(names, [0.0, 0.0, 0.0, 0.0], 0.07)
    time.sleep(0.9)


def _prepare_robot_for_motion(motion, posture):
    """Prepare body stiffness and posture, tolerating wakeUp failures on some setups."""
    try:
        motion.wakeUp()
    except Exception as exc:
        print("Canh bao: wakeUp loi ({}). Thu fallback bang setStiffnesses.".format(exc))
    motion.setStiffnesses("Body", 1.0)
    try:
        posture.goToPosture("StandInit", 0.5)
    except Exception as exc:
        print("Canh bao: khong ve duoc StandInit ({}). Tiep tuc voi tu the hien tai.".format(exc))


def lift_one_leg(
    robot_ip,
    port=9559,
    support_leg="LLeg",
    lift_height=0.008,
    hold_seconds=0.3,
    force_lift=False,
    lean_roll=0.04,
    balance_seconds=4.0,
    up_seconds=3.0,
    down_seconds=4.0,
):
    """Lift one leg, keep balance on the support leg, then put the leg down."""
    motion = ALProxy("ALMotion", robot_ip, port)
    posture = ALProxy("ALRobotPosture", robot_ip, port)

    swing_leg = "RLeg" if support_leg == "LLeg" else "LLeg"

    _prepare_robot_for_motion(motion, posture)

    try:
        # Use NAO whole-body balance to keep COM over support leg.
        motion.wbEnable(True)
        motion.wbFootState("Fixed", "Legs")
        motion.wbEnableBalanceConstraint(True, "Legs")

        # Always do a small pre-lean so the swing leg unloads instead of jerking.
        active_lean = abs(lean_roll) if force_lift else min(abs(lean_roll), 0.03)
        shift_speed = 0.12 if force_lift else 0.08
        shift_settle = 0.8 if force_lift else 1.0
        print("Dang chuyen trong tam ve {} (lean={:.3f} rad)".format(support_leg, active_lean))
        _force_weight_shift(
            motion,
            support_leg,
            lean_roll=active_lean,
            speed=shift_speed,
            settle_seconds=shift_settle,
        )

        motion.wbGoToBalance(support_leg, balance_seconds)
        time.sleep(0.3)

        motion.wbFootState("Free", swing_leg)
        time.sleep(0.2)
        # Gentle raise: keep forward offset small to avoid aggressive shift.
        x_step = 0.004 if force_lift else 0.0
        target_up = [x_step, 0.0, lift_height, 0.0, 0.0, 0.0]
        motion.positionInterpolation(swing_leg, 0, target_up, 63, up_seconds, False)

        print("Da nhac {} len {:.1f} cm, giu trong {:.1f}s".format(swing_leg, lift_height * 100.0, hold_seconds))
        time.sleep(max(0.0, hold_seconds))

    finally:
        try:
            target_down = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            # Lower slowly for smoother landing.
            motion.positionInterpolation(swing_leg, 0, target_down, 63, down_seconds, False)
        except Exception:
            pass

        try:
            # Reverse order while landing: close foot first, then recenter body.
            motion.wbFootState("Fixed", swing_leg)
            _release_weight_shift(motion)
            motion.wbGoToBalance("Legs", 1.5)
            motion.wbEnable(False)
        except Exception:
            pass

        motion.stopMove()
        motion.setStiffnesses("Body", 0.8)
        try:
            # Final settle to reduce post-motion freeze after perturbations.
            posture.goToPosture("StandInit", 0.3)
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="192.168.157.228", help="Robot IP")
    parser.add_argument("--port", type=int, default=9559, help="Robot port")
    parser.add_argument("--support-leg", type=str, default="LLeg", choices=["LLeg", "RLeg"], help="Support leg")
    parser.add_argument("--lift-height", type=float, default=0.008, help="Lift height in meters")
    parser.add_argument("--hold-seconds", type=float, default=0.3, help="Hold time in seconds")
    parser.add_argument("--force-lift", action="store_true", help="Force stronger weight shift before lifting")
    parser.add_argument("--lean-roll", type=float, default=0.04, help="Hip roll bias (rad) used in force-lift")
    parser.add_argument("--balance-seconds", type=float, default=4.0, help="Time to shift COM onto support leg")
    parser.add_argument("--up-seconds", type=float, default=3.0, help="Time to raise swing leg (seconds)")
    parser.add_argument("--down-seconds", type=float, default=4.0, help="Time to lower swing leg (seconds)")
    args = parser.parse_args()

    lift_one_leg(
        args.ip,
        args.port,
        args.support_leg,
        args.lift_height,
        args.hold_seconds,
        args.force_lift,
        args.lean_roll,
        args.balance_seconds,
        args.up_seconds,
        args.down_seconds,
    )