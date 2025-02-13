import math
import json
import logging
from typing import Tuple, Dict, Optional
import numpy as np

logger = logging.getLogger('dart_scorer.scorer')

class ScoreCalculator:
    def __init__(self, config_path: str = 'config/board_config.json'):
        self.config_path = config_path
        self.load_config()
        self.current_score = 501  # Standaard beginnen met 501
        self.throws = []
        self.current_player = 1
        self.players = {1: {'score': 501, 'throws': []},
                       2: {'score': 501, 'throws': []}}
        
    def load_config(self):
        """Laad scoring configuratie"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info("Scoring configuratie geladen")
        except Exception as e:
            logger.error(f"Error bij laden scoring config: {str(e)}")
            raise
            
    def calculate_score(self, hit_position: Tuple[int, int], 
                       board_center: Tuple[int, int],
                       board_radius: int) -> Dict:
        """Bereken score voor een dart hit"""
        try:
            # Bereken afstand en hoek vanaf centrum
            dx = hit_position[0] - board_center[0]
            dy = hit_position[1] - board_center[1]
            distance = math.sqrt(dx*dx + dy*dy)
            angle = math.degrees(math.atan2(dy, dx))
            
            # Normaliseer hoek naar 0-360
            if angle < 0:
                angle += 360
                
            # Bepaal multiplicator (single, double, triple)
            multiplier = self._get_multiplier(distance, board_radius)
            
            # Bepaal segment waarde
            segment_value = self._get_segment_value(angle)
            
            # Check voor bullseye
            if self._is_bullseye(distance, board_radius):
                score = 50 if self._is_double_bull(distance, board_radius) else 25
                multiplier = 1
                segment_value = score
            else:
                score = segment_value * multiplier
                
            result = {
                'score': score,
                'multiplier': multiplier,
                'segment_value': segment_value,
                'angle': angle,
                'distance_factor': distance / board_radius
            }
            
            # Update throws history voor huidige speler
            self.players[self.current_player]['throws'].append(result)
            self._update_player_score(self.current_player, score)
            
            return result
            
        except Exception as e:
            logger.error(f"Error bij score berekening: {str(e)}")
            return {'score': 0, 'error': str(e)}
            
    def _get_multiplier(self, distance: float, board_radius: float) -> int:
        """Bepaal vermenigvuldigingsfactor gebaseerd op afstand"""
        distance_factor = distance / board_radius
        
        # Check triple ring
        triple_outer = self.config['scoring_regions']['triples']['outer_radius_factor']
        triple_inner = self.config['scoring_regions']['triples']['inner_radius_factor']
        if triple_inner <= distance_factor <= triple_outer:
            return 3
            
        # Check double ring
        double_outer = self.config['scoring_regions']['doubles']['outer_radius_factor']
        double_inner = self.config['scoring_regions']['doubles']['inner_radius_factor']
        if double_inner <= distance_factor <= double_outer:
            return 2
            
        return 1
        
    def _get_segment_value(self, angle: float) -> int:
        """Bepaal segment waarde gebaseerd op hoek"""
        segments = self.config['point_values']['segments']
        
        # Vind het juiste segment
        for segment in segments:
            next_angle = (segment['angle'] + 18) % 360
            if segment['angle'] <= angle < next_angle:
                return segment['value']
                
        # Fallback naar eerste segment
        return segments[0]['value']
        
    def _is_bullseye(self, distance: float, board_radius: float) -> bool:
        """Check of hit in bullseye gebied is"""
        distance_factor = distance / board_radius
        return distance_factor <= self.config['scoring_regions']['bullseye']['outer_radius_factor']
        
    def _is_double_bull(self, distance: float, board_radius: float) -> bool:
        """Check of hit in dubbel bull gebied is"""
        distance_factor = distance / board_radius
        return distance_factor <= self.config['scoring_regions']['bullseye']['inner_radius_factor']
        
    def _update_player_score(self, player: int, points: int):
        """Update score voor een specifieke speler"""
        new_score = self.players[player]['score'] - points
        if new_score >= 0:
            self.players[player]['score'] = new_score
            
    def switch_player(self):
        """Wissel naar de volgende speler"""
        self.current_player = 2 if self.current_player == 1 else 1
        logger.info(f"Gewisseld naar speler {self.current_player}")
        
    def get_player_score(self, player: int) -> int:
        """Haal score op voor een specifieke speler"""
        return self.players[player]['score']
        
    def get_player_throws(self, player: int) -> list:
        """Haal worpen geschiedenis op voor een specifieke speler"""
        return self.players[player]['throws']
        
    def reset_game(self, starting_score: int = 501):
        """Reset het spel met een nieuwe startscore"""
        for player in self.players:
            self.players[player]['score'] = starting_score
            self.players[player]['throws'] = []
        self.current_player = 1
        logger.info(f"Spel gereset naar {starting_score}")
        
    def validate_finish(self, player: int) -> Tuple[bool, str]:
        """Valideer of de huidige score een geldige finish is voor een speler"""
        score = self.players[player]['score']
        
        if score > 170:
            return False, "Score te hoog voor finish"
            
        if score == 0:
            throws = self.players[player]['throws']
            last_throw = throws[-1] if throws else None
            if last_throw and last_throw['multiplier'] == 2:
                return True, f"Game shot! Speler {player} heeft gewonnen!"
            return False, "Finish moet met een dubbel"
            
        # Check voor mogelijke finishes
        possible_finish = self._get_possible_finish(score)
        if possible_finish:
            return True, f"Mogelijke finish voor speler {player}: {possible_finish}"
            
        return False, "Geen geldige finish mogelijk"
        
    def _get_possible_finish(self, score: int) -> Optional[str]:
        """Geef mogelijke finish combinatie voor een score"""
        # Bekende finish combinaties
        finishes = {
            170: "T20 T20 DB",
            167: "T20 T19 DB",
            164: "T20 T18 DB",
            161: "T20 T17 DB",
            160: "T20 T20 D20",
            # Voeg meer finishes toe als nodig
        }
        
        return finishes.get(score)
        
    def get_game_statistics(self, player: int) -> Dict:
        """Bereken statistieken voor een speler"""
        throws = self.players[player]['throws']
        if not throws:
            return {
                'average': 0,
                'doubles_hit': 0,
                'triples_hit': 0,
                'bullseyes': 0
            }
            
        total_score = sum(t['score'] for t in throws)
        doubles = sum(1 for t in throws if t['multiplier'] == 2)
        triples = sum(1 for t in throws if t['multiplier'] == 3)
        bullseyes = sum(1 for t in throws if t['score'] in [25, 50])
        
        return {
            'average': total_score / len(throws),
            'doubles_hit': doubles,
            'triples_hit': triples,
            'bullseyes': bullseyes
        }