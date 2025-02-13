# GUI module version
__version__ = '0.1.0'

# Import GUI components
from .setup import CameraSetupGUI
from .scoring import ScoringGUI

# Export belangrijke classes
__all__ = [
    'CameraSetupGUI',
    'ScoringGUI'
]