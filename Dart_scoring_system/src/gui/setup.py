import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import json
import logging
from typing import Dict, Callable
import os
from PIL import Image, ImageTk

logger = logging.getLogger('dart_scorer.gui.setup')

class CameraSetupGUI:
    def __init__(self, root: tk.Tk, camera_manager, on_setup_complete: Callable = None):
        self.root = root
        self.camera_manager = camera_manager
        self.on_setup_complete = on_setup_complete
        
        # Venster instellingen
        self.root.title("Dart Scorer - Camera Setup")
        self.root.geometry("1200x800")
        
        # Camera variabelen
        self.camera_vars = {
            'camera1': {'id': tk.StringVar(), 'active': False, 'preview': None},
            'camera2': {'id': tk.StringVar(), 'active': False, 'preview': None},
            'camera3': {'id': tk.StringVar(), 'active': False, 'preview': None}
        }
        
        self.preview_active = False
        self.setup_gui()
        
    def setup_gui(self):
        """Initialiseer de GUI elementen"""
        # Hoofdframe
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Camera selectie sectie
        self.setup_camera_selection()
        
        # Preview sectie
        self.setup_preview_section()
        
        # Knoppen sectie
        self.setup_button_section()
        
        # Grid configuratie
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
    def setup_camera_selection(self):
        """Maak camera selectie sectie"""
        select_frame = ttk.LabelFrame(self.main_frame, text="Camera Selectie", padding="10")
        select_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Krijg beschikbare camera's
        available_cameras = self.get_available_cameras()
        
        # Maak selectie voor elke camera
        for i, (cam_name, cam_data) in enumerate(self.camera_vars.items()):
            # Label
            ttk.Label(select_frame, text=f"{cam_name}:").grid(
                row=i, column=0, padx=5, pady=5, sticky="w"
            )
            
            # Dropdown
            combo = ttk.Combobox(
                select_frame, 
                textvariable=cam_data['id'],
                values=available_cameras,
                state='readonly',
                width=30
            )
            combo.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            
            # Test knop
            ttk.Button(
                select_frame,
                text="Test",
                command=lambda c=cam_name: self.test_camera(c)
            ).grid(row=i, column=2, padx=5, pady=5)
            
            # Status label
            status_label = ttk.Label(select_frame, text="Niet actief")
            status_label.grid(row=i, column=3, padx=5, pady=5)
            self.camera_vars[cam_name]['status_label'] = status_label
            
    def setup_preview_section(self):
        """Maak preview sectie"""
        preview_frame = ttk.LabelFrame(self.main_frame, text="Camera Previews", padding="10")
        preview_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Preview canvassen voor elke camera
        for i, (cam_name, cam_data) in enumerate(self.camera_vars.items()):
            frame = ttk.Frame(preview_frame)
            frame.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
            
            # Label
            ttk.Label(frame, text=f"{cam_name} Preview").pack(pady=2)
            
            # Canvas voor video preview
            canvas = tk.Canvas(frame, width=400, height=300, bg='black')
            canvas.pack(padx=5, pady=5)
            self.camera_vars[cam_name]['canvas'] = canvas
            
    def setup_button_section(self):
        """Maak knoppen sectie"""
        button_frame = ttk.Frame(self.main_frame, padding="10")
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Start Preview knop
        self.preview_button = ttk.Button(
            button_frame,
            text="Start Previews",
            command=self.toggle_previews
        )
        self.preview_button.pack(side=tk.LEFT, padx=5)
        
        # Save Configuration knop
        ttk.Button(
            button_frame,
            text="Save Configuration",
            command=self.save_configuration
        ).pack(side=tk.LEFT, padx=5)
        
        # Complete Setup knop
        ttk.Button(
            button_frame,
            text="Complete Setup",
            command=self.complete_setup
        ).pack(side=tk.LEFT, padx=5)
        
    def get_available_cameras(self) -> list:
        """Detecteer beschikbare camera's"""
        available_cameras = []
        for i in range(10):  # Check eerste 10 indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(str(i))
                cap.release()
        return available_cameras
        
    def test_camera(self, camera_name: str):
        """Test een specifieke camera"""
        camera_id = self.camera_vars[camera_name]['id'].get()
        if not camera_id:
            messagebox.showwarning("Warning", f"Selecteer eerst een camera voor {camera_name}")
            return
            
        try:
            cap = cv2.VideoCapture(int(camera_id))
            if not cap.isOpened():
                raise Exception("Kon camera niet openen")
                
            ret, frame = cap.read()
            if not ret:
                raise Exception("Kon geen frame lezen")
                
            # Toon test frame
            cv2.imshow(f"{camera_name} Test", frame)
            cv2.waitKey(1000)
            cv2.destroyWindow(f"{camera_name} Test")
            
            # Update status
            self.camera_vars[camera_name]['status_label'].config(
                text="Actief", foreground="green"
            )
            self.camera_vars[camera_name]['active'] = True
            
            cap.release()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error bij testen {camera_name}: {str(e)}")
            self.camera_vars[camera_name]['status_label'].config(
                text="Error", foreground="red"
            )
            self.camera_vars[camera_name]['active'] = False
            
    def toggle_previews(self):
        """Toggle camera previews aan/uit"""
        if not self.preview_active:
            self.start_previews()
        else:
            self.stop_previews()
            
    def start_previews(self):
        """Start camera previews"""
        self.preview_active = True
        self.preview_button.config(text="Stop Previews")
        
        for cam_name, cam_data in self.camera_vars.items():
            if cam_data['active']:
                self.update_preview(cam_name)
                
    def stop_previews(self):
        """Stop camera previews"""
        self.preview_active = False
        self.preview_button.config(text="Start Previews")
        
        # Reset preview canvassen
        for cam_data in self.camera_vars.values():
            if 'canvas' in cam_data:
                cam_data['canvas'].delete("all")
                
    def update_preview(self, camera_name: str):
        """Update preview voor een specifieke camera"""
        if not self.preview_active:
            return
            
        camera_id = self.camera_vars[camera_name]['id'].get()
        try:
            cap = cv2.VideoCapture(int(camera_id))
            ret, frame = cap.read()
            
            if ret:
                # Convert frame naar PIL Image
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (400, 300))
                img = Image.fromarray(frame)
                img_tk = ImageTk.PhotoImage(image=img)
                
                # Update canvas
                canvas = self.camera_vars[camera_name]['canvas']
                canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                canvas.image = img_tk  # Bewaar referentie
                
            cap.release()
            
            # Schedule volgende update
            if self.preview_active:
                self.root.after(30, lambda: self.update_preview(camera_name))
                
        except Exception as e:
            logger.error(f"Error bij updaten preview voor {camera_name}: {str(e)}")
            
    def save_configuration(self):
        """Sla camera configuratie op"""
        config = {}
        for cam_name, cam_data in self.camera_vars.items():
            if cam_data['active']:
                config[cam_name] = cam_data['id'].get()
                
        try:
            with open('config/camera_config.json', 'w') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Success", "Camera configuratie opgeslagen")
        except Exception as e:
            messagebox.showerror("Error", f"Error bij opslaan configuratie: {str(e)}")
            
    def complete_setup(self):
        """Voltooi camera setup"""
        # Stop previews
        self.stop_previews()
        
        # Valideer configuratie
        active_cameras = sum(1 for cam in self.camera_vars.values() if cam['active'])
        if active_cameras < 3:
            messagebox.showwarning(
                "Warning", 
                "Niet alle camera's zijn getest en actief"
            )
            return
            
        # Sla configuratie op
        self.save_configuration()
        
        # Roep callback aan indien aanwezig
        if self.on_setup_complete:
            self.on_setup_complete()
            
        # Sluit setup window
        self.root.destroy()