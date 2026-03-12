from ultralytics import YOLO
import os

print("Current working directory:", os.getcwd())

model = YOLO("yolov8n.pt")

model.train(
    data="data.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    workers=4,
    device="cuda", 
    verbose=True
)