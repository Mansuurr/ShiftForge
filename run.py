"""Entry point for PyInstaller and for `python run.py`."""
import sys

from PySide6.QtCore import QSettings

from dragshift import theme

# Palette constants are imported by the lightweight custom widgets, so choose
# the saved mode before importing the rest of the interface.
theme.set_mode(QSettings("ShiftForge", "ShiftForge").value("theme", "dark"))

from dragshift.handoff import try_handoff

if __name__ == "__main__":
    if try_handoff(sys.argv):
        sys.exit(0)
    from dragshift.app import main
    sys.exit(main())
