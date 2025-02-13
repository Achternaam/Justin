import cv2
import numpy as np
import json
import logging
from typing import Tuple, Optional, Dict, List
import math

logger = logging.getLogger('dart_scorer.detector')

class DartboardDetector:
    def __init__(self, config_path: str = 'config/board_config.json'):
        self.config_path = config_path
        self.load_config()
        self.board_center = None
        self.board_radius = None
        self.perspective_matrix = None
        
    def load_config(self):
        """Laad detectie configuratie uit JSON bestand"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info("Board configuratie succesvol geladen")
        except Exception as e:
            logger.error(f"Error bij laden board config: {str(e)}")
            raise
            
    def detect_board(self, frame: np.ndarray) -> Tuple[bool, Optional[Dict]]:
        """Detecteer het dartbord in het frame"""
        try:
            # Converteer naar HSV voor betere kleurdetectie
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Detecteer zwarte ring van het bord
            black_range = self.config['board_detection']['hsv_ranges']['black']
            black_mask = cv2.inRange(
                hsv,
                np.array(black_range['lower']),
                np.array(black_range['upper'])
            )
            
            # Pas morphological operations toe
            kernel = np.ones((5,5), np.uint8)
            black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
            black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)
            
            # Detecteer cirkels met Hough transform
            circles = cv2.HoughCircles(
                black_mask,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=self.config['board_detection']['circle_detection']['min_distance'],
                param1=self.config['board_detection']['circle_detection']['param1'],
                param2=self.config['board_detection']['circle_detection']['param2'],
                minRadius=self.config['board_detection']['circle_detection']['min_radius'],
                maxRadius=self.config['board_detection']['circle_detection']['max_radius']
            )
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                # Neem de grootste cirkel
                circle = circles[0][0]
                self.board_center = (circle[0], circle[1])
                self.board_radius = circle[2]
                
                return True, {
                    'center': self.board_center,
                    'radius': self.board_radius
                }
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error in board detection: {str(e)}")
            return False, None
            
    def detect_dart(self, frame: np.ndarray) -> Tuple[bool, Optional[Dict]]:
        """Detecteer een dart in het frame"""
        try:
            if self.board_center is None:
                return False, None
                
            # Converteer naar HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Maak een ROI rond het bord
            x, y = self.board_center
            r = self.board_radius
            roi = frame[y-r:y+r, x-r:x+r]
            roi_hsv = hsv[y-r:y+r, x-r:x+r]
            
            # Detecteer dart (aanname: dart heeft een specifieke kleur)
            dart_color = self.config['board_detection']['hsv_ranges']['red']
            dart_mask = cv2.inRange(
                roi_hsv,
                np.array(dart_color['lower']),
                np.array(dart_color['upper'])
            )
            
            # Vind dart contours
            contours, _ = cv2.findContours(
                dart_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if contours:
                # Vind grootste contour (waarschijnlijk de dart)
                dart_contour = max(contours, key=cv2.contourArea)
                M = cv2.moments(dart_contour)
                
                if M["m00"] != 0:
                    # Bereken dart positie relatief aan bord centrum
                    dart_x = int(M["m10"] / M["m00"]) + (x - r)
                    dart_y = int(M["m01"] / M["m00"]) + (y - r)
                    
                    return True, {
                        'position': (dart_x, dart_y),
                        'relative_position': (dart_x - x, dart_y - y)
                    }
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error in dart detection: {str(e)}")
            return False, None
            
    def calibrate_board(self, frame: np.ndarray, reference_points: List[Tuple[int, int]]) -> bool:
        """Kalibreer het bord met referentiepunten"""
        try:
            if len(reference_points) != 4:
                logger.error("Exact 4 referentiepunten nodig voor kalibratie")
                return False
                
            # Bron punten zijn de referentiepunten
            src_points = np.float32(reference_points)
            
            # Doel punten zijn een perfect vierkant
            dst_points = np.float32([
                [0, 0],
                [500, 0],
                [500, 500],
                [0, 500]
            ])
            
            # Bereken perspective transform matrix
            self.perspective_matrix = cv2.getPerspectiveTransform(
                src_points,
                dst_points
            )
            
            # Sla kalibratie op in config
            self.config['calibration']['perspective_matrix'] = self.perspective_matrix.tolist()
            self.save_config()
            
            return True
            
        except Exception as e:
            logger.error(f"Error tijdens kalibratie: {str(e)}")
            return False
            
    def save_config(self):
        """Sla huidige configuratie op"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Board configuratie opgeslagen")
        except Exception as e:
            logger.error(f"Error bij opslaan board config: {str(e)}")
            
    def draw_debug(self, frame: np.ndarray) -> np.ndarray:
        """Teken debug informatie op het frame"""
        debug_frame = frame.copy()
        
        if self.board_center and self.board_radius:
            # Teken gedetecteerd bord
            cv2.circle(
                debug_frame,
                self.board_center,
                self.board_radius,
                (0, 255, 0),
                2
            )
            
            # Teken scoring regions
            for region in ['doubles', 'triples']:
                factor = self.config['scoring_regions'][region]['outer_radius_factor']
                radius = int(self.board_radius * factor)
                cv2.circle(
                    debug_frame,
                    self.board_center,
                    radius,
                    (255, 0, 0),
                    1
                )
                
            # Teken bullseye
            bull_radius = int(self.board_radius * 
                            self.config['scoring_regions']['bullseye']['outer_radius_factor'])
            cv2.circle(
                debug_frame,
                self.board_center,
                bull_radius,
                (0, 0, 255),
                2
            )
            
        return debug_frame