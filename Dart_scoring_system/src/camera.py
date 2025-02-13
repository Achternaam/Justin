import cv2
import json
import numpy as np
import logging
from threading import Thread, Lock
import time
import os

logger = logging.getLogger('dart_scorer.camera')

class Camera:
    """Klasse voor individuele camera handling"""
    def __init__(self, camera_id, config):
        self.camera_id = camera_id
        self.config = config
        self.cap = None
        self.is_running = False
        self.frame_buffer = []
        self.buffer_lock = Lock()
        self.last_frame = None
        self.frame_count = 0
        
    def initialize(self):
        """Initialize de camera met gegeven configuratie"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            # Stel resolutie in
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 
                        self.config['resolution']['width'])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 
                        self.config['resolution']['height'])
            
            # Stel camera parameters in
            self.cap.set(cv2.CAP_PROP_EXPOSURE, 
                        self.config['settings']['exposure'])
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 
                        self.config['settings']['brightness'])
            self.cap.set(cv2.CAP_PROP_CONTRAST, 
                        self.config['settings']['contrast'])
            self.cap.set(cv2.CAP_PROP_FPS, 
                        self.config['settings']['fps'])
            
            if not self.cap.isOpened():
                raise Exception(f"Kon camera {self.camera_id} niet openen")
                
            logger.info(f"Camera {self.camera_id} succesvol geïnitialiseerd")
            return True
            
        except Exception as e:
            logger.error(f"Error bij initialiseren camera {self.camera_id}: {str(e)}")
            return False
            
    def start(self):
        """Start de camera capture thread"""
        if not self.is_running:
            self.is_running = True
            self.capture_thread = Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            logger.info(f"Camera {self.camera_id} capture gestart")
            
    def stop(self):
        """Stop de camera capture"""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join()
        if self.cap:
            self.cap.release()
        logger.info(f"Camera {self.camera_id} capture gestopt")
            
    def _capture_loop(self):
        """Main capture loop die in een aparte thread draait"""
        while self.is_running:
            if self.cap is None:
                continue
                
            ret, frame = self.cap.read()
            if not ret:
                logger.warning(f"Kon geen frame lezen van camera {self.camera_id}")
                continue
                
            # Pas ROI toe als geconfigureerd
            roi = self.config['roi']
            if roi['width'] > 0 and roi['height'] > 0:
                frame = frame[roi['y']:roi['y']+roi['height'],
                            roi['x']:roi['x']+roi['width']]
                
            # Update frame buffer
            with self.buffer_lock:
                self.frame_buffer.append(frame)
                if len(self.frame_buffer) > self.config.get('frame_buffer_size', 10):
                    self.frame_buffer.pop(0)
                self.last_frame = frame
                self.frame_count += 1
                
            # Kleine pauze om CPU gebruik te beperken
            time.sleep(1/self.config['settings']['fps'])
            
    def get_latest_frame(self):
        """Haal het meest recente frame op"""
        with self.buffer_lock:
            return self.last_frame.copy() if self.last_frame is not None else None
            
    def get_frame_buffer(self):
        """Haal de hele frame buffer op"""
        with self.buffer_lock:
            return self.frame_buffer.copy()
            
class CameraManager:
    """Klasse voor het beheren van meerdere camera's"""
    def __init__(self, config_path='config/camera_config.json'):
        self.config_path = config_path
        self.cameras = {}
        self.load_config()
        
    def load_config(self):
        """Laad camera configuratie uit JSON bestand"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Camera config bestand niet gevonden: {self.config_path}")
                return
                
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
                logger.info("Camera configuratie succesvol geladen")
                
        except Exception as e:
            logger.error(f"Error bij laden camera config: {str(e)}")
            self.config = None
            
    def initialize_cameras(self, camera_ids):
        """Initialize alle camera's met gegeven IDs"""
        for cam_name, camera_id in camera_ids.items():
            if cam_name in self.config['cameras']:
                # Update camera ID in config
                self.config['cameras'][cam_name]['id'] = int(camera_id)
                camera_config = self.config['cameras'][cam_name]
                
                # Maak nieuwe camera instance
                camera = Camera(int(camera_id), camera_config)
                if camera.initialize():
                    self.cameras[cam_name] = camera
                    
        self.save_config()
        
    def save_config(self):
        """Sla huidige camera configuratie op"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Camera configuratie opgeslagen")
        except Exception as e:
            logger.error(f"Error bij opslaan camera config: {str(e)}")
            
    def start_all_cameras(self):
        """Start alle geïnitialiseerde camera's"""
        for camera in self.cameras.values():
            camera.start()
            
    def stop_all_cameras(self):
        """Stop alle camera's"""
        for camera in self.cameras.values():
            camera.stop()
            
    def get_frames(self):
        """Haal frames op van alle camera's"""
        frames = {}
        for cam_name, camera in self.cameras.items():
            frames[cam_name] = camera.get_latest_frame()
        return frames