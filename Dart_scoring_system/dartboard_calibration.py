import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import math
import json
import logging

logger = logging.getLogger('dart_scorer.calibration')

class DartboardDetector:
    def __init__(self):
        # Dartbord segment waardes (van buitenaf met de klok mee)
        self.segments = [10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5, 20, 1, 18, 4, 13, 6]
        
        # Ring multiplicators
        self.DOUBLE_RING = 2
        self.TRIPLE_RING = 3
        self.OUTER_BULL = 25
        self.BULL = 50
        
        # Ring afstanden (als percentage van de radius)
        self.DOUBLE_RING_DIST = 0.95
        self.OUTER_DOUBLE_RING_DIST = 0.85
        self.TRIPLE_RING_DIST = 0.65
        self.INNER_TRIPLE_RING_DIST = 0.55
        self.OUTER_BULL_DIST = 0.16
        self.BULL_DIST = 0.08

    def detect_board(self, frame):
        """Detect dartboard in frame using Hough circles"""
        if frame is None:
            return None
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Verhoog het contrast voor betere detectie
        enhanced = cv2.convertScaleAbs(gray, alpha=1.5, beta=50)  # Verhoog het contrast
        
        blurred = cv2.GaussianBlur(enhanced, (9, 9), 2)
        
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,  # Verlaag deze waarde als je meer cirkels wil vinden
            minRadius=100,
            maxRadius=300
        )
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            logger.info(f"Dartbord gedetecteerd: {circles[0][0]}")
            return circles[0][0]  # Return first detected circle
        else:
            logger.error("Geen dartbord gedetecteerd!")
        return None

    def draw_overlay(self, frame, center, radius, rotation_offset=0):
        """Draw dartboard overlay on frame"""
        if center is None or radius is None:
            return frame
            
        overlay = frame.copy()
        
        # Draw rings
        cv2.circle(overlay, center, radius, (0, 255, 0), 2)  # Outer ring
        cv2.circle(overlay, center, int(radius * self.OUTER_DOUBLE_RING_DIST), (0, 255, 0), 1)
        cv2.circle(overlay, center, int(radius * self.TRIPLE_RING_DIST), (0, 255, 0), 1)
        cv2.circle(overlay, center, int(radius * self.INNER_TRIPLE_RING_DIST), (0, 255, 0), 1)
        cv2.circle(overlay, center, int(radius * self.OUTER_BULL_DIST), (0, 255, 0), 1)
        cv2.circle(overlay, center, int(radius * self.BULL_DIST), (0, 255, 0), 1)
        
        # Draw segment lines
        for i in range(20):
            angle = math.radians(i * 18 + rotation_offset)
            end_x = int(center[0] + radius * math.cos(angle))
            end_y = int(center[1] + radius * math.sin(angle))
            cv2.line(overlay, center, (end_x, end_y), (0, 255, 0), 1)
            
            # Add segment numbers
            text_x = int(center[0] + radius * 0.75 * math.cos(angle))
            text_y = int(center[1] + radius * 0.75 * math.sin(angle))
            cv2.putText(overlay, str(self.segments[i]), (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Blend overlay with original frame
        alpha = 0.7
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        
        return frame


class DartboardCalibrationScreen:
    def __init__(self, root, cameras):
        self.root = root
        self.cameras = cameras
        
        # Reset root window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        self.root.configure(bg='#1a75ff')
        
        # Setup variables
        self.current_camera_index = 0
        self.detector = DartboardDetector()
        self.preview_active = False
        self.rotation_offset = 0
        
        # Main frame
        self.main_frame = tk.Frame(self.root, bg='#1a75ff', padx=20, pady=20)
        self.main_frame.pack(expand=True, fill='both')
        
        # Setup GUI elements
        self.setup_instruction_label()
        self.setup_camera_view()
        self.setup_control_buttons()
        self.setup_rotation_control()
        
        # Start camera processing
        self.start_processing()
        
    def setup_instruction_label(self):
        """Setup instructie labels"""
        self.instruction_label = tk.Label(
            self.main_frame,
            text="Automatische dartbord detectie...",
            bg='#1a75ff',
            fg='white',
            font=('Arial', 12)
        )
        self.instruction_label.pack(pady=(0, 10))
        
        self.status_label = tk.Label(
            self.main_frame,
            text="",
            bg='#1a75ff',
            fg='yellow',
            font=('Arial', 14, 'bold')
        )
        self.status_label.pack(pady=(0, 10))
        
    def setup_camera_view(self):
        """Setup camera preview"""
        self.camera_frame = tk.Frame(self.main_frame, bg='#1a75ff')
        self.camera_frame.pack(expand=True, fill='both')
        
        # Links: origineel beeld
        self.original_canvas = tk.Canvas(
            self.camera_frame,
            width=640,
            height=360,
            bg='black',
            highlightbackground='white',
            highlightthickness=2
        )
        self.original_canvas.pack(side='left', padx=5)
        
        # Rechts: gedetecteerd beeld
        self.detection_canvas = tk.Canvas(
            self.camera_frame,
            width=640,
            height=360,
            bg='black',
            highlightbackground='white',
            highlightthickness=2
        )
        self.detection_canvas.pack(side='right', padx=5)

    def setup_rotation_control(self):
        """Setup rotatie controle"""
        rotation_frame = ttk.Frame(self.main_frame)
        rotation_frame.pack(fill='x', pady=10)
        
        ttk.Label(rotation_frame, text="Rotatie aanpassing:").pack(side='left', padx=5)
        
        ttk.Button(
            rotation_frame,
            text="-",
            command=lambda: self.adjust_rotation(-5)
        ).pack(side='left', padx=2)
        
        ttk.Button(
            rotation_frame,
            text="+",
            command=lambda: self.adjust_rotation(5)
        ).pack(side='left', padx=2)

    def setup_control_buttons(self):
        """Setup control buttons"""
        button_frame = tk.Frame(self.main_frame, bg='#1a75ff')
        button_frame.pack(fill='x', pady=20)
        
        # Save knop
        self.save_button = tk.Button(
            button_frame,
            text="Save Calibration",
            command=self.save_calibration,
            bg='white',
            width=15,
            height=2,
            state='disabled'
        )
        self.save_button.pack(side='left', padx=5)
        
        # Next Camera knop
        self.next_button = tk.Button(
            button_frame,
            text="Next Camera" if self.current_camera_index < 2 else "Complete",
            command=self.next_camera,
            bg='#ffb3b3',
            width=15,
            height=2,
            state='disabled'
        )
        self.next_button.pack(side='right', padx=5)

    def start_processing(self):
        """Start camera verwerking"""
        self.preview_active = True
        self.process_frame()
        
    def process_frame(self):
        """Verwerk en toon camera frame"""
        if not self.preview_active:
            return
            
        # Haal frame op van huidige camera
        current_camera = list(self.cameras.values())[self.current_camera_index]
        if current_camera['last_frame'] is not None:
            frame = current_camera['last_frame'].copy()
            
            # Bewaar de originele resolutie voor later gebruik
            original_height, original_width = frame.shape[:2]
            
            # Resize voor display (dit is de weergave-resolutie)
            display_frame = cv2.resize(frame, (640, 360))
            
            # Detecteer dartbord
            circle = self.detector.detect_board(display_frame)
            
            if circle is not None:
                x, y, r = circle
                
                # Schaal de coördinaten terug naar de originele resolutie
                x = int(x * (original_width / 640))  # Schaal de x-coördinaat
                y = int(y * (original_height / 360))  # Schaal de y-coördinaat
                r = int(r * (original_width / 640))  # Schaal de straal op basis van breedte
                
                # Update status
                self.status_label.config(
                    text="Dartbord gedetecteerd!",
                    fg='lime'
                )
                self.save_button.config(state='normal')
                self.next_button.config(state='normal')
                
                # Maak visualisatie (gebruik de originele resolutie voor overlay)
                detected_frame = self.detector.draw_overlay(
                    display_frame.copy(),
                    (x, y),
                    r,
                    self.rotation_offset
                )
                
                # Toon beelden
                self.show_image(display_frame, self.original_canvas)
                self.show_image(detected_frame, self.detection_canvas)
            else:
                # Update status
                self.status_label.config(
                    text="Geen dartbord gedetecteerd",
                    fg='red'
                )
                self.save_button.config(state='disabled')
                self.next_button.config(state='disabled')
                
                # Toon alleen origineel beeld
                self.show_image(display_frame, self.original_canvas)
                self.detection_canvas.delete("all")
                
        # Schedule volgende frame
        if self.preview_active:
            self.root.after(30, self.process_frame)


    def adjust_rotation(self, delta):
        """Pas rotatie aan met gegeven delta"""
        self.rotation_offset = (self.rotation_offset + delta) % 360

    def show_image(self, frame, canvas):
        """Toon een frame op een canvas"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        photo = ImageTk.PhotoImage(image=img)
        
        canvas.delete("all")
        canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        canvas.image = photo

    def save_calibration(self):
        """Sla kalibratie op voor huidige camera"""
        try:
            current_camera = list(self.cameras.values())[self.current_camera_index]
            frame = current_camera['last_frame']
            if frame is not None:
                circle = self.detector.detect_board(cv2.resize(frame, (640, 360)))
                if circle is not None:
                    x, y, r = circle
                    current_camera['calibration'] = {
                        'center': (x, y),
                        'radius': r,
                        'rotation_offset': self.rotation_offset
                    }
                    messagebox.showinfo("Success", "Kalibratie opgeslagen voor huidige camera")
                    return
                    
            messagebox.showerror("Error", "Kon geen dartbord detecteren voor kalibratie")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error bij opslaan kalibratie: {str(e)}")

    def next_camera(self):
        """Ga naar volgende camera of rond kalibratie af"""
        if self.current_camera_index < 2:
            # Ga naar volgende camera
            self.current_camera_index += 1
            self.rotation_offset = 0
            
            # Update button text
            self.next_button.config(
                text="Next Camera" if self.current_camera_index < 2 else "Complete",
                state='disabled'
            )
            self.save_button.config(state='disabled')
            
            # Update status
            self.status_label.config(text="")
            self.instruction_label.config(text=f"Camera {self.current_camera_index + 1} kalibratie...")
            
        else:
            # Kalibratie compleet
            self.complete_calibration()

    def complete_calibration(self):
        """Rond kalibratie af"""
        try:
            # Sla configuratie op
            config = {
                'cameras': {
                    f'camera{i+1}': {
                        'calibration': cam.get('calibration', {})
                    }
                    for i, cam in enumerate(self.cameras.values())
                }
            }
            
            with open('config/board_config.json', 'w') as f:
                json.dump(config, f, indent=4)
                
            messagebox.showinfo("Success", "Kalibratie succesvol afgerond!")
            
            # Stop camera processing
            self.preview_active = False
            
            # Sluit kalibratie scherm
            self.root.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error bij opslaan kalibratie: {str(e)}")

def start_dartboard_calibration(root, cameras):
    """Start het dartbord kalibratie scherm"""
    return DartboardCalibrationScreen(root, cameras)