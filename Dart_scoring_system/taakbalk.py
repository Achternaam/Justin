import threading
from pystray import Icon, MenuItem, Menu
from PIL import Image
import tkinter as tk

def create_icon(root):
    """Creëer een taakbalkpictogram en stel het in."""
    image = Image.open("logo.png")  # Zorg ervoor dat dit je logo bestand is
    icon = Icon("Genius Dart Software", image, menu=Menu(MenuItem("Exit", exit_action, default=True)))
    
    # Koppel het root venster aan de taakbalkpictogram
    icon.root = root
    icon.run()

def exit_action(icon, item):
    """Sluit de applicatie wanneer op 'Exit' wordt geklikt."""
    icon.stop()
    icon.root.quit()

def start_tray_icon(root):
    """Start het taakbalkpictogram in een aparte thread."""
    tray_thread = threading.Thread(target=create_icon, args=(root,))
    tray_thread.start()
