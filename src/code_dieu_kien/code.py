# -*- encoding: UTF-8 -*-

import argparse
from naoqi import ALProxy

robotIP="127.0.0.1"
PORT=9559

def main():
    motionProxy = ALProxy("ALMotion", robotIP, PORT)

    # Example that finds the difference between the command and sensed angles.
    names         = "Body"
    useSensors    = False
    commandAngles = motionProxy.getAngles(names, useSensors)
    print "Command angles:"
    print str(commandAngles)
    print ""

main()