import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.camera_utils import CameraManager, detect_dartboard

class CameraTest:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dart Camera Test")
        self.root.geometry("800x600")
        
        # Initialize camera manager
        self.camera_manager = CameraManager()
        
        # Try to open the first available camera
        available_cameras = self.camera_manager.get_available_cameras()
        if not available_cameras:
            raise ValueError("No cameras found!")
            
        first_camera = list(available_cameras.values())[0]['index']
        self.camera = cv2.VideoCapture(first_camera)
        
        # Create UI elements
        self.setup_ui()
        
        # Start update loop
        self.update_frame()
        
    def setup_ui(self):
        # Camera feed display
        self.display_label = ttk.Label(self.root)
        self.display_label.pack(padx=10, pady=10)
        
        # Status display
        self.status_label = ttk.Label(self.root, text="Testing camera...")
        self.status_label.pack(pady=10)
        
        # Available cameras display
        cameras = self.camera_manager.get_available_cameras()
        camera_frame = ttk.LabelFrame(self.root, text="Available Cameras")
        camera_frame.pack(pady=10, padx=10, fill="x")
        
        for cam_id, cam_info in cameras.items():
            ttk.Label(camera_frame, 
                     text=f"Camera {cam_id}: {cam_info['resolution'][0]}x{cam_info['resolution'][1]} @ {cam_info['fps']:.1f}fps"
            ).pack(padx=5, pady=2)
    
    def update_frame(self):
        ret, frame = self.camera.read()
        if ret:
            # Try to detect dartboard
            circle = detect_dartboard(frame)
            if circle is not None:
                # Draw detected dartboard
                cv2.circle(frame, (circle[0], circle[1]), circle[2], (0, 255, 0), 2)
                self.status_label.config(text="Dartboard detected!")
            else:
                self.status_label.config(text="No dartboard detected - adjust camera position")
            
            # Convert frame for display
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (640, 480))
            
            # Update display
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.display_label.imgtk = imgtk
            self.display_label.configure(image=imgtk)
        else:
            self.status_label.config(text="Error reading from camera!")
        
        self.root.after(10, self.update_frame)
    
    def run(self):
        self.root.mainloop()
    
    def cleanup(self):
        if self.camera.isOpened():
            self.camera.release()
        self.camera_manager.stop()

if __name__ == "__main__":
    test = CameraTest()
    try:
        test.run()
    finally:
        test.cleanup()