import cv2
from yolov5 import YOLOv5
import numpy as np
import time
import warnings

# Suppress PyTorch deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning)

class BulletDetector:
    def __init__(self, camera_source="0"):
        # Load YOLOv5 model
        self.model = YOLOv5('static/models/best_yolo.pt')  # Your custom trained model
        self.classes = ['bullet', 'bullet_out']
        self.colors = [(0, 255, 0), (0, 0, 255)]  # Green for bullet, Red for bullet_out
        self.camera = None
        self.initial_boxes = None
        self.IOU_THRESHOLD = 0.3  # Adjust as needed
        self.camera_source = camera_source  # Default to "0" (webcam), updated dynamically
        self.max_reconnect_attempts = 3  # Number of reconnection attempts
        self.last_camera_source = camera_source  # Suivre la dernière source utilisée
    
    @staticmethod
    def compute_iou(box1, box2):
        """Calculate Intersection over Union (IoU) between two boxes"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union_area = area1 + area2 - inter_area
        
        return inter_area / union_area if union_area != 0 else 0

    def initialize_camera(self):
        """Initialize the camera stream based on camera_source (index or URL)"""
        if self.camera is not None and self.camera.isOpened():
            self.camera.release()

        # Check if camera_source is an index (e.g., "0") or a URL (e.g., "rtsp://...")
        try:
            # If camera_source is a number, treat it as an index
            camera_index = int(self.camera_source)
            print(f"Attempting to connect to webcam with index: {camera_index}")
            self.camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # Use CAP_DSHOW for webcam
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering
            self.camera.set(cv2.CAP_PROP_FPS, 15)  # Set reasonable FPS
        except ValueError:
            # If camera_source is not a number, treat it as a URL (MJPEG, RTSP, etc.)
            print(f"Attempting to connect to camera stream at: {self.camera_source}")
            self.camera = cv2.VideoCapture(self.camera_source, cv2.CAP_FFMPEG)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering for MJPEG/RTSP
            self.camera.set(cv2.CAP_PROP_FPS, 15)  # Set reasonable FPS
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # Force MJPEG codec
            self.camera.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 60000)  # 60-second timeout

        time.sleep(0.5)  # Allow camera to initialize
        if not self.camera.isOpened():
            print(f"Error: Could not open camera at {self.camera_source}")
            return False
        print(f"Successfully connected to camera: {self.camera_source}")
        self.last_camera_source = self.camera_source  # Mettre à jour la dernière source utilisée
        return True

    def release_camera(self):
        """Release camera resources"""
        if self.camera is not None and self.camera.isOpened():
            self.camera.release()

    def close_camera(self):
        """Close the camera if open"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        
    def capture_single_frame(self, detection_state):
        """Capture a single frame from the camera stream"""
        # Vérifier si la source a changé
        if 'camera_source' in detection_state:
            new_source = detection_state['camera_source']
            if new_source != self.last_camera_source:
                self.camera_source = new_source
                self.close_camera()  # Fermer l'ancienne caméra
                self.initialize_camera()  # Réinitialiser avec la nouvelle source
        
        attempt = 0
        while attempt < self.max_reconnect_attempts:
            if not self.initialize_camera():
                attempt += 1
                print(f"Reconnection attempt {attempt}/{self.max_reconnect_attempts}")
                time.sleep(1)
                continue
                
            success, frame = self.camera.read()
            if success:
                return frame
            else:
                print(f"Warning: Failed to read frame from camera at {self.camera_source}")
                self.close_camera()
                attempt += 1
                time.sleep(1)
        
        print("Error: Max reconnection attempts reached")
        self.close_camera()
        return None

    def process_frame(self, frame, detection_state):
        """Process a single frame for bullet detection"""
        if frame is None:
            return None
            
        # Perform detection
        results = self.model.predict(frame)
        detections = results.pred[0]
        
        bullet_count = 0
        
        if self.initial_boxes is None:
            # First frame: store initial boxes
            self.initial_boxes = []
            for det in detections:
                x1, y1, x2, y2, conf, cls = det
                if conf > 0.3:
                    self.initial_boxes.append((
                        x1.item(), 
                        y1.item(), 
                        x2.item(), 
                        y2.item()
                    ))
        else:
            # Filter new boxes
            for det in detections:
                x1, y1, x2, y2, conf, cls = det
                if conf <= 0.3:
                    continue
                    
                # Convert coordinates
                current_box = (
                    x1.item(), 
                    y1.item(), 
                    x2.item(), 
                    y2.item()
                )
                
                # Check if it's a new detection
                is_new = True
                for init_box in self.initial_boxes:
                    iou = self.compute_iou(current_box, init_box)
                    if iou > self.IOU_THRESHOLD:
                        is_new = False
                        break
                
                if is_new:
                    # Draw and count
                    label = f"{self.classes[int(cls)]} {conf:.2f}"
                    color = self.colors[int(cls)]
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    if self.classes[int(cls)] == 'bullet':
                        bullet_count += 1

        # Update counter (0 for first frame)
        detection_state['bullets_detected'] = bullet_count
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        return frame_bytes

    def generate_frames(self, detection_state, interval=0.5):
        """Generate frames with new detection management"""
        try:
            self.initial_boxes = None  # Reset at start
            while detection_state['active']:
                # Vérifier si la source a changé
                if 'camera_source' in detection_state:
                    new_source = detection_state['camera_source']
                    if new_source != self.last_camera_source:
                        self.camera_source = new_source
                        self.close_camera()  # Fermer l'ancienne caméra
                        self.initialize_camera()  # Réinitialiser avec la nouvelle source
                
                frame = self.capture_single_frame(detection_state)
                frame_bytes = self.process_frame(frame, detection_state)
                
                if frame_bytes is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(interval)
        except Exception as e:
            print(f"Error in generate_frames: {e}")
        finally:
            self.close_camera()

    def take_snapshot(self, detection_state):
        """Take a single snapshot and process it"""
        # Vérifier si la source a changé
        if 'camera_source' in detection_state:
            new_source = detection_state['camera_source']
            if new_source != self.last_camera_source:
                self.camera_source = new_source
                self.close_camera()  # Fermer l'ancienne caméra
                self.initialize_camera()  # Réinitialiser avec la nouvelle source
            
        frame = self.capture_single_frame(detection_state)
        result = self.process_frame(frame, detection_state)
        self.close_camera()
        return result