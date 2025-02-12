import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
import math
import time
from utils.camera_utils import calculate_dart_position
from utils.dartboard_recognition import DartboardDetector

class DartGameMenu:
    def __init__(self, calibration_data):
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("Genius Darts Software")
        self.root.geometry("1280x800")

        # Initialize from calibration
        self.camera_indexes = calibration_data.get('cameras', [])
        self.rotation_angles = calibration_data.get('rotation_angles', [0, 0, 0])
        
        # Initialize components
        self.camera_streams = []
        self.running = True
        self.current_score = 501
        self.current_player = 1
        self.dart_count = 0
        self.scores_history = []
        self.dartboard_detector = DartboardDetector()
        self.last_detection_time = 0
        self.detection_interval = 1.0 / 30  # 30 FPS max for detection
        
        # Initialize cameras
        self.initialize_cameras()
        
        # Setup UI
        self.setup_ui()
        self.start_camera_processing()

    def initialize_cameras(self):
        """Initialize cameras from calibration data"""
        for idx in self.camera_indexes:
            if idx is not None:
                try:
                    cap = cv2.VideoCapture(idx)
                    if not cap.isOpened():
                        print(f"Warning: Could not open camera {idx}")
                        self.camera_streams.append(None)
                        continue
                        
                    # Set camera properties
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    
                    self.camera_streams.append(cap)
                except Exception as e:
                    print(f"Error initializing camera {idx}: {e}")
                    self.camera_streams.append(None)
            else:
                self.camera_streams.append(None)

    def setup_ui(self):
        # Main container
        self.main_container = ttk.Frame(self.root, padding="10")
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Game controls
        self.setup_game_controls()
        
        # Right panel - Camera views
        self.setup_camera_views()

    def setup_game_controls(self):
        left_panel = ttk.Frame(self.main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Game mode selection
        game_frame = ttk.LabelFrame(left_panel, text="Game Mode")
        game_frame.pack(fill=tk.X, pady=10)
        
        self.game_mode = tk.StringVar(value='501')
        modes = ['501', '301', '201', 'Cricket', 'Around the Clock']
        for mode in modes:
            ttk.Radiobutton(game_frame, text=mode, value=mode, 
                           variable=self.game_mode,
                           command=self.change_game_mode).pack(anchor=tk.W)
        
        # Player info
        player_frame = ttk.LabelFrame(left_panel, text="Current Game")
        player_frame.pack(fill=tk.X, pady=10)
        
        self.score_label = ttk.Label(player_frame, text=f"Score: {self.current_score}")
        self.score_label.pack(pady=5)
        
        self.player_label = ttk.Label(player_frame, text="Player 1's turn")
        self.player_label.pack(pady=5)
        
        self.dart_label = ttk.Label(player_frame, text="Darts: 0/3")
        self.dart_label.pack(pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(control_frame, text="Undo Last Dart",
                  command=self.undo_last_dart).pack(fill=tk.X, pady=2)
        
        ttk.Button(control_frame, text="New Game",
                  command=self.new_game).pack(fill=tk.X, pady=2)

    def setup_camera_views(self):
        right_panel = ttk.Frame(self.main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Camera views
        self.camera_labels = []
        for i in range(len(self.camera_streams)):
            if self.camera_streams[i] is not None:
                frame = ttk.LabelFrame(right_panel, text=f"Camera {i+1}")
                frame.grid(row=i//2, column=i%2, padx=5, pady=5, sticky='nsew')
                
                label = ttk.Label(frame)
                label.pack(padx=5, pady=5)
                self.camera_labels.append(label)
        
        # Score history
        history_frame = ttk.LabelFrame(right_panel, text="Score History")
        history_frame.grid(row=len(self.camera_streams)//2, column=1, 
                         padx=5, pady=5, sticky='nsew')
        
        self.history_text = tk.Text(history_frame, height=10, width=30)
        self.history_text.pack(fill=tk.BOTH, expand=True)

    def change_game_mode(self):
        """Handle game mode change"""
        mode = self.game_mode.get()
        if mode.isdigit():
            self.current_score = int(mode)
            self.new_game()
        else:
            # Handle special game modes
            self.new_game()

    def new_game(self):
        """Start a new game"""
        self.current_score = int(self.game_mode.get()) if self.game_mode.get().isdigit() else 501
        self.current_player = 1
        self.dart_count = 0
        self.scores_history = []
        self.update_display()
        self.history_text.delete(1.0, tk.END)

    def undo_last_dart(self):
        """Undo the last dart throw"""
        if self.scores_history:
            last_score = self.scores_history.pop()
            self.current_score += last_score
            self.dart_count -= 1
            if self.dart_count < 0:
                self.dart_count = 2
                self.current_player = 2 if self.current_player == 1 else 1
            self.update_display()
            
            # Update history display
            self.history_text.delete("end-2c linestart", tk.END)

    def update_display(self):
        """Update all display elements"""
        self.score_label.config(text=f"Score: {self.current_score}")
        self.player_label.config(text=f"Player {self.current_player}'s turn")
        self.dart_label.config(text=f"Darts: {self.dart_count}/3")

    def process_dart_throw(self, score):
        """Process a dart throw and update the game state"""
        if score > 0:
            self.dart_count += 1
            self.current_score -= score
            self.scores_history.append(score)
            
            # Update history
            self.history_text.insert(tk.END, 
                                   f"Player {self.current_player} - Dart {self.dart_count}: {score}\n")
            self.history_text.see(tk.END)
            
            # Check for player switch
            if self.dart_count >= 3:
                self.dart_count = 0
                self.current_player = 2 if self.current_player == 1 else 1
            
            self.update_display()

    def update_camera_feeds(self):
        """Update camera feeds with dart detection"""
        current_time = time.time()
        
        try:
            for i, cap in enumerate(self.camera_streams):
                if cap is not None:
                    ret, frame = cap.read()
                    if ret:
                        # Only perform detection at specified interval
                        if current_time - self.last_detection_time >= self.detection_interval:
                            # Detect dartboard
                            circle = self.dartboard_detector.detect_dartboard(frame)
                            if circle is not None:
                                center = (circle[0], circle[1])
                                radius = circle[2]
                                
                                # Apply rotation from calibration
                                frame = self.dartboard_detector.draw_overlay(
                                    frame, center, radius, self.rotation_angles[i]
                                )
                                
                                # Detect darts
                                dart_positions = self.dartboard_detector.detect_darts(frame)
                                for pos in dart_positions:
                                    score = self.dartboard_detector.calculate_score(
                                        pos, center, radius, self.rotation_angles[i]
                                    )
                                    if score > 0:
                                        self.process_dart_throw(score)
                                    
                                    # Draw dart position and score
                                    cv2.circle(frame, pos, 5, (0, 0, 255), -1)
                                    cv2.putText(frame, str(score), 
                                              (pos[0]+10, pos[1]),
                                              cv2.FONT_HERSHEY_SIMPLEX,
                                              0.5, (0, 0, 255), 1)
                            
                            self.last_detection_time = current_time
                        
                        # Convert and display frame
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame = cv2.resize(frame, (400, 300))
                        img = Image.fromarray(frame)
                        imgtk = ImageTk.PhotoImage(image=img)
                        self.camera_labels[i].imgtk = imgtk
                        self.camera_labels[i].configure(image=imgtk)
            
            if self.running:
                self.root.after(33, self.update_camera_feeds)  # ~30 FPS
                
        except Exception as e:
            print(f"Error updating camera feeds: {e}")
            if self.running:
                self.root.after(1000, self.update_camera_feeds)

    def start_camera_processing(self):
        """Start processing camera feeds"""
        self.update_camera_feeds()

    def run(self):
        """Run the application"""
        self.root.mainloop()

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        for cap in self.camera_streams:
            if cap is not None:
                cap.release()

if __name__ == "__main__":
    # Test with dummy calibration data
    calibration_data = {
        'cameras': [0],  # Only use first camera for testing
        'rotation_angles': [0, 0, 0]
    }
    
    game = DartGameMenu(calibration_data)
    try:
        game.run()
    finally:
        game.cleanup()