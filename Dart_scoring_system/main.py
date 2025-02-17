import os
os.environ['TK_SILENCE_DEPRECATION'] = "1"

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import json
import logging
from PIL import Image, ImageTk
from src.detector import DartboardDetector
from src.scorer import ScoreCalculator
from src.gui.scoring import ScoringGUI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dart_scorer.main')

class DartScorerApp:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        
        # Initialiseer componenten
        self.detector = DartboardDetector()
        self.scorer = ScoreCalculator()
        
        # Camera management
        self.cameras = {
            'camera1': {'id': None, 'cap': None, 'last_frame': None},
            'camera2': {'id': None, 'cap': None, 'last_frame': None},
            'camera3': {'id': None, 'cap': None, 'last_frame': None}
        }
        
        # GUI elementen
        self.preview_canvases = {}
        self.camera_combos = {}
        
        self.setup_gui()
        
    def setup_window(self):
        """Configureer het hoofdvenster"""
        self.root.title("Genius Dart Software - 0.01")
        self.root.geometry("1400x800")
        self.root.configure(bg='#1a75ff')
        
        # Maak het venster responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Hoofdframe
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
    def setup_gui(self):
        """Setup alle GUI elementen"""
        # Preview sectie
        self.setup_preview_section()
        
        # Camera configuratie sectie
        self.setup_camera_section()
        
        # Knoppen sectie
        self.setup_button_section()
        
    def setup_preview_section(self):
        """Maak camera preview sectie"""
        preview_frame = ttk.LabelFrame(self.main_frame, text="Camera Previews", padding="10")
        preview_frame.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        
        # Preview canvassen voor elke camera
        for i, cam_name in enumerate(['camera1', 'camera2', 'camera3']):
            # Frame voor elke camera
            camera_frame = ttk.Frame(preview_frame)
            camera_frame.grid(row=0, column=i, padx=10, pady=5)
            
            # Label
            ttk.Label(
                camera_frame,
                text=f"{cam_name.capitalize()} Preview"
            ).pack(pady=(0, 5))
            
            # Canvas met grijze achtergrond
            canvas = tk.Canvas(
                camera_frame,
                width=400,
                height=300,
                bg='#cccccc',
                highlightthickness=2,
                highlightbackground='white'
            )
            canvas.pack()
            self.preview_canvases[cam_name] = canvas
            
    def setup_camera_section(self):
        """Maak camera configuratie sectie"""
        camera_frame = ttk.LabelFrame(self.main_frame, text="Camera Configuration", padding="10")
        camera_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        
        for i, cam_name in enumerate(['camera1', 'camera2', 'camera3']):
            # Container voor elke camera
            container = ttk.Frame(camera_frame)
            container.grid(row=0, column=i, padx=10, pady=5)
            
            # Label
            ttk.Label(
                container,
                text=f"{cam_name.capitalize()}"
            ).grid(row=0, column=0, columnspan=2)
            
            # Dropdown voor camera selectie
            combo = ttk.Combobox(
                container,
                values=self.get_available_cameras(),
                state='readonly',
                width=30
            )
            combo.grid(row=1, column=0, columnspan=2, pady=5)
            combo.bind('<<ComboboxSelected>>', 
                      lambda e, name=cam_name: self.on_camera_selected(name))
            self.camera_combos[cam_name] = combo
            
            # Test knop
            ttk.Button(
                container,
                text="Test Camera",
                command=lambda c=cam_name: self.test_camera(c)
            ).grid(row=2, column=0, columnspan=2, pady=5)
            
    def setup_button_section(self):
        """Maak knoppen sectie"""
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="e", padx=5, pady=20)
        
        # Start knop
        self.start_button = ttk.Button(
            button_frame,
            text="Start Calibration",
            command=self.start_calibration,
            state='disabled'
        )
        self.start_button.pack(side='right', padx=5)
        
    def get_available_cameras(self) -> list:
        """Detecteer beschikbare camera's"""
        available_cameras = []
        for i in range(10):  # Check eerste 10 indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(str(i))
                cap.release()
        return available_cameras
        
    def on_camera_selected(self, camera_name: str):
        """Handle camera selectie"""
        try:
            selected_id = int(self.camera_combos[camera_name].get())
            self.cameras[camera_name]['id'] = selected_id
            
            # Update start knop status
            self.update_start_button()
            
            # Neem één frame op om te tonen
            self.capture_single_frame(camera_name)
            
        except Exception as e:
            logger.error(f"Error bij camera selectie: {str(e)}")
            messagebox.showerror("Error", f"Kon camera {selected_id} niet selecteren")
            
    def update_start_button(self):
        """Update status van start knop"""
        # Enable als alle camera's geselecteerd zijn
        all_selected = all(cam['id'] is not None for cam in self.cameras.values())
        self.start_button['state'] = 'normal' if all_selected else 'disabled'
        
    def test_camera(self, camera_name: str):
        """Test een specifieke camera"""
        camera = self.cameras[camera_name]
        if camera['id'] is None:
            messagebox.showwarning("Warning", "Selecteer eerst een camera")
            return
            
        try:
            cap = cv2.VideoCapture(camera['id'])
            if not cap.isOpened():
                raise Exception("Kon camera niet openen")
                
            ret, frame = cap.read()
            if not ret:
                raise Exception("Kon geen frame lezen")
                
            # Toon test frame
            cv2.imshow(f"{camera_name} Test", frame)
            cv2.waitKey(1000)
            cv2.destroyWindow(f"{camera_name} Test")
            
            cap.release()
            messagebox.showinfo("Success", f"Camera {camera_name} werkt correct!")
            
        except Exception as e:
            logger.error(f"Error bij camera test: {str(e)}")
            messagebox.showerror("Error", f"Camera test gefaald: {str(e)}")
            
    def capture_single_frame(self, camera_name: str):
        """Neem één enkel frame op van de camera"""
        camera = self.cameras[camera_name]
        if camera['id'] is None:
            return

        try:
            # Open camera, neem frame op, en sluit direct weer
            cap = cv2.VideoCapture(camera['id'])
            if not cap.isOpened():
                raise Exception("Kon camera niet openen")
                
            ret, frame = cap.read()
            cap.release()  # Sluit camera direct
            
            if ret:
                # Bewaar frame voor detector
                camera['last_frame'] = frame
                
                # Resize en toon preview
                frame = cv2.resize(frame, (400, 300))
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(image=img)
                
                canvas = self.preview_canvases[camera_name]
                canvas.delete("all")  # Clear vorige frame
                canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                canvas.image = photo  # Voorkom garbage collection
                
        except Exception as e:
            logger.error(f"Error bij frame capture: {str(e)}")
            messagebox.showerror("Error", f"Kon geen frame opnemen van camera {camera_name}")
            
    def start_camera_preview(self, camera_name: str):
        """Toon één enkel frame van de camera"""
        self.capture_single_frame(camera_name)
            
    def update_preview(self, camera_name: str):
        """Update functie is niet meer nodig want we gebruiken enkele frames"""
        pass
            
    def start_calibration(self):
        """Start het kalibratieproces"""
        # Stop alle previews
        for camera in self.cameras.values():
            if camera['cap'] is not None:
                camera['cap'].release()
                
        # Start kalibratie met detector
        self.detector.start_calibration(self.root, self.cameras)
        
    def stop_all_cameras(self):
        """Stop alle camera's"""
        for camera in self.cameras.values():
            if camera['cap'] is not None:
                camera['cap'].release()
                
    def on_closing(self):
        """Handle programma afsluiting"""
        self.stop_all_cameras()
        self.root.destroy()

def main():
    try:
        root = tk.Tk()
        app = DartScorerApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        logger.error(f"Error bij starten applicatie: {str(e)}")
        messagebox.showerror("Fatal Error", f"Applicatie error: {str(e)}")

if __name__ == "__main__":
    main()