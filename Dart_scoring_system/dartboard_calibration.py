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
        self.segments = [6, 13, 4, 18, 1, 20, 5, 12, 9, 14, 11, 8, 16, 7, 19, 3, 17, 2, 15, 10]
        
        # Ring multiplicators en afstanden
        self.DOUBLE_RING_DIST = 0.95
        self.TRIPLE_RING_DIST = 0.65
        self.OUTER_BULL_DIST = 0.16
        self.BULL_DIST = 0.08
        
        # Laad template afbeelding
        template_path = 'resources/dartboard_template.jpg'
        self.template = cv2.imread(template_path)
        if self.template is not None:
            # Converteer template naar optimale formaat voor matching
            self.template = cv2.resize(self.template, (400, 400))
            self.template_gray = cv2.cvtColor(self.template, cv2.COLOR_BGR2GRAY)
            # Maak edge template voor robuustere matching
            self.template_edges = cv2.Canny(self.template_gray, 50, 150)
        else:
            raise Exception(f"Kon template afbeelding niet laden: {template_path}")

    def detect_board(self, frame):
        """Detect dartboard using template matching and edge detection"""
        if frame is None:
            return None

        # Convert frame naar grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detecteer edges in frame
        edges = cv2.Canny(gray, 50, 150)
        
        best_match = None
        best_scale = 1.0
        best_score = -1
        
        # Test verschillende schalen
        for scale in np.linspace(0.5, 1.5, 20):
            width = int(self.template.shape[1] * scale)
            height = int(self.template.shape[0] * scale)
            
            # Resize frame edges voor matching
            resized_edges = cv2.resize(edges, (width, height))
            
            # Template matching met edges
            result = cv2.matchTemplate(resized_edges, self.template_edges, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_score:
                best_score = max_val
                best_scale = scale
                best_match = (max_loc, (width, height))
        
        if best_score > 0.3:  # Threshold voor goede match
            loc, (w, h) = best_match
            center_x = int(loc[0] + w/2)
            center_y = int(loc[1] + h/2)
            radius = int(min(w, h)/2)
            
            # Valideer met circle detection
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=radius,
                param1=50,
                param2=30,
                minRadius=int(radius*0.8),
                maxRadius=int(radius*1.2)
            )
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                x, y, r = circles[0][0]
                # Gebruik gemiddelde van template en circle detection
                final_x = int((center_x + x)/2)
                final_y = int((center_y + y)/2)
                final_r = int((radius + r)/2)
                return np.array([final_x, final_y, final_r])
            
            return np.array([center_x, center_y, radius])
            
        return None

    def draw_overlay(self, frame, center, radius, rotation_offset=0):
        """Draw dartboard overlay on frame"""
        if center is None or radius is None:
            return frame
            
        overlay = frame.copy()
        
        # Draw rings met specifieke kleuren voor Winmau bord
        cv2.circle(overlay, center, radius, (255, 255, 255), 2)  # Outer ring (wit)
        cv2.circle(overlay, center, int(radius * self.DOUBLE_RING_DIST), (0, 255, 0), 2)  # Double ring (groen)
        cv2.circle(overlay, center, int(radius * self.TRIPLE_RING_DIST), (0, 0, 255), 2)  # Triple ring (rood)
        cv2.circle(overlay, center, int(radius * self.OUTER_BULL_DIST), (0, 255, 0), 2)  # Outer bull (groen)
        cv2.circle(overlay, center, int(radius * self.BULL_DIST), (0, 0, 255), 2)  # Bull (rood)
        
        # Draw segment lijnen
        for i in range(20):
            angle = math.radians(i * 18 + rotation_offset)
            end_x = int(center[0] + radius * math.cos(angle))
            end_y = int(center[1] + radius * math.sin(angle))
            cv2.line(overlay, center, (end_x, end_y), (255, 255, 255), 1)
            
            # Voeg segment nummers toe
            text_x = int(center[0] + radius * 0.85 * math.cos(angle))
            text_y = int(center[1] + radius * 0.85 * math.sin(angle))
            cv2.putText(overlay, str(self.segments[i]), (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Blend overlay met origineel frame
        alpha = 0.6
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
            width=600,
            height=450,
            bg='black',
            highlightbackground='white',
            highlightthickness=2
        )
        self.original_canvas.pack(side='left', padx=5)
        
        # Rechts: gedetecteerd beeld
        self.detection_canvas = tk.Canvas(
            self.camera_frame,
            width=600,
            height=450,
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
        """Verwerk en toon camera frame met debug logging"""
        if not self.preview_active:
            return
            
        try:
            # Debug print voor camera status
            print("Actieve camera's:", self.cameras)
            
            # Haal frame op van huidige camera
            current_camera = list(self.cameras.values())[self.current_camera_index]
            print(f"Huidige camera index: {self.current_camera_index}")
            print(f"Camera data: {current_camera}")
            
            if current_camera['last_frame'] is not None:
                print("Frame gevonden, afmetingen:", current_camera['last_frame'].shape)
                frame = current_camera['last_frame'].copy()
                
                # Controleer frame
                if frame is None:
                    print("Frame is None!")
                    return
                    
                if frame.size == 0:
                    print("Frame is leeg!")
                    return
                    
                # Resize voor display
                display_frame = cv2.resize(frame, (600, 450))
                print("Frame geresized naar:", display_frame.shape)
                
                # Toon origineel frame eerst
                self.show_image(display_frame, self.original_canvas)
                print("Origineel frame getoond")
                
                # Detecteer dartbord
                circle = self.detector.detect_board(display_frame)
                
                if circle is not None:
                    x, y, r = circle
                    print(f"Dartbord gedetecteerd: center=({x},{y}), radius={r}")
                    
                    # Update status
                    self.status_label.config(
                        text="Dartbord gedetecteerd!",
                        fg='lime'
                    )
                    self.save_button.config(state='normal')
                    self.next_button.config(state='normal')
                    
                    # Maak visualisatie
                    detected_frame = self.detector.draw_overlay(
                        display_frame.copy(),
                        (x, y),
                        r,
                        self.rotation_offset
                    )
                    
                    # Toon gedetecteerd frame
                    self.show_image(detected_frame, self.detection_canvas)
                    print("Gedetecteerd frame getoond")
                else:
                    print("Geen dartbord gedetecteerd")
                    # Update status
                    self.status_label.config(
                        text="Geen dartbord gedetecteerd",
                        fg='red'
                    )
                    self.save_button.config(state='disabled')
                    self.next_button.config(state='disabled')
                    
                    # Toon alleen origineel
                    self.detection_canvas.delete("all")
            else:
                print("Geen frame beschikbaar van camera")
                
        except Exception as e:
            print(f"Error in process_frame: {str(e)}")
            import traceback
            traceback.print_exc()
                
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
                circle = self.detector.detect_board(cv2.resize(frame, (600, 450)))
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