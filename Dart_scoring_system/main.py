import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import time

class KalmanFilter:
    def __init__(self, dt, u_x, u_y, std_acc, x_std_meas, y_std_meas):
        self.dt = dt
        self.u_x = u_x
        self.u_y = u_y
        self.std_acc = std_acc

        self.A = np.array([[1, 0, self.dt, 0],
                           [0, 1, 0, self.dt],
                           [0, 0, 1, 0],
                           [0, 0, 0, 1]])

        self.B = np.array([[(self.dt**2)/2, 0],
                           [0, (self.dt**2)/2],
                           [self.dt, 0],
                           [0, self.dt]])

        self.H = np.array([[1, 0, 0, 0],
                           [0, 1, 0, 0]])

        self.Q = np.array([[(self.dt**4)/4, 0, (self.dt**3)/2, 0],
                           [0, (self.dt**4)/4, 0, (self.dt**3)/2],
                           [(self.dt**3)/2, 0, self.dt**2, 0],
                           [0, (self.dt**3)/2, 0, self.dt**2]]) * self.std_acc**2

        self.R = np.array([[x_std_meas**2, 0],
                           [0, y_std_meas**2]])

        self.P = np.eye(4)
        self.x = np.zeros((4, 1))

    def predict(self):
        self.x = np.dot(self.A, self.x) + np.dot(self.B, np.array([[self.u_x], [self.u_y]]))
        self.P = np.dot(np.dot(self.A, self.P), self.A.T) + self.Q
        return self.x

    def update(self, z):
        y = z - np.dot(self.H, self.x)
        S = np.dot(self.H, np.dot(self.P, self.H.T)) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        I = np.eye(self.H.shape[1])
        self.P = np.dot(np.dot(I - np.dot(K, self.H), self.P),
                        (I - np.dot(K, self.H)).T) + np.dot(np.dot(K, self.R), K.T)

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
        self.selected_points = []
        self.prev_frame = None
        self.auto_detect_tries = 0
        self.max_auto_detect_tries = 30  # Aantal pogingen voor auto-detectie
        
        # Initialize Kalman filter
        dt = 1.0/30.0
        self.kalman = KalmanFilter(dt, 0, 0, 1.0, 0.1, 0.1)
        
        # Main frame
        self.main_frame = tk.Frame(self.root, bg='#1a75ff', padx=20, pady=20)
        self.main_frame.pack(expand=True, fill='both')
        
        # Setup UI elements
        self.setup_instruction_label()
        self.setup_camera_view()
        self.setup_control_buttons()
        
        # Start met automatische detectie
        self.start_auto_detection()

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
            text="Camera 1 - Detecteren...",
            bg='#1a75ff',
            fg='yellow',
            font=('Arial', 14, 'bold')
        )
        self.status_label.pack(pady=(0, 10))

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
        self.canvas.bind('<Button-1>', self.on_canvas_click)

    def setup_control_buttons(self):
        """Setup control buttons"""
        button_frame = tk.Frame(self.main_frame, bg='#1a75ff')
        button_frame.pack(fill='x', pady=20)
        
        # Manual mode knop
        self.manual_button = tk.Button(
            button_frame,
            text="Switch to Manual",
            command=self.switch_to_manual,
            bg='white',
            width=15,
            height=2,
            state='disabled'
        )
        self.manual_button.pack(side='left', padx=5)
        
        # Reset knop
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

    def start_auto_detection(self):
        """Start automatische detectie"""
        self.auto_detect_tries = 0
        self.instruction_label.config(text="Automatische dartbord detectie...")
        self.status_label.config(text=f"Camera {self.current_camera_index + 1} - Detecteren...")
        self.try_auto_detect()

    def try_auto_detect(self):
        """Probeer dartbord automatisch te detecteren"""
        if self.auto_detect_tries >= self.max_auto_detect_tries:
            self.manual_button.config(state='normal')
            self.status_label.config(text="Automatische detectie mislukt - Schakel over naar handmatig")
            return

        current_camera = list(self.cameras.values())[self.current_camera_index]
        if current_camera['last_frame'] is not None:
            frame = current_camera['last_frame'].copy()
            frame = cv2.resize(frame, (800, 600))
            
            # Probeer dartbord te detecteren
            detected, corners = self.detect_dartboard(frame)
            
            if detected:
                self.selected_points = corners
                self.draw_detection_result(frame)
                self.next_button.config(state='normal')
                self.status_label.config(text="Dartbord gedetecteerd!")
                return
            
            self.auto_detect_tries += 1
            self.root.after(100, self.try_auto_detect)

    def detect_dartboard(self, frame):
        """Detecteer dartbord met geavanceerde methoden"""
        try:
            # Convert naar grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Pas verschillende blur methoden toe
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            bilateral = cv2.bilateralFilter(blurred, 9, 75, 75)
            
            # Detecteer edges
            edges = cv2.goodFeaturesToTrack(bilateral, 640, 0.0008, 1, 
                                          mask=None,
                                          blockSize=3,
                                          useHarrisDetector=1,
                                          k=0.06)
            
            if edges is None:
                return False, None
                
            # Filter corners
            corners = np.intp(edges)
            mean_corners = np.mean(corners, axis=0)
            corners_filtered = np.array([i for i in corners 
                                       if abs(mean_corners[0][0] - i[0][0]) <= 180 
                                       and abs(mean_corners[0][1] - i[0][1]) <= 120])
            
            if len(corners_filtered) < 30:
                return False, None
                
            # Detecteer cirkels
            circles = cv2.HoughCircles(
                bilateral,
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
                for circle in circles[0, :]:
                    x, y, r = circle
                    
                    # Valideer cirkel met corners
                    points_on_circle = 0
                    for corner in corners_filtered:
                        dist = np.sqrt((corner[0][0] - x)**2 + (corner[0][1] - y)**2)
                        if abs(dist - r) < 10:
                            points_on_circle += 1
                    
                    if points_on_circle >= 10:
                        # Bereken 4 punten op de cirkel
                        points = []
                        for angle in [0, 90, 180, 270]:
                            rad = np.radians(angle)
                            px = int(x + r * np.cos(rad))
                            py = int(y + r * np.sin(rad))
                            points.append([px, py])
                        
                        return True, points
            
            return False, None
            
        except Exception as e:
            print(f"Error in detectie: {str(e)}")
            return False, None

    def draw_detection_result(self, frame):
        """Teken detectie resultaat"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Teken punten en verbindingen
        for i, point in enumerate(self.selected_points):
            cv2.circle(frame_rgb, tuple(point), 5, (255, 0, 0), -1)
            cv2.putText(frame_rgb, str(i+1), 
                       (point[0]+10, point[1]+10),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # Update canvas
        self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def switch_to_manual(self):
        """Schakel over naar handmatige modus"""
        self.instruction_label.config(text="Handmatige kalibratie - Selecteer 4 punten")
        self.status_label.config(text=f"Camera {self.current_camera_index + 1} - Selecteer punt 1/4")
        self.selected_points = []
        self.reset_button.config(state='normal')
        self.manual_button.config(state='disabled')
        self.update_canvas()

    def update_canvas(self):
        """Update canvas met huidige frame"""
        current_camera = list(self.cameras.values())[self.current_camera_index]
        if current_camera['last_frame'] is not None:
            frame = current_camera['last_frame'].copy()
            frame = cv2.resize(frame, (800, 600))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Teken geselecteerde punten
            for i, point in enumerate(self.selected_points):
                cv2.circle(frame_rgb, tuple(point), 5, (255, 0, 0), -1)
                cv2.putText(frame_rgb, str(i+1),
                           (point[0]+10, point[1]+10),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

    [Voeg de rest van de vorige code hier toe voor on_canvas_click, reset_points, next_camera, etc.]

def start_dartboard_calibration(root, cameras):
    """Start het dartbord kalibratie scherm"""
    return DartboardCalibrationScreen(root, cameras)