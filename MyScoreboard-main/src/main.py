"""Entry point for multi-sport LED scoreboard.

Rotates through NFL, MLB, and Premier League games using screen modules and
the scheduling layer with caching.

Falls back to console output when rgbmatrix library isn't available (e.g. on
Windows for development).
"""
import os
import time
import argparse
from typing import List


USING_STUB = False
try:  # pragma: no cover - hardware import
    from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions  # type: ignore
except Exception:  # Library not available -> provide light stubs
    USING_STUB = True
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


def run_rotation(matrix, debug: bool = False):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    last_cfg = load_config(project_root)
    last_reload = time.time()
    rotation = tuple(last_cfg.get("rotation", ("nfl", "mlb", "prem")))
    last_empty_notice = 0.0
    EMPTY_INTERVAL = 1.0  # seconds between placeholder refreshes
    for games in rotation_iterator(rotation=rotation, dynamic_reorder=True):
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

        if debug:
            print(f"[DEBUG] Rotation sport={rotation[0] if rotation else '?'} current_sport_games={len(games)}")
        if not games:
            now = time.time()
            if now - last_empty_notice > EMPTY_INTERVAL:
                if debug:
                    print("[DEBUG] No games fetched for sport; drawing placeholder frame")
                _show_placeholder(matrix, f"{rotation[0].upper() if rotation else 'SPORT'}", "NO DATA", "FETCHING...")
                last_empty_notice = now
            continue
        sport = games[0].sport if games else "nfl"
        try:
            if sport == "nfl":
                nfl_cfg = last_cfg.get("nfl", {})
                per = float(nfl_cfg.get("per_game_seconds", 6))
                per *= float(last_cfg.get("duration_multiplier", 1.0))
                cycle_nfl_games(matrix, games, show_leaders=True, per_game_seconds=per)
                if nfl_cfg.get("show_leaders", True):
                    cycle_nfl_leaders(matrix, games, mode=nfl_cfg.get("leader_mode", "all"), per_game_seconds=per)
            elif sport == "mlb":
                mlb_cfg = last_cfg.get("mlb", {})
                per = float(mlb_cfg.get("per_game_seconds", 6))
                per *= float(last_cfg.get("duration_multiplier", 1.0))
                show_logos = bool(mlb_cfg.get("show_logos", True))
                cycle_mlb_games(matrix, games, show_leaders=True, per_game_seconds=per, show_logos=show_logos)
                if mlb_cfg.get("show_batting", True):
                    cycle_mlb_batting(matrix, games, per_game_seconds=per / 2)
            elif sport == "prem":
                prem_cfg = last_cfg.get("prem", {})
                per = float(prem_cfg.get("per_game_seconds", 5))
                per *= float(last_cfg.get("duration_multiplier", 1.0))
                cycle_prem_games(matrix, games, show_leaders=prem_cfg.get("show_leaders", True), per_game_seconds=per)
            if debug:
                print(f"[DEBUG] Displayed {len(games)} {sport} games")
        except Exception as exc:
            print(f"Display error [{sport}]: {exc}")
            time.sleep(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Multi-sport LED scoreboard")
    parser.add_argument("--rows", type=int, default=int(os.getenv("MATRIX_ROWS", 32)))
    parser.add_argument("--cols", type=int, default=int(os.getenv("MATRIX_COLS", 64)))
    parser.add_argument("--chain", type=int, default=int(os.getenv("MATRIX_CHAIN", 1)))
    parser.add_argument("--parallel", type=int, default=int(os.getenv("MATRIX_PARALLEL", 1)))
    parser.add_argument("--hardware-mapping", default=os.getenv("MATRIX_HW", "adafruit-hat"))
    parser.add_argument("--brightness", type=int, default=int(os.getenv("MATRIX_BRIGHTNESS", 80)))
    parser.add_argument("--gpio-slowdown", type=int, default=int(os.getenv("MATRIX_GPIO_SLOWDOWN", 2)))
    parser.add_argument("--no-led", action="store_true", help="Force stub mode even if library present (debug)")
    parser.add_argument("--test-pattern", action="store_true", help="Show a test pattern then exit")
    parser.add_argument("--debug", action="store_true", help="Verbose debug logging")
    parser.add_argument("--mock", action="store_true", help="Use static mock dataset (no network calls)")
    return parser.parse_args()


def build_matrix(args):
    if USING_STUB or args.no_led:
        if USING_STUB and not args.no_led:
            print("[INFO] rgbmatrix lib not found – using console stub (no LED output).")
        else:
            print("[INFO] Forced no-led mode – using console stub.")
        return RGBMatrix()
    opts = RGBMatrixOptions()
    # Defensive attribute setting
    for attr, val in {
        "rows": args.rows,
        "cols": args.cols,
        "chain_length": args.chain,
        "parallel": args.parallel,
        "hardware_mapping": args.hardware_mapping,
        "brightness": max(1, min(100, args.brightness)),
        "gpio_slowdown": args.gpio_slowdown,
    }.items():
        try:
            setattr(opts, attr, val)
        except Exception:
            pass
    try:
        matrix = RGBMatrix(options=opts)
        print(f"[INFO] RGBMatrix init OK {args.cols}x{args.rows} chain={args.chain} parallel={args.parallel} brightness={args.brightness}")
    except Exception as exc:
        print(f"[WARN] RGBMatrix init failed ({exc}); falling back to stub.")
        matrix = RGBMatrix()
    return matrix


def main():
    args = parse_args()
    matrix = build_matrix(args)
    if USING_STUB and not args.no_led:
        print("[HINT] Install hzeller/rpi-rgb-led-matrix on the Pi for real LED output.")
    if args.test_pattern:
        _show_test_pattern(matrix)
        return
    if args.mock:
        try:
            from . import scheduling
            from .mock_data import mock_events
            scheduling.enable_mock_mode(mock_events)
            print("[INFO] Mock mode enabled (static sample events for nfl/mlb/prem).")
        except Exception as exc:
            print(f"[WARN] Failed to initialize mock mode: {exc}")
    print("[INFO] Starting rotation loop. Press Ctrl+C to exit.")
    try:
        run_rotation(matrix, debug=args.debug)
    except KeyboardInterrupt:
        print("Exiting...")


def _show_placeholder(matrix, *lines: str):
    try:
        from .Screens.common import draw_frame
    except Exception:
        return
    canvas = matrix.CreateFrameCanvas()
    draw_frame(canvas, list(lines)[:4])
    matrix.SwapOnVSync(canvas)


def _show_test_pattern(matrix):
    try:
        from rgbmatrix import graphics  # type: ignore
    except Exception:
        pass
    canvas = matrix.CreateFrameCanvas()
    # Attempt colored gradient if SetPixel exists
    for x in range(64):
        for y in range(32):
            try:
                canvas.SetPixel(x, y, (x*4)%256, (y*8)%256, ((x+y)*2)%256)  # type: ignore[attr-defined]
            except Exception:
                break
    from .Screens.common import draw_frame
    draw_frame(canvas, ["TEST", "PATTERN", "OK"], center=True)
    matrix.SwapOnVSync(canvas)
    print("[INFO] Test pattern shown.")

if __name__ == "__main__":
    main()