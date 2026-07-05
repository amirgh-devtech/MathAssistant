# test_cef_lab.py
"""Quick test for CEFPython lab manager."""
import sys
from pathlib import Path

# Add myLab to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.lab_manager import LabManager, Grade, Subject

print("=" * 50)
print("  PhET Lab Manager - CEF Test")
print("=" * 50)

# Create manager
manager = LabManager()
stats = manager.get_stats()
print(f"\nLoaded {stats['total_labs']} labs from {stats.get('build_dir', 'N/A')}")

# Open a lab
print("\nOpening 'Ohm's Law'...")
manager.open_lab("ohms-law", Grade.G8, Subject.PHYS)
print("Lab opened! Close the window to exit, or press Ctrl+C.")

# Keep running
try:
    manager.run()
except KeyboardInterrupt:
    print("\nShutting down...")
    manager.close_all()
    print("Done!")
