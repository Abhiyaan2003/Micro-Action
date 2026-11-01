"""Run the editor without installing the keyboard hook or starting engines."""
from __future__ import annotations

import os
import sys
import tempfile

from PyQt6.QtWidgets import QApplication

from config import Config
from ui.main_window import GlassNumpadEditor


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Micro Action Preview")
    preview_config = os.path.join(tempfile.gettempdir(), "micro-action-preview.json")
    window = GlassNumpadEditor(Config(preview_config))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
