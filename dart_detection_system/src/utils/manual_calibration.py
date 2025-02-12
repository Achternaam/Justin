import cv2
import numpy as np

class ManualCalibrationPoints:
    def __init__(self):
        self.calibration_points = []
        self.current_frame = None
        self.reference_points = [
            ("20-1", "Top"),
            ("13-6", "Right"),
            ("11-14", "Bottom"),
            ("3-17", "Left")
        ]
    
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.calibration_points) < 4:
                self.calibration_points.append((x, y))
                # Draw point on frame
                cv2.circle(self.current_frame, (x, y), 5, (0, 255, 0), -1)
                point_name = self.reference_points[len(self.calibration_points)-1][0]
                cv2.putText(self.current_frame, point_name, (x+10, y), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    def get_manual_points(self, frame):
        """Let user select 4 calibration points on the dartboard"""
        self.current_frame = frame.copy()
        window_name = "Select Calibration Points"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        while len(self.calibration_points) < 4:
            cv2.imshow(window_name, self.current_frame)
            # Display instructions
            instruction = f"Click on the border between {self.reference_points[len(self.calibration_points)][0]}"
            cv2.putText(self.current_frame, instruction, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC key to cancel
                self.calibration_points = []
                break
        
        cv2.destroyWindow(window_name)
        return self.calibration_points

def calculate_transformation(points):
    """Calculate transformation matrix from calibration points"""
    if len(points) != 4:
        return None
        
    # Define standard dartboard coordinates (normalized)
    std_points = np.float32([
        [0.5, 0.0],  # Top (20-1)
        [1.0, 0.5],  # Right (13-6)
        [0.5, 1.0],  # Bottom (11-14)
        [0.0, 0.5]   # Left (3-17)
    ])
    
    points = np.float32(points)
    return cv2.getPerspectiveTransform(points, std_points)