# src/MathAssistant/ui/vector_window.py

from PyQt6.QtWidgets import QWidget

class VectorWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("بردار و مختصات")
