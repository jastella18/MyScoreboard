"""Entry point for multi-sport LED scoreboard.

Rotates through NFL, MLB, and Premier League games using screen modules and
the scheduling layer with caching.

Falls back to console output when rgbmatrix library isn't available (e.g. on
Windows for development).
"""
import os
import time
from typing import List


try:  # pragma: no cover - hardware import
    from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions  # type: ignore
except Exception:  # Library not available -> provide light stubs
    class _Color:
        def __init__(self, r, g, b):
            self.r, self.g, self.b = r, g, b

    class _Font:
        def LoadFont(self, path):
            pass

    class _Canvas:
        def __init__(self):
            self.text_lines: List[str] = []
        def SetImage(self, image, x, y):
            pass
        def Clear(self):
            self.text_lines.clear()
    class _Matrix:
        def __init__(self, *_, **__):
            self._c = _Canvas()
        def CreateFrameCanvas(self):
            return self._c
        def Clear(self):
            self._c.Clear()
        def SwapOnVSync(self, canvas):
            if getattr(canvas, 'text_lines', None):
                print("\n".join(canvas.text_lines))
            return canvas
    class graphics:  # type: ignore
        Font = _Font
        Color = _Color
        @staticmethod
        def DrawText(canvas, font, x, y, color, text):  # noqa: D401
            # Store for console display
            if hasattr(canvas, 'text_lines'):
                canvas.text_lines.append(text)
            return x + len(text) * 4
    class RGBMatrixOptions:  # type: ignore
        pass
    class RGBMatrix:  # type: ignore
        def __init__(self, *_, **__):
            pass
        def CreateFrameCanvas(self):
            return _Canvas()
        def SwapOnVSync(self, canvas):
            if getattr(canvas, 'text_lines', None):
                print("\n".join(canvas.text_lines))
            return canvas
        def Clear(self):
            pass


"""NOTE ON IMPORTS

All intra-package imports use explicit relative form (``from .scheduling`` etc.)
so the project must be executed as a module:

    python -m src.main

Running ``python src/main.py`` will no longer work because relative imports
require package context. A convenience ``run.py`` wrapper is added at repo root.
"""

from .scheduling import rotation_iterator
from .Screens.nflGameScreen import cycle_games as cycle_nfl_games
from .Screens.mlbGameScreen import cycle_games as cycle_mlb_games
from .Screens.premGameScreen import cycle_games as cycle_prem_games
from .Screens.yardsLeaders import cycle_leaders as cycle_nfl_leaders
from .Screens.battingLeaders import cycle_batting as cycle_mlb_batting
from .config_loader import load_config

CONFIG_RELOAD_INTERVAL = 30  # seconds


def run_rotation(matrix):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    last_cfg = load_config(project_root)
    last_reload = time.time()
    rotation = tuple(last_cfg.get("rotation", ("nfl", "mlb", "prem")))
    for games in rotation_iterator(rotation=rotation):
        # Periodically reload config to allow mode switching by editing file
        if time.time() - last_reload > CONFIG_RELOAD_INTERVAL:
            try:
                new_cfg = load_config(project_root)
                last_cfg = new_cfg
                rotation = tuple(new_cfg.get("rotation", rotation))
                print("Config reloaded")
            except Exception as exc:
                print(f"Config reload failed: {exc}")
            finally:
                last_reload = time.time()

        if not games:
            continue
        sport = games[0].sport if games else "nfl"
        try:
            if sport == "nfl":
                nfl_cfg = last_cfg.get("nfl", {})
                per = float(nfl_cfg.get("per_game_seconds", 6))
                cycle_nfl_games(matrix, games, show_leaders=True, per_game_seconds=per)
                if nfl_cfg.get("show_leaders", True):
                    cycle_nfl_leaders(matrix, games, mode=nfl_cfg.get("leader_mode", "all"), per_game_seconds=per)
            elif sport == "mlb":
                mlb_cfg = last_cfg.get("mlb", {})
                per = float(mlb_cfg.get("per_game_seconds", 6))
                cycle_mlb_games(matrix, games, show_leaders=True, per_game_seconds=per)
                if mlb_cfg.get("show_batting", True):
                    cycle_mlb_batting(matrix, games, per_game_seconds=per / 2)
            elif sport == "prem":
                prem_cfg = last_cfg.get("prem", {})
                per = float(prem_cfg.get("per_game_seconds", 5))
                cycle_prem_games(matrix, games, show_leaders=prem_cfg.get("show_leaders", True), per_game_seconds=per)
        except Exception as exc:
            print(f"Display error [{sport}]: {exc}")
            time.sleep(1)


def main():
    # Configure RGB Matrix (safe defaults; ignore if stub implementation)
    options = RGBMatrixOptions()
    # These attributes may not exist in stub, so set conditionally
    for attr, val in {"rows": 32, "cols": 64, "hardware_mapping": "adafruit-hat", "chain_length": 1}.items():
        try:
            setattr(options, attr, val)
        except Exception:
            pass
    try:
        matrix = RGBMatrix(options=options)
    except Exception:
        matrix = RGBMatrix()
    try:
        run_rotation(matrix)
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    main()