import cv2
import numpy as np
import time
from threading import Thread, Lock

class CameraManager:
    def __init__(self):
        self.available_cameras = {}  # Dictionary met camera info
        self.camera_lock = Lock()
        self.running = True
        self.callbacks = []  # Voor notificaties bij camera veranderingen
        
        # Start camera monitoring in aparte thread
        self.monitor_thread = Thread(target=self._monitor_cameras, daemon=True)
        self.monitor_thread.start()
    
    def _monitor_cameras(self):
        """Continue monitoring voor cameras"""
        while self.running:
            try:
                # Scan alle video devices
                for i in range(10):  # Check eerste 10 indices
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret:
                            # Camera info verzamelen
                            camera_info = {
                                'index': i,
                                'name': f"Camera {i}",
                                'resolution': (
                                    int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                    int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                ),
                                'fps': cap.get(cv2.CAP_PROP_FPS)
                            }
                            
                            with self.camera_lock:
                                if i not in self.available_cameras:
                                    self.available_cameras[i] = camera_info
                                    self._notify_camera_change()
                        cap.release()
                    else:
                        # Verwijder camera als deze niet meer beschikbaar is
                        with self.camera_lock:
                            if i in self.available_cameras:
                                del self.available_cameras[i]
                                self._notify_camera_change()
                
                time.sleep(1)  # Check elke seconde voor veranderingen
                
            except Exception as e:
                print(f"Fout bij camera monitoring: {e}")
                time.sleep(1)
    
    def get_available_cameras(self):
        """Krijg lijst met beschikbare camera's"""
        with self.camera_lock:
            return self.available_cameras.copy()
    
    def add_callback(self, callback):
        """Voeg callback toe voor camera veranderingen"""
        self.callbacks.append(callback)
    
    def _notify_camera_change(self):
        """Notificeer alle callbacks van camera veranderingen"""
        for callback in self.callbacks:
            try:
                callback(self.available_cameras.copy())
            except Exception as e:
                print(f"Fout in camera change callback: {e}")
    
    def stop(self):
        """Stop de camera monitoring"""
        self.running = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()

def detect_dartboard(frame):
    """Detect dartbord in frame met Hough circles"""
    if frame is None:
        return None
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,
        param1=50,
        param2=30,
        minRadius=100,
        maxRadius=300
    )
    
    if circles is not None:
        circles = np.uint16(np.around(circles))
        return circles[0][0]  # Return first detected circle
    return None

def calculate_dart_position(frame, board_center, board_radius):
    """Detect dart positie in frame"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Define color range for dart detection
    lower_dart = np.array([0, 0, 200])
    upper_dart = np.array([180, 30, 255])
    
    mask = cv2.inRange(hsv, lower_dart, upper_dart)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    dart_positions = []
    for contour in contours:
        if cv2.contourArea(contour) > 100:
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                dart_positions.append((cx, cy))
    
    return dart_positions