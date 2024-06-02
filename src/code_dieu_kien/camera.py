# -*- coding: utf-8 -*-
from naoqi import ALProxy
import cv2
import numpy as np

# Thông tin kết nối đến robot
robot_ip = "127.0.0.1"  # Thay bằng địa chỉ IP của robot NAO
robot_port = 9559

# Tạo proxy cho ALVideoDevice
video_proxy = ALProxy("ALVideoDevice", robot_ip, robot_port)

# Đăng ký một client video
resolution = 2  # kQVGA (320x240)
color_space = 11  # kRGBColorSpace
fps = 30

name_id = video_proxy.subscribe("python_client", resolution, color_space, fps)

# Lấy một hình ảnh từ camera
image_container = video_proxy.getImageRemote(name_id)

# Rút đăng ký client video sau khi lấy hình ảnh
video_proxy.unsubscribe(name_id)

# Lấy các thông tin hình ảnh
image_width = image_container[0]
image_height = image_container[1]
array = image_container[6]

# Chuyển đổi mảng ảnh thành định dạng OpenCV
image_string = str(bytearray(array))
image = np.fromstring(image_string, dtype=np.uint8).reshape((image_height, image_width, 3))

# Hiển thị hình ảnh
cv2.imshow("Camera", image)
cv2.waitKey(0)
cv2.destroyAllWindows()
