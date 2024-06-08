# -*- encoding: UTF-8 -*-
from naoqi import ALProxy
import math
import time

# IP và cổng của robot NAO
IP = "127.0.0.1"
PORT = 9559

def Nao_cuidau():

    # Kết nối đến robot
    motionProxy = ALProxy("ALMotion", IP, PORT)

    # Tốc độ di chuyển (0.5 là một ví dụ)
    speed = 0.5

    # Góc ban đầu của HeadYaw và HeadPitch
    initialHeadPitch = 0.0

    # Góc cuối cùng của HeadPitch (ngẩng đầu dần)
    finalHeadPitch = 29*(math.pi/180)  # Ví dụ

    # Số bước chia nhỏ khoảng cách từ góc ban đầu đến góc cuối cùng
    num_steps = 10

    # Tính toán giá trị góc cho từng bước
    step_size = (finalHeadPitch - initialHeadPitch) / num_steps

    # Điều khiển di chuyển khớp đầu
    for i in range(num_steps+1):
        targetPitch = initialHeadPitch + step_size*i
        motionProxy.setAngles(["HeadYaw", "HeadPitch"], [0, targetPitch], speed)

def Nao_stand_up():
    # Kết nối tới dịch vụ ALMotion và ALRobotPosture
    motion_proxy = ALProxy("ALMotion", IP, PORT)
    posture_proxy = ALProxy("ALRobotPosture", IP, PORT)

    # Đưa robot vào tư thế đứng
    posture_proxy.goToPosture("Crouch", 1.0)
    time.sleep(1)
    posture_proxy.goToPosture("Stand", 1.0)
    time.sleep(1)