"""Convenience launcher.

Allows running the scoreboard with ``python run.py`` while keeping
package-safe relative imports inside ``src``.
"""
from src.main import main

if __name__ == "__main__":
    main()
