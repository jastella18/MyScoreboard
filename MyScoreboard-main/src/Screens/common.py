"""Shared tiny LED matrix screen rendering helpers.

Designed for 64x32 (4mm pitch) panels using 4x6 font.
Provides graceful fallback when rgbmatrix lib not present (prints frames).
"""
from __future__ import annotations
import os
from typing import List, Iterable

try:  # real library
    from rgbmatrix import graphics  # type: ignore
except Exception:  # fallback stubs
    class _Color:
        def __init__(self, r, g, b):
            self.r, self.g, self.b = r, g, b
    class _Font:
        def LoadFont(self, path):
            pass
    class graphics:  # type: ignore
        Font = _Font
        Color = _Color
        @staticmethod
        def DrawText(canvas, font, x, y, color, text):
            if hasattr(canvas, 'lines'):
                canvas.lines.append((x, y, text))
            return x + len(text) * 4

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FONTS_DIR = os.path.join(PROJECT_ROOT, 'rpi-rgb-led-matrix', 'rpi-rgb-led-matrix', 'fonts')
DEFAULT_FONT_PATH = os.path.join(FONTS_DIR, '4x6.bdf')

class FontManager:
    _font = None
    @classmethod
    def get_font(cls):
        if cls._font is None:
            f = graphics.Font()
            try:
                f.LoadFont(DEFAULT_FONT_PATH)
            except Exception:
                pass
            cls._font = f
        return cls._font

def wrap_text(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = []
    cur_len = 0
    for w in words:
        if cur and cur_len + 1 + len(w) > max_chars:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            if not cur:
                cur = [w]
                cur_len = len(w)
            else:
                cur.append(w)
                cur_len += 1 + len(w)
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]

def truncate(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 1] + '…'

def center_x(text: str, panel_width: int = 64, char_width: int = 4) -> int:
    text_w = len(text) * char_width
    return max(0, (panel_width - text_w) // 2)

def prepare_lines(raw_lines: Iterable[str], max_lines: int = 5, max_chars: int = 15) -> List[str]:
    out: List[str] = []
    for line in raw_lines:
        if not line:
            continue
        for wrapped in wrap_text(line, max_chars):
            if len(out) >= max_lines:
                return out
            out.append(truncate(wrapped, max_chars))
    return out

def draw_frame(canvas, lines: List[str], *, start_y: int = 6, line_height: int = 8, center: bool = True, color=None):
    font = FontManager.get_font()
    color = color or graphics.Color(255, 255, 255)
    y = start_y
    for line in lines:
        x = center_x(line) if center else 0
        graphics.DrawText(canvas, font, x, y, color, line)
        y += line_height

__all__ = [
    'wrap_text', 'truncate', 'center_x', 'prepare_lines', 'draw_frame', 'FontManager'
]
