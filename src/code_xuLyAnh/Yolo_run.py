import cv2
import numpy as np
import subprocess
import time
from naoqi import ALProxy
import requests

ROBOT_IP = "127.0.0.1"
ROBOT_PORT = 9559
YOLO_URL = "http://127.0.0.1:5000/detect"

def send_to_yolo(frame):

    _, buf = cv2.imencode(".jpg", frame) #image -> JPG 

    try:
        r = requests.post(
            YOLO_URL,
            files={"image": buf.tobytes()},
            timeout=1
        )

        if r.status_code == 200: #200 OK, 500 Server error, 404 Not found
            arr = np.frombuffer(r.content, np.uint8) #JPG -> Array 1D
            result = cv2.imdecode(arr, cv2.IMREAD_COLOR) #Array 1D -> image
            return result
        else:
            print("YOLO server error:", r.status_code)

    except Exception as e:
        print("YOLO connection error:", e)

    return frame

def init_camera():

    video_proxy = ALProxy("ALVideoDevice", ROBOT_IP, ROBOT_PORT)
    camera_index = 0  #top camera
    resolution = 2   # 640x480
    color_space = 13 # 11 for RGB, 13 for BGR
    fps = 30

    video_proxy.setActiveCamera(camera_index)

    name_id = video_proxy.subscribe(
        "python_client",
        resolution,
        color_space,
        fps
    )

    return video_proxy, name_id

def run_camera():

    video_proxy, name_id = init_camera()

    try:

        while True:

            image_container = video_proxy.getImageRemote(name_id)
            #getImageRmote returns a tuple with 
            #0 width, 1 height, 2 number of layers, 3 color space, 4 timestamp, 5 camera id , 6 image data

            if image_container is None:
                print("Cannot capture image")
                continue

            width = image_container[0]
            height = image_container[1]
            array = image_container[6]
            
            image = np.frombuffer(array, dtype=np.uint8).reshape((height, width, 3))
            result = send_to_yolo(image)
            
            cv2.imshow("YOLO detect", result)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:

        video_proxy.unsubscribe(name_id)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run_camera()
