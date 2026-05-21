# main.py
import sys
from src.MathAssistant.ui.styles import theme, SystemDetector, QtAdapter

# تشخیص Qt
adapter = QtAdapter()
app = adapter.QApplication(sys.argv)
theme.apply_to_application(app)

from src.MathAssistant.ui.main_window import MainWindow
window = MainWindow()
window.show()

# نمایش اطلاعات
info = theme.get_system_info()
print(f"🚀 MathAssistant v4.0 | {info['os']} | {info['qt_version']} | {info['theme']}")

sys.exit(app.exec())
