import cv2
import numpy as np
import math

class DartboardDetector:
    def __init__(self):
        # Dartbord segment waardes (van buitenaf met de klok mee)
        self.segments = [6, 13, 4, 18, 1, 20, 5, 12, 9, 14, 11, 8, 16, 7, 19, 3, 17, 2, 15, 10]
        
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
        
        # Detection parameters
        self.min_dart_area = 100
        self.detection_threshold = 50

    def detect_dartboard(self, frame):
        """Detect dartboard in frame using Hough circles"""
        if frame is None:
            return None
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=100,
            maxRadius=300
        )
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            return circles[0][0]  # Return first detected circle
        return None

    def detect_darts(self, frame):
        """Detect darts in frame"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define color ranges for dart detection
        # Light colored darts (white, silver)
        lower_light = np.array([0, 0, 200])
        upper_light = np.array([180, 30, 255])
        mask_light = cv2.inRange(hsv, lower_light, upper_light)
        
        # Dark colored darts (black)
        lower_dark = np.array([0, 0, 0])
        upper_dark = np.array([180, 255, 30])
        mask_dark = cv2.inRange(hsv, lower_dark, upper_dark)
        
        # Combine masks
        mask = cv2.bitwise_or(mask_light, mask_dark)
        
        # Noise reduction
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        dart_positions = []
        for contour in contours:
            if cv2.contourArea(contour) > self.min_dart_area:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    dart_positions.append((cx, cy))
        
        return dart_positions

    def calculate_score(self, dart_position, board_center, board_radius, rotation_offset=0):
        """Calculate score for dart position"""
        if not all([dart_position, board_center, board_radius]):
            return 0
            
        # Calculate distance from center as percentage of radius
        dx = dart_position[0] - board_center[0]
        dy = dart_position[1] - board_center[1]
        distance = math.sqrt(dx*dx + dy*dy) / board_radius
        
        # Check bull's eye and outer bull
        if distance <= self.BULL_DIST:
            return self.BULL
        if distance <= self.OUTER_BULL_DIST:
            return self.OUTER_BULL
            
        # Calculate angle
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
            
        # Apply rotation offset
        angle = (angle + rotation_offset) % 360
        
        # Determine segment (18 degrees per segment)
        segment_idx = int((angle + 9) / 18) % 20
        segment_value = self.segments[segment_idx]
        
        # Determine multiplier based on distance
        if self.OUTER_DOUBLE_RING_DIST <= distance <= self.DOUBLE_RING_DIST:
            return segment_value * 2  # Double
        elif self.INNER_TRIPLE_RING_DIST <= distance <= self.TRIPLE_RING_DIST:
            return segment_value * 3  # Triple
        elif distance > self.DOUBLE_RING_DIST:
            return 0  # Miss
        else:
            return segment_value  # Single

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

    def get_segment_info(self):
        """Return information about dartboard segments"""
        return {
            'segments': self.segments,
            'rings': {
                'double': (self.OUTER_DOUBLE_RING_DIST, self.DOUBLE_RING_DIST),
                'triple': (self.INNER_TRIPLE_RING_DIST, self.TRIPLE_RING_DIST),
                'outer_bull': self.OUTER_BULL_DIST,
                'bull': self.BULL_DIST
            }
        }