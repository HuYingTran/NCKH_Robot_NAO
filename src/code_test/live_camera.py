#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import sys
import time

try:
    from naoqi import ALProxy
except ImportError:
    ALProxy = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Xem truc tiep camera robot NAO (nhan q de thoat)"
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
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="ID camera (0: top, 1: bottom)",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=2,
        help="Do phan giai NAOqi (0..4, mac dinh: 2 = VGA)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=15,
        help="FPS yeu cau (mac dinh: 15)",
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

    try:
        cv2 = __import__("cv2")
        np = __import__("numpy")
    except ImportError:
        print(
            "Can OpenCV + NumPy de xem truc tiep.\n"
            "Hay cai dat roi chay lai (vi du: sudo apt install python-opencv python-numpy).",
            file=sys.stderr,
        )
        return 2

    print("Dang ket noi toi NAO tai {}:{} ...".format(args.ip, args.port))

    try:
        video_proxy = ALProxy("ALVideoDevice", args.ip, args.port)
        motion_proxy = ALProxy("ALMotion", args.ip, args.port)
        posture_proxy = ALProxy("ALRobotPosture", args.ip, args.port)
    except Exception as exc:
        print("Khong tao duoc proxy can thiet: {}".format(exc), file=sys.stderr)
        return 3

    try:
        print("Dang dua robot ve tu the dung (StandInit) ...")
        motion_proxy.wakeUp()
        posture_proxy.goToPosture("StandInit", 0.5)
        print("Robot da o trang thai dung.")
    except Exception as exc:
        print("Khong the dua robot ve trang thai dung: {}".format(exc), file=sys.stderr)
        return 5

    client_name = "python_live_camera"
    color_space = 11
    capture_id = None
    head_scan_started = False
    head_scan_done = False
    head_scan_stage = 0
    next_head_action_time = 0.0

    try:
        capture_id = video_proxy.subscribeCamera(
            client_name,
            args.camera,
            args.resolution,
            color_space,
            args.fps,
        )

        print("Dang xem camera... nhan 'q' de thoat.")

        while True:
            image = video_proxy.getImageRemote(capture_id)
            if image is None:
                continue

            width = image[0]
            height = image[1]
            image_buffer = image[6]

            frame_rgb = np.frombuffer(image_buffer, dtype=np.uint8).reshape((height, width, 3))
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            lower_height = int(height * 0.38)
            lower_top_width = int(width * 0.64)
            lower_bottom_width = int(width * 0.82)
            lower_center_x = width // 2
            lower_top_y = height - lower_height - 20
            lower_bottom_y = lower_top_y + lower_height

            upper_height = int(height * 0.18)
            upper_top_width = int(lower_top_width * 0.72)
            upper_bottom_width = lower_top_width
            upper_center_x = width // 2
            upper_top_y = max(10, lower_top_y - upper_height)
            upper_bottom_y = lower_top_y

            upper_top_x1 = upper_center_x - (upper_top_width // 2)
            upper_top_x2 = upper_center_x + (upper_top_width // 2)
            upper_bottom_x1 = upper_center_x - (upper_bottom_width // 2)
            upper_bottom_x2 = upper_center_x + (upper_bottom_width // 2)

            lower_top_x1 = lower_center_x - (lower_top_width // 2)
            lower_top_x2 = lower_center_x + (lower_top_width // 2)
            lower_bottom_x1 = lower_center_x - (lower_bottom_width // 2)
            lower_bottom_x2 = lower_center_x + (lower_bottom_width // 2)

            overlay = frame_bgr.copy()
            upper_zone_pts = np.array(
                [
                    [upper_top_x1, upper_top_y],
                    [upper_top_x2, upper_top_y],
                    [upper_bottom_x2, upper_bottom_y],
                    [upper_bottom_x1, upper_bottom_y],
                ],
                dtype=np.int32,
            )
            lower_zone_pts = np.array(
                [
                    [lower_top_x1, lower_top_y],
                    [lower_top_x2, lower_top_y],
                    [lower_bottom_x2, lower_bottom_y],
                    [lower_bottom_x1, lower_bottom_y],
                ],
                dtype=np.int32,
            )
            cv2.fillConvexPoly(overlay, upper_zone_pts, (0, 215, 255))
            cv2.fillConvexPoly(overlay, lower_zone_pts, (0, 180, 0))
            cv2.addWeighted(overlay, 0.18, frame_bgr, 0.82, 0, frame_bgr)

            cv2.polylines(frame_bgr, [upper_zone_pts], True, (0, 255, 255), 2)
            cv2.putText(
                frame_bgr,
                "CAUTION",
                (upper_top_x1 + 8, max(22, upper_top_y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.polylines(frame_bgr, [lower_zone_pts], True, (0, 255, 0), 2)
            cv2.putText(
                frame_bgr,
                "SAFE ZONE",
                (lower_top_x1 + 8, max(22, lower_top_y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("NAO Live Camera", frame_bgr)

            if not head_scan_done:
                try:
                    now = time.time()
                    if not head_scan_started:
                        print("Dang cui/ngang dau de mo rong goc camera ...")
                        motion_proxy.setStiffnesses("Head", 1.0)
                        motion_proxy.setAngles("HeadPitch", 0.35, 0.12)
                        head_scan_started = True
                        head_scan_stage = 1
                        next_head_action_time = now + 1.0
                    elif now >= next_head_action_time:
                        if head_scan_stage == 1:
                            motion_proxy.setAngles("HeadYaw", -0.55, 0.12)
                            head_scan_stage = 2
                            next_head_action_time = now + 1.0
                        elif head_scan_stage == 2:
                            motion_proxy.setAngles("HeadYaw", 0.55, 0.12)
                            head_scan_stage = 3
                            next_head_action_time = now + 1.2
                        elif head_scan_stage == 3:
                            motion_proxy.setAngles("HeadYaw", 0.0, 0.15)
                            motion_proxy.setAngles("HeadPitch", 0.0, 0.15)
                            head_scan_stage = 4
                            next_head_action_time = now + 0.8
                        elif head_scan_stage == 4:
                            print("Da hoan tat cui/ngang dau.")
                            head_scan_done = True
                except Exception as exc:
                    print("Khong the dieu khien dau robot: {}".format(exc), file=sys.stderr)
                    return 6

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    except Exception as exc:
        print("Loi khi xem camera: {}".format(exc), file=sys.stderr)
        return 4
    finally:
        if capture_id:
            try:
                video_proxy.unsubscribe(capture_id)
            except Exception:
                pass
        if cv2 is not None:
            cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
