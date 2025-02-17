import cv2
import numpy as np
import json
import logging
from typing import Tuple, Optional, Dict, TypedDict, List
import math
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import ttk, messagebox

logger = logging.getLogger('dart_scorer.detector')

class CircleDetectionConfig(TypedDict):
    min_distance: int
    param1: int
    param2: int
    min_radius: int
    max_radius: int

class PreprocessingConfig(TypedDict):
    clahe_clip_limit: float
    clahe_grid_size: int
    canny_low: int
    canny_high: int
    morph_kernel_size: int

class RegionConfig(TypedDict):
    outer_radius_factor: float
    inner_radius_factor: float

class BoardConfig(TypedDict):
    board_detection: Dict[str, PreprocessingConfig | CircleDetectionConfig]
    scoring_regions: Dict[str, RegionConfig]
    cameras: Dict[str, Dict]

class DartboardDetector:
    def __init__(self, config_path: str = 'config/board_config.json'):
        self.config_path = config_path
        self.load_config()
        self.board_center: Optional[Tuple[int, int]] = None
        self.board_radius: Optional[int] = None
        self.perspective_matrix: Optional[np.ndarray] = None
        self.calibration_ui = None
        self.preview_active = False

    def load_config(self) -> None:
        """Laad detectie configuratie uit JSON bestand"""
        try:
            with open(self.config_path, 'r') as f:
                self.config: BoardConfig = json.load(f)
            logger.info("Board configuratie succesvol geladen")
        except Exception as e:
            logger.error(f"Error bij laden board config: {str(e)}")
            # Maak default config als het bestand niet bestaat
            self.config = {
                'board_detection': {
                    'preprocessing': {
                        'clahe_clip_limit': 2.0,
                        'clahe_grid_size': 8,
                        'canny_low': 50,
                        'canny_high': 150,
                        'morph_kernel_size': 5
                    },
                    'circle_detection': {
                        'min_distance': 100,
                        'param1': 50,
                        'param2': 25,
                        'min_radius': 50,
                        'max_radius': 300
                    }
                },
                'scoring_regions': {
                    'doubles': {
                        'outer_radius_factor': 0.95,
                        'inner_radius_factor': 0.85
                    },
                    'triples': {
                        'outer_radius_factor': 0.65,
                        'inner_radius_factor': 0.55
                    },
                    'bullseye': {
                        'outer_radius_factor': 0.16,
                        'inner_radius_factor': 0.08
                    }
                },
                'cameras': {}
            }

    def detect_board(self, frame: np.ndarray) -> Tuple[bool, Optional[Dict]]:
        """Detecteer het dartbord met focus op de dubbele ring als buitenste referentie"""
        try:
            if frame is None:
                return False, None
                
            # Converteer naar grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Verbeter contrast
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Gaussian blur voor ruisreductie
            blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
            
            # Pas thresholding toe om zwarte ring te isoleren
            _, thresh = cv2.threshold(blurred, 70, 255, cv2.THRESH_BINARY_INV)
            
            # Edge detection
            edges = cv2.Canny(thresh, 30, 150)
            
            # Morphologische operaties om de dubbele ring te benadrukken
            kernel = np.ones((3,3), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=1)
            
            # Cirkeldetectie met parameters afgestemd op de dubbele ring
            circles = cv2.HoughCircles(
                dilated,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=frame.shape[0] // 2,
                param1=50,
                param2=30,
                minRadius=int(frame.shape[0] * 0.25),  # Verkleind voor dubbele ring
                maxRadius=int(frame.shape[0] * 0.45)   # Verkleind voor dubbele ring
            )
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                
                # Filter cirkels op basis van intensiteit rond de rand
                valid_circles = []
                for circle in circles[0]:
                    x, y, r = circle
                    
                    # Check of het punt binnen het frame ligt
                    if (x > r and x < frame.shape[1] - r and 
                        y > r and y < frame.shape[0] - r):
                        
                        # Maak een masker voor de ring
                        mask = np.zeros_like(gray)
                        cv2.circle(mask, (x, y), r, 255, 3)
                        
                        # Check gemiddelde intensiteit op de ring
                        ring_mean = cv2.mean(gray, mask=mask)[0]
                        
                        # Voeg cirkel toe als de ring donker genoeg is (dubbele ring is zwart)
                        if ring_mean < 100:  # Threshold voor donkere ring
                            valid_circles.append(circle)
                
                if valid_circles:
                    # Neem de meest geschikte cirkel
                    best_circle = sorted(valid_circles, key=lambda c: c[2])[0]
                    
                    # De gevonden cirkel is de dubbele ring
                    x, y, r = best_circle
                    self.board_center = (x, y)
                    self.board_radius = r
                    
                    logger.info(f"Dubbele ring gedetecteerd: center=({x}, {y}), radius={r}")
                    
                    return True, {
                        'center': self.board_center,
                        'radius': self.board_radius
                    }
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error in board detection: {str(e)}")
            return False, None

    def detect_segment(self, point: Tuple[int, int]) -> Dict:
        """
        Detecteer in welk segment en ring een punt ligt
        """
        try:
            if self.board_center is None or self.board_radius is None:
                return {'success': False, 'error': 'Bord niet gedetecteerd'}

            # Bereken afstand van punt tot centrum
            dx = point[0] - self.board_center[0]
            dy = point[1] - self.board_center[1]
            distance = math.sqrt(dx*dx + dy*dy)
            distance_factor = distance / self.board_radius
            
            # Bereken hoek (0-360 graden)
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0:
                angle += 360
                
            # Segment waarden in volgorde (tegen de klok in, startend bij 20)
            segment_values = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]
            
            # Bepaal segment nummer (0-19)
            # We draaien 9 graden (halve segment) voor correcte uitlijning
            segment_index = int(((angle + 9) % 360) / 18)
            segment_value = segment_values[segment_index]
            
            # Bepaal ring (double, triple, single of bull)
            ring_value = 1  # default single
            regions = self.config['scoring_regions']
            
            if distance_factor <= regions['bullseye']['outer_radius_factor']:
                # Bullseye gebied
                if distance_factor <= regions['bullseye']['inner_radius_factor']:
                    segment_value = 50  # Double bull
                    ring_value = 1
                else:
                    segment_value = 25  # Single bull
                    ring_value = 1
            else:
                # Check double ring
                if regions['doubles']['inner_radius_factor'] <= distance_factor <= regions['doubles']['outer_radius_factor']:
                    ring_value = 2
                # Check triple ring
                elif regions['triples']['inner_radius_factor'] <= distance_factor <= regions['triples']['outer_radius_factor']:
                    ring_value = 3
                # Check of punt binnen het bord valt
                elif distance_factor > regions['doubles']['outer_radius_factor']:
                    return {'success': False, 'error': 'Punt buiten bord'}
            
            score = segment_value * ring_value
            
            return {
                'success': True,
                'segment_value': segment_value,
                'ring_value': ring_value,
                'score': score,
                'segment_index': segment_index,
                'distance_factor': distance_factor,
                'angle': angle
            }
            
        except Exception as e:
            logger.error(f"Error bij segment detectie: {str(e)}")
            return {'success': False, 'error': str(e)}

    def draw_debug(self, frame: np.ndarray, rotation: float = 0) -> np.ndarray:
        """Teken debug visualisatie op frame met blauw triple 20 vak"""
        try:
            if frame is None:
                return frame

            debug_frame = frame.copy()
            
            if self.board_center is None or self.board_radius is None:
                return debug_frame
                
            # Teken scoring regions
            for region_name, region in self.config['scoring_regions'].items():
                outer_radius = int(self.board_radius * region['outer_radius_factor'])
                inner_radius = int(self.board_radius * region['inner_radius_factor'])
                
                # Standaard groene kleur voor de cirkels
                circle_color = (0, 255, 0)
                cv2.circle(debug_frame, self.board_center, outer_radius, circle_color, 1)
                cv2.circle(debug_frame, self.board_center, inner_radius, circle_color, 1)

            # Teken segmentlijnen en het speciale T20 vak
            for i in range(20):
                angle = math.radians(i * 18 + rotation)
                next_angle = math.radians((i + 1) * 18 + rotation)
                
                # Teken segmentlijnen
                end_x = int(self.board_center[0] + self.board_radius * math.cos(angle))
                end_y = int(self.board_center[1] + self.board_radius * math.sin(angle))
                cv2.line(debug_frame, self.board_center, (end_x, end_y), (0, 255, 0), 1)
                
                # Markeer het triple 20 vak (segment 20 is op positie 5)
                if i == 5:  # Index voor segment 20
                    # Bereken hoekpunten voor het triple 20 vak
                    triple_outer = self.board_radius * self.config['scoring_regions']['triples']['outer_radius_factor']
                    triple_inner = self.board_radius * self.config['scoring_regions']['triples']['inner_radius_factor']
                    
                    # Maak een lijst van punten voor het triple 20 vak
                    pts = np.array([
                        [
                            int(self.board_center[0] + triple_outer * math.cos(angle)),
                            int(self.board_center[1] + triple_outer * math.sin(angle))
                        ],
                        [
                            int(self.board_center[0] + triple_outer * math.cos(next_angle)),
                            int(self.board_center[1] + triple_outer * math.sin(next_angle))
                        ],
                        [
                            int(self.board_center[0] + triple_inner * math.cos(next_angle)),
                            int(self.board_center[1] + triple_inner * math.sin(next_angle))
                        ],
                        [
                            int(self.board_center[0] + triple_inner * math.cos(angle)),
                            int(self.board_center[1] + triple_inner * math.sin(angle))
                        ]
                    ], np.int32)
                    
                    # Teken een blauw triple 20 vak
                    cv2.fillPoly(debug_frame, [pts], (255, 0, 0))  # Blauw vulling
                    cv2.polylines(debug_frame, [pts], True, (0, 255, 0), 1)  # Groene rand
                
                # Voeg segmentnummers toe
                text_angle = angle + math.pi/36
                text_radius = self.board_radius * 0.75
                text_x = int(self.board_center[0] + text_radius * math.cos(text_angle))
                text_y = int(self.board_center[1] + text_radius * math.sin(text_angle))
                
                segment_value = self.get_segment_value(i)
                cv2.putText(debug_frame, str(segment_value), (text_x, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
            return debug_frame
            
        except Exception as e:
            logger.error(f"Error in debug visualization: {str(e)}")
            return frame

    def get_segment_value(self, segment_index: int) -> int:
        """Krijg puntenwaarde voor een segment"""
        segment_values = [10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5, 20, 1, 18, 4, 13, 6]
        return segment_values[segment_index % 20]

    def start_calibration(self, root: tk.Tk, cameras: Dict) -> None:
        """Start het kalibratieproces voor de camera's"""
        self.calibration_ui = CalibrationUI(root, self, cameras)

    def save_calibration(self, camera_name: str, center: Tuple[int, int], radius: int, rotation: float = 0) -> None:
        """Sla kalibratie op voor een specifieke camera"""
        if 'cameras' not in self.config:
            self.config['cameras'] = {}
            
        self.config['cameras'][camera_name] = {
            'calibration': {
                'center': center,
                'radius': radius,
                'rotation': rotation
            }
        }
        
        self.save_config()

    def save_config(self) -> None:
        """Sla configuratie op naar bestand"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuratie opgeslagen")
        except Exception as e:
            logger.error(f"Error bij opslaan config: {str(e)}")



class CalibrationUI:
    def __init__(self, root: tk.Tk, detector: DartboardDetector, cameras: Dict):
        self.root = root
        self.detector = detector
        self.cameras = cameras
        self.current_camera_index = 0
        self.preview_active = False
        self.rotation = 0
        
        # Reset root window
        for widget in root.winfo_children():
            widget.destroy()
            
        self.setup_ui()
        
    def setup_ui(self):
        """Setup het kalibratie interface"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Status label
        self.status_label = ttk.Label(
            self.main_frame,
            text=f"Kalibreren camera {self.current_camera_index + 1}",
            font=('Arial', 14, 'bold')
        )
        self.status_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Preview frames
        self.setup_preview_frames()
        
        # Controls
        self.setup_controls()
        
        # Start preview
        self.start_preview()
        
    def setup_preview_frames(self):
        """Setup preview frames voor origineel en gedetecteerd beeld"""
        preview_frame = ttk.Frame(self.main_frame)
        preview_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Origineel beeld
        self.original_canvas = tk.Canvas(
            preview_frame,
            width=640,
            height=360,
            bg='black'
        )
        self.original_canvas.grid(row=0, column=0, padx=5)
        
        # Gedetecteerd beeld
        self.detection_canvas = tk.Canvas(
            preview_frame,
            width=640,
            height=360,
            bg='black'
        )
        self.detection_canvas.grid(row=0, column=1, padx=5)
        
    def setup_controls(self):
        """Setup control knoppen"""
        control_frame = ttk.Frame(self.main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Rotatie controls
        ttk.Label(control_frame, text="Rotatie:").grid(row=0, column=0, padx=5)
        ttk.Button(
            control_frame,
            text="-",
            command=lambda: self.adjust_rotation(-5)
        ).grid(row=0, column=1, padx=2)
        ttk.Button(
            control_frame,
            text="+",
            command=lambda: self.adjust_rotation(5)
        ).grid(row=0, column=2, padx=2)
        
        # Save en Next knoppen
        ttk.Button(
            control_frame,
            text="Save",
            command=self.save_current
        ).grid(row=1, column=0, pady=10, padx=5)
        
        self.next_button = ttk.Button(
            control_frame,
            text="Next Camera" if self.current_camera_index < 2 else "Complete",
            command=self.next_camera
        )
        self.next_button.grid(row=1, column=1, columnspan=2, pady=10, padx=5)
        
    def start_preview(self):
        """Start camera preview"""
        self.preview_active = True
        self.update_preview()
        
    def update_preview(self):
        """Update camera preview"""
        if not self.preview_active:
            return
            
        # Krijg huidige camera
        current_camera = list(self.cameras.values())[self.current_camera_index]
        frame = current_camera['last_frame']
        
        if frame is not None:
            # Resize voor display
            display_frame = cv2.resize(frame, (640, 360))
            
            # Detecteer bord
            detected, info = self.detector.detect_board(display_frame)
            
            if detected:
                # Maak debug visualisatie
                debug_frame = self.detector.draw_debug(display_frame, self.rotation)
                
                # Update beide canvassen
                self.show_frame(display_frame, self.original_canvas)
                self.show_frame(debug_frame, self.detection_canvas)
            else:
                # Alleen origineel frame
                self.show_frame(display_frame, self.original_canvas)
                self.detection_canvas.delete("all")
                
        # Schedule volgende update
        if self.preview_active:
            self.root.after(30, self.update_preview)
            
    def show_frame(self, frame: np.ndarray, canvas: tk.Canvas):
        """Toon frame op canvas"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        photo = ImageTk.PhotoImage(image=img)
        
        canvas.delete("all")
        canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        canvas.image = photo
        
    def adjust_rotation(self, delta: float):
        """Pas rotatie aan"""
        self.rotation = (self.rotation + delta) % 360
        
    def save_current(self):
        """Sla kalibratie op voor huidige camera"""
        current_camera = list(self.cameras.keys())[self.current_camera_index]
        
        if self.detector.board_center and self.detector.board_radius:
            self.detector.save_calibration(
                current_camera,
                self.detector.board_center,
                self.detector.board_radius,
                self.rotation
            )
            messagebox.showinfo("Success", f"Kalibratie opgeslagen voor {current_camera}")
        else:
            messagebox.showerror("Error", "Geen dartbord gedetecteerd")
            
    def next_camera(self):
        """Ga naar volgende camera of rond af"""
        if self.current_camera_index < 2:
            self.current_camera_index += 1
            self.rotation = 0
            self.status_label.config(text=f"Kalibreren camera {self.current_camera_index + 1}")
            self.next_button.config(
                text="Next Camera" if self.current_camera_index < 2 else "Complete"
            )
        else:
            # Kalibratie compleet
            self.complete_calibration()
            
    def complete_calibration(self):
        """Rond kalibratie proces af"""
        try:
            # Sla finale configuratie op
            self.detector.save_config()
            messagebox.showinfo("Success", "Kalibratie succesvol afgerond!")
            
            # Stop preview
            self.preview_active = False
            
            # Sluit kalibratie window
            self.root.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error bij afronden kalibratie: {str(e)}")
            
    def stop_preview(self):
        """Stop camera preview"""
        self.preview_active = False
        self.original_canvas.delete("all")
        self.detection_canvas.delete("all")