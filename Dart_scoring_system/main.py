import os
os.environ['TK_SILENCE_DEPRECATION'] = "1"

import tkinter as tk
from tkinter import ttk
import cv2
import json

class DartScorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dart Scorer")
        self.root.geometry("1200x800")
        self.root.configure(bg='white')  # Witte achtergrond

        # Hoofdframe met duidelijke styling
        self.main_frame = tk.Frame(self.root, bg='lightgray', padx=20, pady=20)
        self.main_frame.pack(expand=True, fill='both', padx=20, pady=20)

        # Camera selectie sectie
        self.setup_camera_section()

        # Preview sectie
        self.setup_preview_section()

        # Knoppen sectie
        self.setup_button_section()

        # Camera variabelen
        self.cameras = {
            'camera1': None,
            'camera2': None,
            'camera3': None
        }

    def setup_camera_section(self):
        """Maak camera setup sectie"""
        camera_frame = tk.LabelFrame(
            self.main_frame,
            text="Camera Setup",
            bg='lightgray',
            font=('Arial', 12),
            padx=10,
            pady=10
        )
        camera_frame.pack(fill='x', padx=10, pady=10)

        # Beschikbare camera's ophalen
        available_cameras = self.get_available_cameras()

        # Camera dropdowns
        for i, cam_name in enumerate(['Camera 1', 'Camera 2', 'Camera 3']):
            # Frame voor elke camera rij
            cam_row = tk.Frame(camera_frame, bg='lightgray')
            cam_row.pack(fill='x', pady=5)

            # Label
            tk.Label(
                cam_row,
                text=f"{cam_name}:",
                bg='lightgray',
                font=('Arial', 12)
            ).pack(side='left', padx=5)

            # Dropdown
            combo = ttk.Combobox(
                cam_row,
                values=available_cameras,
                state='readonly',
                width=30
            )
            combo.pack(side='left', padx=5)

            # Test knop
            tk.Button(
                cam_row,
                text="Test Camera",
                bg='lightblue',
                font=('Arial', 10),
                command=lambda c=cam_name: self.test_camera(c)
            ).pack(side='left', padx=5)

    def setup_preview_section(self):
        """Maak preview sectie"""
        preview_frame = tk.LabelFrame(
            self.main_frame,
            text="Camera Previews",
            bg='lightgray',
            font=('Arial', 12),
            padx=10,
            pady=10
        )
        preview_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Preview canvassen
        for i in range(3):
            canvas = tk.Canvas(
                preview_frame,
                width=300,
                height=225,
                bg='black'
            )
            canvas.grid(row=0, column=i, padx=5, pady=5)

    def setup_button_section(self):
        """Maak knoppen sectie"""
        button_frame = tk.Frame(self.main_frame, bg='lightgray')
        button_frame.pack(fill='x', padx=10, pady=10)

        # Start knop
        tk.Button(
            button_frame,
            text="Start Scoring",
            bg='lightgreen',
            font=('Arial', 12),
            padx=20,
            pady=10,
            command=self.start_scoring
        ).pack(side='left', padx=5)

        # Test knop
        tk.Button(
            button_frame,
            text="Test All Cameras",
            bg='lightblue',
            font=('Arial', 12),
            padx=20,
            pady=10,
            command=self.test_cameras
        ).pack(side='left', padx=5)

    def get_available_cameras(self):
        """Detecteer beschikbare camera's"""
        available_cameras = []
        for i in range(10):  # Check eerste 10 indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(str(i))
                cap.release()
        return available_cameras

    def test_camera(self, camera_name):
        """Test een specifieke camera"""
        print(f"Testing camera: {camera_name}")  # Debug print

    def test_cameras(self):
        """Test alle geselecteerde camera's"""
        print("Testing all cameras")  # Debug print

    def start_scoring(self):
        """Start het scoring systeem"""
        print("Starting scoring system")  # Debug print

def main():
    root = tk.Tk()
    app = DartScorerApp(root)
    print("App started!")  # Debug print
    root.mainloop()

if __name__ == "__main__":
    main()