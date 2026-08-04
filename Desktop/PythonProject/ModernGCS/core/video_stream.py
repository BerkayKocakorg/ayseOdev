import threading
import time
import cv2
import numpy as np

# YOLO availability is determined later
_YOLO_AVAILABLE_CACHE = None

class VideoStream:
    """
    Video stream handler with optional YOLOv8 object detection and target tracking.
    
    Features:
    - OpenCV video capture from camera index, RTSP URL, or video file
    - YOLOv8 real-time object detection (graceful fallback if not installed)
    - Target tracking: click on a detected object to lock and track it
    - Thread-safe frame delivery via callback
    - FPS measurement
    """
    
    def __init__(self):
        self.cap = None
        self.running = False
        self.thread = None
        self.source = 0  # Default: first camera
        
        # Detection
        self.detection_enabled = False
        self.model = None
        self.detections = []  # List of detected objects: [{"label", "confidence", "bbox"}]
        self._detection_lock = threading.Lock()
        
        # Tracking
        self.tracking_enabled = False
        self.tracker = None
        self.track_bbox = None  # (x, y, w, h)
        self.track_label = ""
        self._tracking_initialized = False
        
        # Performance
        self.fps = 0.0
        self._frame_count = 0
        self._fps_time = time.time()
        
        # Callback: called with (frame, detections, track_bbox) on each frame
        self.on_frame = None
        
        # Try to load YOLO model asynchronously
        self.model = None
        threading.Thread(target=self._load_yolo_model, daemon=True).start()

    def _load_yolo_model(self):
        """Load YOLO model in background thread, including the heavy import."""
        try:
            print("[INFO] Importing ultralytics in background...")
            from ultralytics import YOLO
            print("[INFO] Loading YOLOv8 model...")
            self.model = YOLO("yolov8n.pt")
            print("[INFO] YOLOv8 model loaded successfully")
        except ImportError:
            print("[WARN] ultralytics not installed. Object detection disabled.")
            self.model = None
        except Exception as e:
            print(f"[WARN] Failed to load YOLOv8 model: {e}")
            self.model = None
    
    def set_source(self, source):
        """
        Set video source.
        - int: camera index (0, 1, 2...)
        - str: RTSP URL or video file path
        """
        was_running = self.running
        if was_running:
            self.stop()
        
        self.source = source
        
        if was_running:
            self.start()
    
    def start(self):
        """Start video capture in background thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop video capture."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
    
    def enable_detection(self, enabled=True):
        """Enable/disable YOLOv8 object detection."""
        if enabled and self.model is None:
            print("[WARN] Cannot enable detection: YOLO model not loaded or ultralytics not installed")
            return
        self.detection_enabled = enabled
    
    def start_tracking(self, frame, bbox):
        """
        Start tracking an object at the given bounding box.
        bbox: (x, y, w, h)
        """
        try:
            self.tracker = cv2.TrackerCSRT_create()
            self.tracker.init(frame, tuple(bbox))
            self.track_bbox = bbox
            self.tracking_enabled = True
            self._tracking_initialized = True
        except Exception as e:
            print(f"[WARN] Tracker init failed: {e}")
            self.tracking_enabled = False
    
    def stop_tracking(self):
        """Stop target tracking."""
        self.tracking_enabled = False
        self.tracker = None
        self.track_bbox = None
        self._tracking_initialized = False
    
    def _capture_loop(self):
        """Main capture loop running in background thread."""
        try:
            self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                print(f"[ERROR] Cannot open video source: {self.source}")
                self.running = False
                return
            
            self._fps_time = time.time()
            self._frame_count = 0
            
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    # If reading a video file, loop back to start
                    if isinstance(self.source, str) and not self.source.startswith("rtsp"):
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    time.sleep(0.01)
                    continue
                
                detections = []
                track_bbox = None
                
                # YOLOv8 Detection
                if self.detection_enabled and self.model:
                    try:
                        results = self.model(frame, verbose=False, conf=0.5)
                        for r in results:
                            for box in r.boxes:
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                                conf = float(box.conf[0])
                                cls_id = int(box.cls[0])
                                label = self.model.names.get(cls_id, f"class_{cls_id}")
                                
                                detections.append({
                                    "label": label,
                                    "confidence": conf,
                                    "bbox": (x1, y1, x2 - x1, y2 - y1),  # (x, y, w, h)
                                    "bbox_xyxy": (x1, y1, x2, y2)
                                })
                    except Exception as e:
                        pass
                
                with self._detection_lock:
                    self.detections = detections
                
                # Target Tracking
                if self.tracking_enabled and self.tracker and self._tracking_initialized:
                    try:
                        success, bbox = self.tracker.update(frame)
                        if success:
                            self.track_bbox = tuple(int(v) for v in bbox)
                            track_bbox = self.track_bbox
                        else:
                            # Lost track
                            self.stop_tracking()
                    except Exception:
                        self.stop_tracking()
                
                # FPS Calculation
                self._frame_count += 1
                elapsed = time.time() - self._fps_time
                if elapsed >= 1.0:
                    self.fps = self._frame_count / elapsed
                    self._frame_count = 0
                    self._fps_time = time.time()
                
                # Deliver frame via callback
                if self.on_frame:
                    try:
                        self.on_frame(frame, detections, track_bbox)
                    except Exception:
                        pass
                
                time.sleep(0.01)  # ~100 FPS max, limited by camera
                
        except Exception as e:
            print(f"[ERROR] Video capture error: {e}")
        finally:
            if self.cap:
                self.cap.release()
            self.running = False
    
    def get_current_detections(self):
        """Get the latest detection results (thread-safe)."""
        with self._detection_lock:
            return list(self.detections)
