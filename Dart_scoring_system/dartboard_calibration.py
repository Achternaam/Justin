import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import time

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
        self.calibration_points = []
        self.selected_point = None
        self.detected_circles = []
        self.manual_mode = False
        self.reference_positions = [
            {"name": "20-1", "description": "tussen 20 en 1"},
            {"name": "13-6", "description": "tussen 13 en 6"},
            {"name": "17-3", "description": "tussen 17 en 3"},
            {"name": "18-8", "description": "tussen 18 en 8"}
        ]
        
        # Initialize detection variables
        self.prev_frame = None
        self.kalman_filter = cv2.KalmanFilter(4, 2)
        self.setup_kalman_filter()
        
        # Main frame
        self.main_frame = tk.Frame(self.root, bg='#1a75ff', padx=20, pady=20)
        self.main_frame.pack(expand=True, fill='both')
        
        # Setup UI elements
        self.setup_instruction_label()
        self.setup_camera_view()
        self.setup_control_buttons()
        
        # Start met automatische detectie
        self.capture_and_detect()

    def setup_kalman_filter(self):
        """Initialize Kalman Filter parameters"""
        self.kalman_filter.measurementMatrix = np.array([[1, 0, 0, 0],
                                                        [0, 1, 0, 0]], np.float32)
        self.kalman_filter.transitionMatrix = np.array([[1, 0, 1, 0],
                                                       [0, 1, 0, 1],
                                                       [0, 0, 1, 0],
                                                       [0, 0, 0, 1]], np.float32)
        self.kalman_filter.processNoiseCov = np.array([[1, 0, 0, 0],
                                                      [0, 1, 0, 0],
                                                      [0, 0, 1, 0],
                                                      [0, 0, 0, 1]], np.float32) * 0.03

    def cam2gray(self, frame):
        """Convert frame to grayscale"""
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def get_threshold(self, frame):
        """Get threshold image for motion detection"""
        if self.prev_frame is None:
            self.prev_frame = self.cam2gray(frame)
            return None
            
        current_frame = self.cam2gray(frame)
        dimg = cv2.absdiff(self.prev_frame, current_frame)
        blur = cv2.GaussianBlur(dimg, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 60, 255, cv2.THRESH_BINARY)
        
        kernel = np.ones((5, 5), np.uint8)
        closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        opening = cv2.morphologyEx(closing, cv2.MORPH_OPEN, kernel)
        
        self.prev_frame = current_frame
        return opening

    def detect_dartboard(self, frame):
        """Detecteer dartbord met geavanceerde methoden"""
        try:
            # Convert naar grayscale
            gray = self.cam2gray(frame)
            
            # Detecteer edges
            edges = cv2.goodFeaturesToTrack(gray, 640, 0.0008, 1, 
                                          blockSize=3, 
                                          useHarrisDetector=1, 
                                          k=0.06)
            
            if edges is None:
                return False, None
                
            corners = np.intp(edges)
            
            # Filter corners
            mean_corners = np.mean(corners, axis=0)
            corners_filtered = np.array([i for i in corners 
                                       if abs(mean_corners[0][0] - i[0][0]) <= 180 
                                       and abs(mean_corners[0][1] - i[0][1]) <= 120])
            
            if len(corners_filtered) < 30:
                return False, None
                
            # Detect circles with Hough transform
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=200,
                param1=50,
                param2=30,
                minRadius=100,
                maxRadius=300
            )
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                best_circle = circles[0][0]  # Get the first circle
                
                # Validate circle with corners
                center_x, center_y, radius = best_circle
                circle_region = np.zeros_like(gray)
                cv2.circle(circle_region, (center_x, center_y), radius, 255, 2)
                
                # Count corners near circle perimeter
                corner_count = sum(1 for corner in corners_filtered
                                 if abs(np.sqrt((corner[0][0] - center_x)**2 + 
                                              (corner[0][1] - center_y)**2) - radius) < 10)
                
                if corner_count >= 10:  # At least 10 corners should lie on the circle
                    self.detected_circles = [best_circle]
                    self.calculate_reference_points(best_circle)
                    return True, best_circle
                    
            return False, None
            
        except Exception as e:
            print(f"Error in detectie: {str(e)}")
            return False, None
        
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
        
        self.action_label = tk.Label(
            self.main_frame,
            text="",
            bg='#1a75ff',
            fg='yellow',
            font=('Arial', 14, 'bold')
        )
        self.action_label.pack(pady=(0, 10))
        
    def set_manual_mode(self):
        """Schakel over naar handmatige kalibratie"""
        self.manual_mode = True
        self.instruction_label.config(
            text="Plaats de 4 referentiepunten op het dartbord.\n" +
                 "Punt 1: tussen 20 en 1\n" +
                 "Punt 2: tussen 13 en 6\n" +
                 "Punt 3: tussen 17 en 3\n" +
                 "Punt 4: tussen 18 en 8"
        )
        self.manual_button.config(state='disabled')
        self.update_points()
        
    def setup_camera_view(self):
        """Setup camera preview"""
        self.camera_frame = tk.Frame(self.main_frame, bg='#1a75ff')
        self.camera_frame.pack(expand=True, fill='both')
        
        self.canvas = tk.Canvas(
            self.camera_frame,
            width=800,
            height=600,
            bg='black',
            highlightbackground='white',
            highlightthickness=2
        )
        self.canvas.pack(expand=True)
        
        # Bind mouse events voor handmatige mode
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_canvas_release)
        
    def setup_control_buttons(self):
        """Setup control buttons"""
        button_frame = tk.Frame(self.main_frame, bg='#1a75ff')
        button_frame.pack(fill='x', pady=20)
        
        # Manual mode knop
        self.manual_button = tk.Button(
            button_frame,
            text="Switch to Manual",
            command=self.set_manual_mode,
            bg='white',
            width=15,
            height=2
        )
        self.manual_button.pack(side='left', padx=5)
        
        # Reset knop (initieel verborgen)
        self.reset_button = tk.Button(
            button_frame,
            text="Reset Points",
            command=self.reset_points,
            bg='white',
            width=15,
            height=2,
            state='disabled'
        )
        self.reset_button.pack(side='left', padx=5)
        
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
        
    def capture_and_detect(self):
        """Capture frame en probeer automatische detectie"""
        current_camera = list(self.cameras.values())[self.current_camera_index]
        
        if current_camera['last_frame'] is not None:
            frame = current_camera['last_frame'].copy()
            
            # Convert en resize
            frame = cv2.resize(frame, (800, 600))
            self.current_frame = frame
            
            # Probeer automatische detectie
            success = self.detect_board()
            
            if success:
                self.action_label.config(text="Dartbord succesvol gedetecteerd!")
                self.next_button.config(state='normal')
                self.manual_button.config(state='disabled')
            else:
                self.action_label.config(text="Automatische detectie mislukt - schakel over naar handmatige kalibratie")
                self.manual_button.config(state='normal')
                
            # Display frame
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            
    def detect_board(self):
        """Detecteer dartbord met OpenCV"""
        try:
            # Convert naar grayscale
            gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
            
            # Blur toepassen
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            
            # Circles detecteren met Hough transform
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=200,
                param1=50,
                param2=30,
                minRadius=100,
                maxRadius=300
            )
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                self.detected_circles = circles[0, :]
                
                # Draw circles
                self.draw_detected_circles()
                
                # Als we precies één cirkel vinden, probeer de referentiepunten te bepalen
                if len(circles[0]) == 1:
                    self.calculate_reference_points(circles[0][0])
                    return True
                    
            return False
            
        except Exception as e:
            print(f"Error in detectie: {str(e)}")
            return False
            
    def draw_detected_circles(self):
        """Teken gedetecteerde cirkels op canvas"""
        for circle in self.detected_circles:
            x, y, r = circle
            self.canvas.create_oval(
                x-r, y-r, x+r, y+r,
                outline='white',
                width=2,
                tags='circle'
            )
            
    def calculate_reference_points(self, circle):
        """Bereken referentiepunten gebaseerd op gedetecteerde cirkel"""
        x, y, r = circle
        self.calibration_points = [
            [x, y - r],  # Top (20-1)
            [x + r, y],  # Right (13-6)
            [x, y + r],  # Bottom (17-3)
            [x - r, y]   # Left (18-8)
        ]
        
    def reset_points(self):
        """Reset calibratie punten"""
        if self.manual_mode:
            self.calibration_points = []
            self.selected_point = None
            self.update_points()
            self.next_button.config(state='disabled')
            
    def draw_point(self, x, y, index, selected=False):
        """Teken een calibratie punt"""
        radius = 5
        color = "red" if selected else "yellow"
        
        # Teken punt
        self.canvas.create_oval(
            x-radius, y-radius, x+radius, y+radius,
            fill=color, outline=color,
            tags=f"point{index}"
        )
        
        # Teken nummer
        self.canvas.create_text(
            x, y-15,
            text=str(index + 1),
            fill=color,
            font=('Arial', 12, 'bold'),
            tags=f"point{index}"
        )
        
    def update_points(self):
        """Update alle punten op canvas"""
        # Clear bestaande punten
        for i in range(4):
            self.canvas.delete(f"point{i}")
            
        # Draw circles again
        self.draw_detected_circles()
        
        # Teken alle punten
        for i, point in enumerate(self.calibration_points):
            self.draw_point(point[0], point[1], i, i == self.selected_point)
            
        # Update next button status
        if self.manual_mode:
            self.next_button.config(state='normal' if len(self.calibration_points) == 4 else 'disabled')
            
        # Update instruction in manual mode
        if self.manual_mode and len(self.calibration_points) < 4:
            current_point = len(self.calibration_points)
            ref = self.reference_positions[current_point]
            self.action_label.config(text=f"Plaats punt {current_point + 1}: {ref['description']}")
        elif self.manual_mode:
            self.action_label.config(text="Alle punten geplaatst - verplaats indien nodig")
            
    def on_canvas_click(self, event):
        """Handle mouse click op canvas"""
        if not self.manual_mode:
            return
            
        x, y = event.x, event.y
        
        # Check of click dichtbij bestaand punt is
        for i, point in enumerate(self.calibration_points):
            if (x - point[0])**2 + (y - point[1])**2 < 100:  # 10px radius
                self.selected_point = i
                self.update_points()
                return
                
        # Voeg nieuw punt toe als we nog niet alle punten hebben
        if len(self.calibration_points) < 4:
            self.calibration_points.append([x, y])
            self.update_points()
            
    def on_canvas_drag(self, event):
        """Handle mouse drag op canvas"""
        if not self.manual_mode:
            return
            
        if self.selected_point is not None:
            x, y = event.x, event.y
            self.calibration_points[self.selected_point] = [x, y]
            self.update_points()
            
    def on_canvas_release(self, event):
        """Handle mouse release op canvas"""
        if not self.manual_mode:
            return
            
        self.selected_point = None
        self.update_points()
        
    def next_camera(self):
        """Ga naar volgende camera of rond kalibratie af"""
        if self.manual_mode and len(self.calibration_points) < 4:
            messagebox.showwarning("Warning", "Plaats eerst alle 4 de punten!")
            return
            
        # Sla punten op voor huidige camera
        current_camera = list(self.cameras.values())[self.current_camera_index]
        current_camera['calibration_points'] = self.calibration_points
        
        if self.current_camera_index < 2:
            # Ga naar volgende camera
            self.current_camera_index += 1
            self.manual_mode = False  # Reset naar auto mode voor nieuwe camera
            self.calibration_points = []
            self.capture_and_detect()
            
            # Update button text
            self.next_button.config(
                text="Next Camera" if self.current_camera_index < 2 else "Complete"
            )
            self.next_button.config(state='disabled')
            self.reset_button.config(state='disabled')
        else:
            # Kalibratie compleet
            self.complete_calibration()
            
    def complete_calibration(self):
        """Rond kalibratie af en ga naar volgende stap"""
        print("Calibration complete!")
        # Hier kun je de volgende stap in je systeem starten
        
def start_dartboard_calibration(root, cameras):
    """Start het dartbord kalibratie scherm"""
    return DartboardCalibrationScreen(root, cameras)