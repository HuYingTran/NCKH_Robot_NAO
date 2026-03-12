from ultralytics import YOLO
import cv2
import numpy as np

# load YOLO model once
model = YOLO("yolov8n.pt")


def detect_frame(frame):
    """Run YOLO on a single OpenCV frame and return annotated image."""
    results = model(frame)
    annotated = results[0].plot()
    return annotated


def nao_camera_loop(robot_ip="127.0.0.1", robot_port=9559, camera_index=1):
    """Fetch frames from a NAO robot and show YOLO output locally.

    Requires the NAOqi Python bindings to be importable in this interpreter.
    """
    try:
        from naoqi import ALProxy
    except ImportError:
        print("NAOqi bindings not available in this environment")
        return

    video = ALProxy("ALVideoDevice", robot_ip, robot_port)
    video.setActiveCamera(camera_index)
    uid = video.subscribe("py3_yolo", 2, 11, 30)
    try:
        import cv2
        import numpy as np
        while True:
            img = video.getImageRemote(uid)
            if img is None:
                continue
            w, h = img[0], img[1]
            arr = img[6]
            frame = np.frombuffer(arr, np.uint8).reshape((h, w, 3))
            annotated = detect_frame(frame)
            cv2.imshow("YOLO NAO", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        video.unsubscribe(uid)
        cv2.destroyAllWindows()


# HTTP server for Python2 client (NAO) ------------------------------------
try:
    from flask import Flask, request
except ImportError:
    Flask = None
    print("warning: Flask not installed; install via `pip install flask` to enable HTTP server")

app = Flask(__name__) if Flask is not None else None

if app is not None:
    @app.route("/detect", methods=["POST"])
    def detect():
        file = request.files.get("image")
        if file is None:
            return "no image", 400
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        annotated = detect_frame(frame)
        _, buf = cv2.imencode(".jpg", annotated)
        return buf.tobytes(), 200, {"Content-Type": "image/jpeg"}

    def run_server():
        # start Flask server (use python3 venv)
        print("starting YOLO HTTP server on port 5000")
        app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="YOLO runner: HTTP server or NAO camera demo."
    )
    parser.add_argument("--mode", choices=["server", "nao"], default="server",
                        help="`server` runs HTTP API; `nao` pulls from a NAO robot")
    parser.add_argument("--nao-ip", default="127.0.0.1", help="NAO robot IP")
    parser.add_argument("--nao-port", type=int, default=9559, help="NAO robot port")
    parser.add_argument("--camera", type=int, default=1, help="NAO camera index (0 top,1 bottom)")
    args = parser.parse_args()

    if args.mode == "server":
        if app is not None:
            run_server()
        else:
            print("YOLO module started without Flask; no server will run.")
    else:
        # nao demo
        nao_camera_loop(robot_ip=args.nao_ip,
                        robot_port=args.nao_port,
                        camera_index=args.camera)
