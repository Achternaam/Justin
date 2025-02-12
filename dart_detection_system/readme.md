# Dart Detection System

An automated dart detection and scoring system using computer vision.

## Requirements

- Python 3.8 or higher
- Three webcams
- A dartboard
- USB ports for camera connections

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/dart_detection_system.git
cd dart_detection_system
```

2. Create a virtual environment (recommended):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python src/main.py
```

2. Follow the camera calibration process:
   - Select your three cameras from the dropdown menus
   - Position the cameras around your dartboard
   - Wait for automatic calibration
   - Proceed to the main menu when calibration is successful

3. Select your game mode and start playing!

## Troubleshooting

1. Camera not detected:
   - Make sure cameras are properly connected
   - Try different USB ports
   - Check camera permissions

2. Calibration issues:
   - Ensure good lighting conditions
   - Position cameras at different angles
   - Make sure dartboard is clearly visible

## License

MIT License - feel free to use and modify as needed.
