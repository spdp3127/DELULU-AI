import os
import time
from core.skill import Skill

class DetectionSkill(Skill):
    """
    Skill for detecting objects using YOLOv8 with Windows CUDA and CPU support.
    """
    
    def __init__(self):
        self.model = None
        self.device = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
        except Exception:
            self.device = "cpu"
        print(f"DetectionSkill: Configured device '{self.device}'")

    @property
    def name(self):
        return "detection_skill"

    def _load_model(self):
        if self.model is None:
            print("Loading YOLOv8 model...")
            try:
                from ultralytics import YOLO
                model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "yolov8n.pt")
                if not os.path.exists(model_path):
                    model_path = "yolov8n.pt"
                self.model = YOLO(model_path)
                self.model.to(self.device)
                print("YOLOv8 model loaded successfully.")
            except Exception as e:
                print(f"Error loading YOLO model: {e}")
                self.model = None

    def get_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "detect_objects",
                    "description": "Detect objects in the current room/view using the camera and computer vision.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
        ]

    def get_functions(self):
        return {
            "detect_objects": self.detect_objects
        }

    def detect_objects(self, **kwargs):
        """Captures a camera frame and runs YOLO object detection."""
        try:
            import cv2
        except ImportError:
            return "OpenCV (cv2) is not installed on this machine."

        try:
            self._load_model()
            if not self.model:
                return "YOLOv8 model could not be loaded."

            # Open camera (DirectShow on Windows for fast opening)
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(0)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                return "Error: Could not access camera."

            time.sleep(0.5)
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                return "Error: Failed to capture camera frame."

            results = self.model(frame, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = self.model.names[cls_id]
                    detections.append(f"{label} ({int(conf * 100)}%)")

            if not detections:
                return "Scan complete. No prominent objects detected in view, Sir."

            # Save annotated image
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
            os.makedirs(assets_dir, exist_ok=True)
            timestamp = int(time.time())
            filepath = os.path.join(assets_dir, f"detection_{timestamp}.jpg")

            annotated_frame = results[0].plot()
            cv2.imwrite(filepath, annotated_frame)

            return f"Objects detected: {', '.join(detections)}. Frame archived to {filepath}"

        except Exception as e:
            return f"Error during vision scan: {e}"
