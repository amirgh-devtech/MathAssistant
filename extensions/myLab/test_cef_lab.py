# test_cef_lab.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.lab_manager import LabManager

print("=" * 50)
print("  PhET Lab Manager - Test")
print("=" * 50)

manager = LabManager()

print("\nOpening Lab Explorer...")
manager.run()

print("Done!")
