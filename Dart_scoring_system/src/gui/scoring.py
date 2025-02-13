import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import logging
from typing import Dict, Callable
import json
from PIL import Image, ImageTk

logger = logging.getLogger('dart_scorer.gui.scoring')

class ScoringGUI:
    def __init__(self, root: tk.Tk, camera_manager, detector, scorer):
        self.root = root
        self.camera_manager = camera_manager
        self.detector = detector
        self.scorer = scorer
        
        # Venster instellingen
        self.root.title("Dart Scorer - Game")
        self.root.geometry("1400x900")
        
        # Variabelen
        self.preview_active = False
        self.game_active = False
        self.current_player = 1
        self.throws_left = 3
        
        # GUI setup
        self.setup_gui()
        
    def setup_gui(self):
        """Initialiseer de GUI elementen"""
        # Hoofdframe
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Maak secties
        self.setup_camera_section()
        self.setup_score_section()
        self.setup_control_section()
        self.setup_history_section()
        
        # Grid configuratie
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
    def setup_camera_section(self):
        """Maak camera preview sectie"""
        camera_frame = ttk.LabelFrame(self.main_frame, text="Camera Views", padding="10")
        camera_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=5, pady=5)
        
        # Preview canvassen voor elke camera
        self.camera_canvases = {}
        for i, cam_name in enumerate(['camera1', 'camera2', 'camera3']):
            frame = ttk.Frame(camera_frame)
            frame.grid(row=i, column=0, padx=5, pady=5, sticky="nsew")
            
            # Label
            ttk.Label(frame, text=f"{cam_name}").pack(pady=2)
            
            # Canvas
            canvas = tk.Canvas(frame, width=400, height=300, bg='black')
            canvas.pack(padx=5, pady=5)
            self.camera_canvases[cam_name] = canvas
            
    def setup_score_section(self):
        """Maak score display sectie"""
        score_frame = ttk.LabelFrame(self.main_frame, text="Scores", padding="10")
        score_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Player 1 score
        p1_frame = ttk.Frame(score_frame)
        p1_frame.pack(fill=tk.X, pady=5)
        ttk.Label(p1_frame, text="Player 1:", font=('Arial', 14)).pack(side=tk.LEFT)
        self.p1_score = ttk.Label(p1_frame, text="501", font=('Arial', 24))
        self.p1_score.pack(side=tk.RIGHT)
        
        # Player 2 score
        p2_frame = ttk.Frame(score_frame)
        p2_frame.pack(fill=tk.X, pady=5)
        ttk.Label(p2_frame, text="Player 2:", font=('Arial', 14)).pack(side=tk.LEFT)
        self.p2_score = ttk.Label(p2_frame, text="501", font=('Arial', 24))
        self.p2_score.pack(side=tk.RIGHT)
        
        # Current throw info
        throw_frame = ttk.Frame(score_frame)
        throw_frame.pack(fill=tk.X, pady=10)
        self.throw_label = ttk.Label(throw_frame, text="Throws left: 3", font=('Arial', 12))
        self.throw_label.pack()
        
        # Current player indicator
        self.player_label = ttk.Label(score_frame, text="Player 1 to throw", font=('Arial', 14))
        self.player_label.pack(pady=10)
        
    def setup_control_section(self):
        """Maak controle knoppen sectie"""
        control_frame = ttk.Frame(self.main_frame, padding="10")
        control_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        # Start/Stop Game knop
        self.game_button = ttk.Button(
            control_frame,
            text="Start Game",
            command=self.toggle_game
        )
        self.game_button.pack(pady=5)
        
        # Manual score correctie
        correction_frame = ttk.LabelFrame(control_frame, text="Score Correction", padding="5")
        correction_frame.pack(fill=tk.X, pady=5)
        
        self.correction_value = ttk.Entry(correction_frame, width=10)
        self.correction_value.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            correction_frame,
            text="Apply",
            command=self.apply_correction
        ).pack(side=tk.LEFT, padx=5)
        
        # Undo knop
        ttk.Button(
            control_frame,
            text="Undo Last Throw",
            command=self.undo_last_throw
        ).pack(pady=5)
        
        # Reset Game knop
        ttk.Button(
            control_frame,
            text="Reset Game",
            command=self.reset_game
        ).pack(pady=5)
        
    def setup_history_section(self):
        """Maak score geschiedenis sectie"""
        history_frame = ttk.LabelFrame(self.main_frame, text="Score History", padding="10")
        history_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Treeview voor score geschiedenis
        self.history_tree = ttk.Treeview(
            history_frame,
            columns=("player", "throw", "score", "remaining"),
            show="headings"
        )
        
        # Kolom headers
        self.history_tree.heading("player", text="Player")
        self.history_tree.heading("throw", text="Throw")
        self.history_tree.heading("score", text="Score")
        self.history_tree.heading("remaining", text="Remaining")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            history_frame,
            orient=tk.VERTICAL,
            command=self.history_tree.yview
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack elementen
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def toggle_game(self):
        """Start/Stop het spel"""
        self.game_active = not self.game_active
        if self.game_active:
            self.start_game()
        else:
            self.stop_game()
            
    def start_game(self):
        """Start een nieuw spel"""
        self.game_active = True
        self.game_button.config(text="Stop Game")
        self.preview_active = True
        self.current_player = 1
        self.throws_left = 3
        self.update_displays()
        self.start_camera_processing()
        
    def stop_game(self):
        """Stop het huidige spel"""
        self.game_active = False
        self.game_button.config(text="Start Game")
        self.preview_active = False
        self.stop_camera_processing()
        
    def start_camera_processing(self):
        """Start camera verwerking en dart detectie"""
        if not self.preview_active:
            return
            
        for cam_name, canvas in self.camera_canvases.items():
            self.process_camera(cam_name, canvas)
            
    def process_camera(self, camera_name: str, canvas: tk.Canvas):
        """Verwerk camera feed en detecteer darts"""
        if not self.preview_active:
            return
            
        try:
            # Krijg frame van camera
            frame = self.camera_manager.get_frame(camera_name)
            if frame is not None:
                # Dart detectie
                found_dart, dart_info = self.detector.detect_dart(frame)
                if found_dart:
                    self.process_dart_hit(dart_info)
                    
                # Update preview
                frame = cv2.resize(frame, (400, 300))
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                img_tk = ImageTk.PhotoImage(image=img)
                canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                canvas.image = img_tk
                
            # Schedule volgende update
            self.root.after(30, lambda: self.process_camera(camera_name, canvas))
            
        except Exception as e:
            logger.error(f"Error bij camera processing: {str(e)}")
            
    def process_dart_hit(self, dart_info: Dict):
        """Verwerk een gedetecteerde dart hit"""
        if self.throws_left > 0 and self.game_active:
            # Bereken score
            score_info = self.scorer.calculate_score(
                dart_info['position'],
                dart_info['board_center'],
                dart_info['board_radius']
            )
            
            # Update score
            self.update_score(score_info['score'])
            
            # Update geschiedenis
            self.add_to_history(score_info)
            
            # Update throws left
            self.throws_left -= 1
            if self.throws_left == 0:
                self.switch_player()
                
            self.update_displays()
            
            # Check voor finish
            self.check_finish()
            
    def update_score(self, points: int):
        """Update score voor huidige speler"""
        if self.current_player == 1:
            score = int(self.p1_score['text']) - points
            if score >= 0:
                self.p1_score['text'] = str(score)
        else:
            score = int(self.p2_score['text']) - points
            if score >= 0:
                self.p2_score['text'] = str(score)
                
    def switch_player(self):
        """Wissel naar andere speler"""
        self.current_player = 2 if self.current_player == 1 else 1
        self.throws_left = 3
        self.update_displays()
        
    def update_displays(self):
        """Update alle display elementen"""
        self.throw_label['text'] = f"Throws left: {self.throws_left}"
        self.player_label['text'] = f"Player {self.current_player} to throw"
        
    def add_to_history(self, score_info: Dict):
        """Voeg score toe aan geschiedenis"""
        remaining = self.p1_score['text'] if self.current_player == 1 else self.p2_score['text']
        self.history_tree.insert(
            "",
            0,
            values=(
                f"Player {self.current_player}",
                f"{4-self.throws_left}",
                f"{score_info['score']} ({score_info['multiplier']}x{score_info['segment_value']})",
                remaining
            )
        )
        
    def check_finish(self):
        """Check voor mogelijke finish"""
        current_score = int(self.p1_score['text'] if self.current_player == 1 else self.p2_score['text'])
        if current_score == 0:
            # Check of laatste worp een dubbel was
            last_throw = self.scorer.get_player_throws(self.current_player)[-1]
            if last_throw['multiplier'] == 2:
                messagebox.showinfo("Game Shot!", f"Player {self.current_player} wins!")
                self.stop_game()
            else:
                messagebox.showinfo("Bust!", "Finish moet met een dubbel!")
                self.undo_last_throw()
                
    def apply_correction(self):
        """Pas handmatige score correctie toe"""
        try:
            correction = int(self.correction_value.get())
            self.update_score(-correction)  # Negatief omdat we de correctie willen toevoegen
            self.correction_value.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Voer een geldig getal in")
            
    def undo_last_throw(self):
        """Maak laatste worp ongedaan"""
        # Verwijder laatste item uit geschiedenis
        last_item = self.history_tree.get_children()[0]
        self.history_tree.delete(last_item)
        
        # Reset score
        self.throws_left += 1
        if self.throws_left > 3:
            self.throws_left = 3
            self.current_player = 2 if self.current_player == 1 else 1
            
        self.update_displays()
        
    def reset_game(self):
        """Reset het spel naar begintoestand"""
        if messagebox.askyesno("Reset Game", "Weet je zeker dat je het spel wilt resetten?"):
            self.p1_score['text'] = "501"
            self.p2_score['text'] = "501"
            self.current_player = 1
            self.throws_left = 3
            self.update_displays()
            
            # Clear geschiedenis
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
                
            self.scorer.reset_game()
            
    def stop_camera_processing(self):
        """Stop camera verwerking"""
        self.preview_active = False
        # Reset camera canvassen
        for canvas in self.camera_canvases.values():
            canvas.delete("all")