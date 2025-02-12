from camera_calibration import DartboardCalibration
from main_menu import DartGameMenu

def main():
    # First run calibration
    calibration = DartboardCalibration()
    calibration.run()
    
    # If calibration was successful, start main menu
    if calibration.is_calibrated:
        menu = DartGameMenu(calibration.selected_cameras)
        menu.run()

if __name__ == "__main__":
    main()