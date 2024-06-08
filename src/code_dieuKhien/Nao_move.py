# -*- encoding: UTF-8 -*-
from naoqi import ALProxy
import time

# IP và cổng của robot NAO
IP = "127.0.0.1"
PORT = 9559

def Nao_tienThang(x,y,theta):
    motionProxy = ALProxy("ALMotion", IP, PORT)
    postureProxy = ALProxy("ALRobotPosture", IP, PORT)

    frequency = 1.0
    motionProxy.moveToward(x, y, theta, [["Frequency", frequency]])
    # time.sleep(3)
    # motionProxy.stopMove()