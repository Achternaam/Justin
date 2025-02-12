import cv2
import tkinter as tk
from tkinter import ttk

class CameraSettings:
    def __init__(self, camera):
        self.camera = camera
        self.settings = {
            'brightness': (cv2.CAP_PROP_BRIGHTNESS, -64, 64, 0),
            'contrast': (cv2.CAP_PROP_CONTRAST, 0, 100, 50),
            'saturation': (cv2.CAP_PROP_SATURATION, 0, 100, 50),
            'exposure': (cv2.CAP_PROP_EXPOSURE, -13, 0, -6),
            'gain': (cv2.CAP_PROP_GAIN, 0, 100, 50),
            'sharpness': (cv2.CAP_PROP_SHARPNESS, 0, 100, 50)
        }
        
    def create_settings_window(self, parent):
        settings_frame = ttk.LabelFrame(parent, text="Camera Settings")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        for setting_name, (prop_id, min_val, max_val, default) in self.settings.items():
            frame = ttk.Frame(settings_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Label
            ttk.Label(frame, text=f"{setting_name.title()}:").pack(side=tk.LEFT)
            
            # Value label
            value_label = ttk.Label(frame, text=str(default))
            value_label.pack(side=tk.RIGHT, padx=5)
            
            # Slider
            slider = ttk.Scale(frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL)
            slider.set(self.camera.get(prop_id) if self.camera else default)
            slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # Update function
            def update_setting(value, prop_id=prop_id, label=value_label):
                if self.camera:
                    self.camera.set(prop_id, float(value))
                    label.config(text=str(int(float(value))))
            
            slider.configure(command=lambda v, p=prop_id, l=value_label: update_setting(v, p, l))
        
        # Reset button
        ttk.Button(settings_frame, text="Reset to Defaults",
                  command=self.reset_to_defaults).pack(pady=5)
    
    def reset_to_defaults(self):
        """Reset all camera settings to their default values"""
        if self.camera:
            for prop_id, min_val, max_val, default in self.settings.values():
                self.camera.set(prop_id, default)