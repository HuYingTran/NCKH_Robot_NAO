from naoqi import ALProxy

motion = ALProxy("ALMotion","127.0.0.1",9559)
posture = ALProxy("ALRobotPosture","127.0.0.1",9559)

motion.setStiffnesses("Body",1.0)

posture.goToPosture("StandInit",0.5)

motion.wbEnable(True)

motion.wbFootState("Fixed","LLeg")
motion.wbFootState("Free","RLeg")

motion.wbEnableBalanceConstraint(True,"LLeg")

target = [0.0,0.0,0.04,0,0,0]

motion.positionInterpolation(
    "RLeg",
    0,
    target,
    63,
    1.0,
    False
)