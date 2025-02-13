# Version information
__version__ = '0.1.0'

# Import belangrijke modules
from .camera import CameraManager, Camera
from .detector import DartboardDetector
from .scorer import ScoreCalculator

# Stel de logger in
import logging
import os

def setup_logging():
    """Initialize logging voor de applicatie"""
    logger = logging.getLogger('dart_scorer')
    logger.setLevel(logging.DEBUG)

    # Maak logs directory als die niet bestaat
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # File handler
    fh = logging.FileHandler('logs/dart_scorer.log')
    fh.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Add handlers
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

# Initialize logger
logger = setup_logging()

# Exporteer belangrijke classes en functies
__all__ = [
    'CameraManager',
    'Camera',
    'DartboardDetector',
    'ScoreCalculator',
    'logger'
]