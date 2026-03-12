# -*- coding: utf-8 -*-
import cv2
import numpy as np

# flag to avoid spamming server warnings
_yo_warned = False

# convenience: image size used by NAO camera

# NAOqi proxy (Python 2)
try:
    from naoqi import ALProxy
except ImportError:
    ALProxy = None
    print("error: naoqi module not available")

# HTTP client used to send frames to the Python 3 YOLO server.
try:
    import requests
except ImportError:
    requests = None
    print("error: requests module not found. install with `pip2 install requests` and restart")
    exit(1)

# helper to make sure YOLO server is running; if not, try to launch it
import subprocess, time

def ensure_yolo_server():
    if requests is None:
        return
    url = "http://127.0.0.1:5000/detect"
    try:
        requests.post(url, files={"image": b""}, timeout=0.5)
    except Exception:
        print("YOLO server not reachable, launching in background...")
        subprocess.Popen(["python3", "YOLO.py"])
        time.sleep(2)

# check at import time
ensure_yolo_server()

import detect_canh

# NAOqi proxy (Python 2)
try:
    from naoqi import ALProxy
except ImportError:
    ALProxy = None
    print("error: naoqi module not available")

# HTTP client used to send frames to the Python 3 YOLO server.
# requests may not be installed in the Python 2 NAOqi environment.
try:
    import requests
except ImportError:
    requests = None
    print("error: requests module not found. install with `pip2 install requests` and restart")
    # without requests the server cannot be contacted, so stop early
    exit(1)

import detect_canh
# YOLO detection is performed by a separate Python 3 server
# the server should be running (e.g. `python3 YOLO.py` in the venv)
# and exposes an HTTP endpoint at /detect


# Thông tin kết nối đến robot
robot_ip = "127.0.0.1"  # Thay bằng địa chỉ IP của robot NAO
robot_port = 9559

# Tạo proxy cho ALVideoDevice
video_proxy = ALProxy("ALVideoDevice", robot_ip, robot_port)

# Chọn camera (0: Top camera, 1: Bottom camera)
cameraIndex = 0  # Thay đổi giá trị này thành 1 để sử dụng Bottom camera
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

def send_to_yolo(frame):
    """Encode frame as JPEG and post to local YOLO server.

    On failure (network error or server not running) the original frame is
    returned and a warning printed once.
    """
    global _yo_warned
    _, buf = cv2.imencode(".jpg", frame)
    try:
        r = requests.post("http://127.0.0.1:5000/detect", files={"image": buf.tobytes()}, timeout=1)
        if r.status_code == 200:
            arr = np.frombuffer(r.content, np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        else:
            if not _yo_warned:
                print("warning: YOLO server returned status", r.status_code)
                _yo_warned = True
    except Exception as e:
        if not _yo_warned:
            print("warning: could not contact YOLO server:", e)
            _yo_warned = True
    return frame

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

            # NAO nominally returns RGB (kRGBColorSpace). OpenCV expects BGR.
            # manually swap channels; if the resulting video is still green,
            # comment out the swap and send `image` itself.
            image_bgr = image[:, :, ::-1]

            # also keep an RGB copy for edge detection / display
            image_rgb = image

            # debug log the first pixel values once to check ordering

            # run custom edge detection on rgb copy
            global x,y,e
            processed, x, y, e = detect_canh.detect_canh(image_rgb)

            # send the BGR frame to the Python 3 YOLO server and display its response
            annotated = send_to_yolo(image_bgr)
            cv2.imshow("YOLO Detect", annotated)

            # show the result of the edge/line detection
            cv2.imshow("Camera", processed)

            # Thoát vòng lặp nếu nhấn phím 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        # Rút đăng ký client video
        video_proxy.unsubscribe(name_id)
        cv2.destroyAllWindows()

def data_canh():
    return x,y,e


if __name__ == "__main__":
    # start the camera loop when the script is executed directly
    Nao_camera_detect()