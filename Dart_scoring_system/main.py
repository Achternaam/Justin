import os
os.environ['TK_SILENCE_DEPRECATION'] = "1"

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import json
from PIL import Image, ImageTk
import numpy as np

class DartScorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dart Scorer")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a75ff')  # Blauwe achtergrond

        # Camera variabelen
        self.cameras = {
            'camera1': {'id': None, 'cap': None, 'rotation': 0, 'last_frame': None},
            'camera2': {'id': None, 'cap': None, 'rotation': 0, 'last_frame': None},
            'camera3': {'id': None, 'cap': None, 'rotation': 0, 'last_frame': None}
        }

        # Hoofdframe
        self.main_frame = tk.Frame(self.root, bg='#1a75ff', padx=20, pady=20)
        self.main_frame.pack(expand=True, fill='both')

        # Setup GUI elementen
        self.setup_preview_section()
        self.setup_control_section()
        self.setup_continue_button()

    def setup_preview_section(self):
        """Maak preview sectie bovenin"""
        preview_frame = tk.Frame(self.main_frame, bg='#1a75ff')
        preview_frame.pack(fill='x', pady=(0, 20))

        # Preview canvassen
        self.preview_canvases = {}
        for i, cam_name in enumerate(['camera1', 'camera2', 'camera3']):
            # Container voor elke camera
            container = tk.Frame(preview_frame, bg='#1a75ff')
            container.pack(side='left', expand=True, padx=10)
            
            # Canvas met grijze achtergrond en witte rand
            canvas = tk.Canvas(
                container,
                width=350,
                height=250,
                bg='#cccccc',  # Grijze achtergrond
                highlightbackground='white',  # Witte rand
                highlightthickness=2
            )
            canvas.pack(pady=(0, 10))
            self.preview_canvases[cam_name] = canvas

    def setup_control_section(self):
        """Maak control sectie onder de previews"""
        control_frame = tk.Frame(self.main_frame, bg='#1a75ff')
        control_frame.pack(fill='x')

        # Camera controls
        self.camera_combos = {}
        for i, cam_name in enumerate(['camera1', 'camera2', 'camera3']):
            # Container voor elke camera control set
            container = tk.Frame(control_frame, bg='#1a75ff')
            container.pack(side='left', expand=True, padx=10)

            # Frame voor dropdown en rotatie knoppen
            control_row = tk.Frame(container, bg='#1a75ff')
            control_row.pack()

            # Dropdown
            combo = ttk.Combobox(
                control_row,
                values=self.get_available_cameras(),
                state='readonly',
                width=30
            )
            combo.pack(side='left', padx=2)
            combo.bind('<<ComboboxSelected>>', lambda e, name=cam_name: self.on_camera_selected(name))
            self.camera_combos[cam_name] = combo

            # Rotatie knoppen
            tk.Button(
                control_row,
                text="<",
                command=lambda c=cam_name: self.rotate_camera(c, -10),
                width=3,
                bg='white'
            ).pack(side='left', padx=2)
            
            tk.Button(
                control_row,
                text=">",
                command=lambda c=cam_name: self.rotate_camera(c, 10),
                width=3,
                bg='white'
            ).pack(side='left', padx=2)

    def setup_continue_button(self):
        """Maak continue knop rechtsonder"""
        continue_frame = tk.Frame(self.main_frame, bg='#1a75ff')
        continue_frame.pack(fill='x', side='bottom', pady=20)
        
        tk.Button(
            continue_frame,
            text="Continue",
            bg='#ffb3b3',  # Lichtroze achtergrond
            font=('Arial', 12),
            width=15,
            height=2,
            command=self.start_scoring
        ).pack(side='right')

    def get_available_cameras(self):
        """Detecteer beschikbare camera's"""
        available_cameras = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(str(i))
                cap.release()
        return available_cameras

    def rotate_camera(self, camera_name, angle):
        """Roteer camera beeld"""
        camera = self.cameras[camera_name]
        if camera['last_frame'] is not None:
            camera['rotation'] = (camera['rotation'] + angle) % 360
            self.display_frame(camera_name, camera['last_frame'])

    def rotate_image(self, image, angle):
        """Roteer een afbeelding met de gegeven hoek"""
        height, width = image.shape[:2]
        center = (width/2, height/2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_image = cv2.warpAffine(image, rotation_matrix, (width, height))
        return rotated_image

    def on_camera_selected(self, camera_name):
        """Handle camera selectie"""
        try:
            selected_id = int(self.camera_combos[camera_name].get())
            self.cameras[camera_name]['id'] = selected_id
            self.capture_frame(camera_name)
        except Exception as e:
            messagebox.showerror("Error", f"Error bij selecteren camera: {str(e)}")

    def capture_frame(self, camera_name):
        """Capture één frame van de geselecteerde camera"""
        try:
            camera_id = self.cameras[camera_name]['id']
            if camera_id is not None:
                cap = cv2.VideoCapture(camera_id)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        self.cameras[camera_name]['last_frame'] = frame
                        self.display_frame(camera_name, frame)
                    cap.release()
                else:
                    messagebox.showerror("Error", f"Kon camera {camera_id} niet openen")
        except Exception as e:
            messagebox.showerror("Error", f"Error bij camera capture: {str(e)}")

    def display_frame(self, camera_name, frame):
        """Toon frame in canvas met huidige rotatie"""
        if frame is not None:
            # Pas rotatie toe
            rotation = self.cameras[camera_name]['rotation']
            if rotation != 0:
                frame = self.rotate_image(frame, rotation)

            # Convert en resize naar canvas grootte
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (350, 250))
            
            photo = ImageTk.PhotoImage(image=Image.fromarray(frame_resized))
            
            canvas = self.preview_canvases[camera_name]
            canvas.delete("all")
            canvas.create_image(0, 0, image=photo, anchor=tk.NW)
            canvas.image = photo

    def start_scoring(self):
        """Start het scoring systeem"""
        active_cameras = sum(1 for cam in self.cameras.values() if cam['id'] is not None)
        if active_cameras < 3:
            messagebox.showwarning("Warning", "Configureer eerst alle camera's!")
            return
            
        # Start dartbord kalibratie
        from dartboard_calibration import start_dartboard_calibration
        start_dartboard_calibration(self.root, self.cameras)

def main():
    try:
        root = tk.Tk()
        app = DartScorerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Error bij starten applicatie: {str(e)}")
        
if __name__ == "__main__":
    main()