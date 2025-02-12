import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, Scale
import threading
from PIL import Image, ImageTk
import time
import os

class CameraHandler:
    def __init__(self, camera_index):
        self.cap = None
        self.camera_index = camera_index
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self.last_frame_time = 0
        self.frame_interval = 1/30  # 30 FPS maximum

    def start(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                return False
            
            # Set lower resolution for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.running = True
            threading.Thread(target=self._update_frame, daemon=True).start()
        return True

    def _update_frame(self):
        while self.running:
            current_time = time.time()
            # Only capture new frame if enough time has passed
            if current_time - self.last_frame_time >= self.frame_interval:
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.frame = frame
                        self.last_frame_time = current_time
            time.sleep(0.01)  # Small sleep to prevent CPU overload

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

class CameraSettings:
    def __init__(self, camera):
        self.camera = camera
        self.window = None
        self.settings = {
            'Brightness': (cv2.CAP_PROP_BRIGHTNESS, -64, 64, 0),
            'Contrast': (cv2.CAP_PROP_CONTRAST, 0, 100, 50),
            'Saturation': (cv2.CAP_PROP_SATURATION, 0, 100, 50),
            'Exposure': (cv2.CAP_PROP_EXPOSURE, -13, 0, -6),
            'Gain': (cv2.CAP_PROP_GAIN, 0, 100, 50),
            'Focus': (cv2.CAP_PROP_FOCUS, 0, 255, 128)
        }

    def show_settings_window(self):
        if self.window is None or not self.window.winfo_exists():
            self.window = tk.Toplevel()
            self.window.title("Camera Settings")
            self.create_settings_controls()

    def create_settings_controls(self):
        for name, (prop_id, min_val, max_val, default) in self.settings.items():
            frame = ttk.Frame(self.window)
            frame.pack(fill='x', padx=5, pady=2)
            
            ttk.Label(frame, text=name).pack(side='left')
            
            current_value = self.camera.get(prop_id)
            scale = Scale(frame, from_=min_val, to=max_val, orient='horizontal',
                        command=lambda v, p=prop_id: self.update_setting(p, float(v)))
            scale.set(current_value)
            scale.pack(side='right', fill='x', expand=True)

    def update_setting(self, prop_id, value):
        self.camera.set(prop_id, value)

class DartboardCalibration:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Genius Darts Software")
        self.root.geometry("1280x720")

        # Set window icon
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.ico')
            self.root.iconbitmap(logo_path)
        except Exception as e:
            print(f"Could not load icon: {e}")

        self.camera_handlers = [None, None, None]
        self.active_cameras = set()
        self.is_calibrated = False
        self.camera_dropdowns = []  # Store dropdown references
        
        self.setup_ui()
        self.update_interval = 50  # Update UI every 50ms (20 FPS)
        self.find_cameras()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill='both', expand=True)

        # Camera selection
        selection_frame = ttk.LabelFrame(main_frame, text="Camera Selection", padding=5)
        selection_frame.pack(fill='x', pady=5)

        self.camera_vars = []
        for i in range(3):
            frame = ttk.Frame(selection_frame)
            frame.pack(fill='x', pady=2)
            
            ttk.Label(frame, text=f"Camera {i+1}:").pack(side='left')
            var = tk.StringVar()
            self.camera_vars.append(var)
            dropdown = ttk.Combobox(frame, textvariable=var)
            dropdown.pack(side='left', padx=5)
            self.camera_dropdowns.append(dropdown)  # Store dropdown reference
            
            # Start/Stop button per camera
            self.create_camera_controls(frame, i)

        # Camera views
        views_frame = ttk.LabelFrame(main_frame, text="Camera Views", padding=5)
        views_frame.pack(fill='both', expand=True, pady=5)

        self.camera_labels = []
        self.rotation_vars = []
        for i in range(3):
            frame = ttk.Frame(views_frame)
            frame.grid(row=0, column=i, padx=5, pady=5)

            # Camera view
            label = ttk.Label(frame)
            label.pack()
            self.camera_labels.append(label)

            # Rotation control
            rot_frame = ttk.Frame(frame)
            rot_frame.pack(fill='x', pady=5)
            ttk.Label(rot_frame, text="Rotation:").pack(side='left')
            rotation_var = tk.IntVar(value=0)
            self.rotation_vars.append(rotation_var)
            Scale(rot_frame, from_=0, to=359, variable=rotation_var,
                  orient='horizontal').pack(side='left', fill='x', expand=True)

        # Status
        self.status_label = ttk.Label(main_frame, text="Select and start cameras")
        self.status_label.pack(fill='x', pady=5)

    def create_camera_controls(self, parent, camera_index):
        control_frame = ttk.Frame(parent)
        control_frame.pack(side='right')

        # Start/Stop button
        self.create_toggle_button(control_frame, camera_index)

        # Settings button
        ttk.Button(control_frame, text="Settings",
                  command=lambda: self.show_camera_settings(camera_index)).pack(side='right', padx=2)

    def create_toggle_button(self, parent, camera_index):
        btn = ttk.Button(parent, text="Start",
                        command=lambda: self.toggle_camera(camera_index, btn))
        btn.pack(side='right', padx=2)

    def toggle_camera(self, camera_index, button):
        if camera_index not in self.active_cameras:
            # Start camera
            if self.start_camera(camera_index):
                button.configure(text="Stop")
                self.active_cameras.add(camera_index)
        else:
            # Stop camera
            self.stop_camera(camera_index)
            button.configure(text="Start")
            self.active_cameras.remove(camera_index)

    def start_camera(self, camera_index):
        try:
            camera_name = self.camera_vars[camera_index].get()
            if not camera_name:
                return False

            index = int(camera_name.split()[-1])
            handler = CameraHandler(index)
            if handler.start():
                self.camera_handlers[camera_index] = handler
                return True
            return False
        except Exception as e:
            self.status_label.config(text=f"Error starting camera: {str(e)}")
            return False

    def stop_camera(self, camera_index):
        if self.camera_handlers[camera_index]:
            self.camera_handlers[camera_index].stop()
            self.camera_handlers[camera_index] = None
            # Clear the camera view
            self.camera_labels[camera_index].configure(image='')

    def update_camera_views(self):
        """Update all active camera views"""
        for i in self.active_cameras:
            handler = self.camera_handlers[i]
            if handler:
                frame = handler.get_frame()
                if frame is not None:
                    # Apply rotation
                    if self.rotation_vars[i].get() != 0:
                        center = (frame.shape[1] // 2, frame.shape[0] // 2)
                        matrix = cv2.getRotationMatrix2D(center, self.rotation_vars[i].get(), 1.0)
                        frame = cv2.warpAffine(frame, matrix, (frame.shape[1], frame.shape[0]))

                    # Convert and resize for display
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (400, 300))
                    img = Image.fromarray(frame)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.camera_labels[i].imgtk = imgtk
                    self.camera_labels[i].configure(image=imgtk)

        # Schedule next update
        self.root.after(self.update_interval, self.update_camera_views)

    def find_cameras(self):
        """Find available cameras"""
        available_cameras = []
        for i in range(5):  # Only check first 5 cameras for performance
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                cap.release()

        camera_list = [f"Camera {i}" for i in available_cameras]
        for dropdown in self.camera_dropdowns:
            dropdown['values'] = camera_list

    def show_camera_settings(self, camera_index):
        handler = self.camera_handlers[camera_index]
        if handler and handler.cap:
            settings = CameraSettings(handler.cap)
            settings.show_settings_window()

    def run(self):
        self.update_camera_views()
        self.root.mainloop()

    def cleanup(self):
        for i in range(3):
            self.stop_camera(i)

if __name__ == "__main__":
    app = DartboardCalibration()
    try:
        app.run()
    finally:
        app.cleanup()