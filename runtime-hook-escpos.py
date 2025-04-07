# runtime-hook-escpos.py
import os
import sys

# Configurar rutas para escpos
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
os.environ["ESCPOS_CAPABILITIES_FILE"] = os.path.join(base_path, 'escpos', 'capabilities.json')