#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import os
import sys

try:
    cv2 = __import__("cv2")
    np = __import__("numpy")
except ImportError:
    cv2 = None
    np = None

try:
    from naoqi import ALProxy
except ImportError:
    ALProxy = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Chup 1 buc anh tu camera robot NAO"
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
        default=10,
        help="FPS yeu cau (mac dinh: 10)",
    )
    parser.add_argument(
        "--output",
        default="nao_photo.jpg",
        help="File anh dau ra (vi du: nao_photo.jpg, nao_photo.png, nao_photo.ppm)",
    )
    return parser.parse_args()


def save_ppm(file_path, width, height, rgb_buffer):
    with open(file_path, "wb") as file_obj:
        header = "P6\n{} {}\n255\n".format(width, height).encode("ascii")
        file_obj.write(header)
        file_obj.write(rgb_buffer)


def save_image(file_path, width, height, rgb_buffer):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".ppm":
        save_ppm(file_path, width, height, rgb_buffer)
        return file_path

    if cv2 is not None and np is not None:
        image_np = np.frombuffer(rgb_buffer, dtype=np.uint8).reshape((height, width, 3))
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        ok = cv2.imwrite(file_path, image_bgr)
        if not ok:
            raise RuntimeError("cv2.imwrite that bai")
        return file_path

    fallback_path = os.path.splitext(file_path)[0] + ".ppm"
    save_ppm(fallback_path, width, height, rgb_buffer)
    return fallback_path


def main():
    args = parse_args()

    if ALProxy is None:
        print(
            "Khong import duoc module 'naoqi'. Hay chay bang Python di kem NAOqi SDK.",
            file=sys.stderr,
        )
        return 1

    print("Dang ket noi ALVideoDevice tai {}:{} ...".format(args.ip, args.port))

    try:
        video_proxy = ALProxy("ALVideoDevice", args.ip, args.port)
    except Exception as exc:
        print("Khong tao duoc ALVideoDevice proxy: {}".format(exc), file=sys.stderr)
        return 2

    client_name = "python_read_camera"
    color_space = 11
    capture_id = None

    try:
        capture_id = video_proxy.subscribeCamera(
            client_name,
            args.camera,
            args.resolution,
            color_space,
            args.fps,
        )

        image = video_proxy.getImageRemote(capture_id)
        if image is None:
            print("Khong doc duoc frame tu camera.", file=sys.stderr)
            return 3

        width = image[0]
        height = image[1]
        number_of_layers = image[2]
        color_space_read = image[3]
        timestamp_seconds = image[4]
        timestamp_microseconds = image[5]
        image_buffer = image[6]

        print("Doc frame thanh cong:")
        print("- Kich thuoc: {}x{}".format(width, height))
        print("- So kenh: {}".format(number_of_layers))
        print("- Color space: {}".format(color_space_read))
        print("- Timestamp: {}.{}".format(timestamp_seconds, timestamp_microseconds))
        print("- So byte du lieu: {}".format(len(image_buffer)))

        if args.output:
            output_path = os.path.abspath(args.output)
            saved_path = save_image(output_path, width, height, image_buffer)
            if saved_path != output_path:
                print("Khong co OpenCV, da fallback luu anh PPM: {}".format(saved_path))
            else:
                print("Da luu anh: {}".format(saved_path))

    except Exception as exc:
        print("Loi khi doc camera: {}".format(exc), file=sys.stderr)
        return 4
    finally:
        if capture_id:
            try:
                video_proxy.unsubscribe(capture_id)
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
