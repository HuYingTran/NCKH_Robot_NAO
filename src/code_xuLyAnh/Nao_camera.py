# -*- coding: utf-8 -*-
from naoqi import ALProxy
import cv2
import numpy as np

import detect_canh

# Thông tin kết nối đến robot
robot_ip = "127.0.0.1"  # Thay bằng địa chỉ IP của robot NAO
robot_port = 9559

# Tạo proxy cho ALVideoDevice
video_proxy = ALProxy("ALVideoDevice", robot_ip, robot_port)

# Chọn camera (0: Top camera, 1: Bottom camera)
cameraIndex = 1  # Thay đổi giá trị này thành 1 để sử dụng Bottom camera
video_proxy.setActiveCamera(cameraIndex)

# Đăng ký một client video
resolution = 2 # k4VGA (1280x960)
color_space = 11  # kRGBColorSpace
fps = 30

x,y,e = 0, 0, 0

name_id = video_proxy.subscribe("python_client", resolution, color_space, fps)

# Kernel sharpening
kernel = np.array([[0, -1, 0],
                   [-1, 5,-1],
                   [0, -1, 0]])

def Nao_camera_detect():
    try:
        while True:
            # Lấy một hình ảnh từ camera
            image_container = video_proxy.getImageRemote(name_id)

            if image_container is None:
                print("Cannot capture image.")
                continue

            # Lấy các thông tin hình ảnh
            image_width = image_container[0]
            image_height = image_container[1]
            array = image_container[6]

            # Chuyển đổi mảng ảnh thành định dạng OpenCV
            image_string = str(bytearray(array))
            image = np.frombuffer(image_string, dtype=np.uint8).reshape((image_height, image_width, 3))

            # Hiển thị hình ảnh
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            global x,y,e
            image, x, y, e = detect_canh.detect_canh(image_rgb)

            cv2.imshow("Camera", image_rgb)

            # Thoát vòng lặp nếu nhấn phím 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        # Rút đăng ký client video
        video_proxy.unsubscribe(name_id)
        cv2.destroyAllWindows()

def data_canh():
    return x,y,e