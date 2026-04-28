#!/usr/bin/env python3
"""
QSync - Professional File Synchronization Tool
Cross-platform file sync application with a modern glass UI.
"""

import sys
import os

# Ensure the src directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from ui.app import QSyncApp


def main():
    app = QSyncApp()
    app.run()


if __name__ == "__main__":
    main()
