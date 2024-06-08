# -*- coding: utf-8 -*-
from naoqi import ALProxy

# Thông tin kết nối đến robot
robot_ip = "127.0.0.1"  # Thay bằng địa chỉ IP của robot NAO
robot_port = 9559

# Tạo proxy cho ALMotion
motion_proxy = ALProxy("ALMotion", robot_ip, robot_port)

# Tạo proxy cho ALRobotPosture
posture_proxy = ALProxy("ALRobotPosture", robot_ip, robot_port)

# Đánh thức robot
motion_proxy.wakeUp()

# Đưa robot vào trạng thái đứng
posture_proxy.goToPosture("StandInit", 0.5)

# Optional: Giữ robot ở trạng thái đứng (bật stiff mode)
motion_proxy.setStiffnesses("Body", 1.0)
