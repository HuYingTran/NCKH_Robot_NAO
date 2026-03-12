from ultralytics import YOLO
import cv2
import numpy as np
import time
from flask import Flask, request, send_file
import io

model = YOLO("yolov8n.pt")
app = Flask(__name__)

@app.route("/detect", methods=["POST"])
def detect():
    if "image" not in request.files:
        return "No image uploaded", 400

    file = request.files["image"]
    img_bytes = file.read()
    img_array = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    results = model(img)

    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy().astype(int)
        classes = result.boxes.cls.cpu().numpy().astype(int)
        confs = result.boxes.conf.cpu().numpy()

        for box, cls, conf in zip(boxes, classes, confs):
            x1, y1, x2, y2 = box
            area = (x2 - x1) * (y2 - y1)
            label = model.names[cls]
            text = f"{label} {conf:.2f} area: {area}"
            if conf > 0.5 and area > 500: 
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                cv2.rectangle(img,(x1,y1),(x2,y2),(0,0,255),1)
                
    _, buf = cv2.imencode(".jpg", img)
    return send_file(io.BytesIO(buf.tobytes()), mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    