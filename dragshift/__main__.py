import sys

from PySide6.QtCore import QSettings

from dragshift import theme

theme.set_mode(QSettings("ShiftForge", "ShiftForge").value("theme", "dark"))

from dragshift.handoff import try_handoff

if try_handoff(sys.argv):
    sys.exit(0)

from dragshift.app import main  # noqa: E402

sys.exit(main())
