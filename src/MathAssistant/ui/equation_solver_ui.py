# src/MathAssistant/ui/equation_solver_ui.py

from PyQt6.QtWidgets import QWidget

class EquationSolverWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("حل معادلات")
