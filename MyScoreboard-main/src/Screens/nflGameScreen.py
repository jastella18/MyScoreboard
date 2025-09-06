"""NFL screen rendering for tiny LED matrix.

Provides functions to build per-game frames (score/status + leaders) and
iterate through all current games.
"""
from __future__ import annotations
import time
from typing import Iterable, List
from datetime import datetime
try:
	from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
	ZoneInfo = None  # type: ignore
from ..GameClasses.nflGame import NFLGame
from ..logo_cache import get_processed_logo
from .common import prepare_lines, draw_frame


def game_primary_lines(game: NFLGame) -> List[str]:
	base = [game.score_line(), game.status_line()]
	if game.last_play and game.state == 'in':
		base.append(game.last_play)
	return base


def game_leaders_lines(game: NFLGame) -> List[str]:
	return game.leaders_lines()


def render_game(matrix, game: NFLGame, leaders: bool = False, hold: float = 2.5, show_logos: bool = True):
	canvas = matrix.CreateFrameCanvas()
	width = getattr(canvas, 'width', getattr(canvas, 'GetWidth', lambda: 64)()) if hasattr(canvas, 'width') else 64
	height = getattr(canvas, 'height', getattr(canvas, 'GetHeight', lambda: 32)()) if hasattr(canvas, 'height') else 32

	# Enhanced pre-game layout similar to MLB version
	if show_logos and (game.state or '') == 'pre' and width >= 48 and height >= 24:
		from .common import graphics, FontManager, center_x_width
		font = FontManager.get_font()
		bold_font = FontManager.get_font(bold=True)
		white = graphics.Color(255,255,255)
		MED = 18
		l_med = get_processed_logo('nfl', game.away.abbr, url=getattr(game.away, 'logo', None), size=MED, remove_bg=True)
		r_med = get_processed_logo('nfl', game.home.abbr, url=getattr(game.home, 'logo', None), size=MED, remove_bg=True)
		def blit_med(img, ox, oy=0):
			if img is None: return
			try: has_alpha = img.mode == 'RGBA'
			except Exception: has_alpha = False
			w,h = img.size; pix = img.load()
			for y2 in range(h):
				py = oy + y2
				if py >= height: break
				for x2 in range(w):
					px = ox + x2
					if px < 0 or px >= width: continue
					val = pix[x2,y2]
					if has_alpha and len(val)==4:
						r,g2,b2,a = val
						if a < 90: continue
					else:
						r,g2,b2 = val[:3]
					try: canvas.SetPixel(px, py, int(r), int(g2), int(b2))
					except Exception: pass
		if l_med: blit_med(l_med, 0, 0)
		if r_med: blit_med(r_med, width - r_med.size[0], 0)
		# Records under logos (fit if needed, 4px char width)
		def fit(text: str, max_px: int) -> str:
			if not text: return ''
			char_w = 4
			if len(text)*char_w <= max_px: return text
			return text[: max_px//char_w]
		name_y = min(height - 3, MED + 4)
		if l_med and game.away.record:
			w_logo = l_med.size[0]
			txt = fit(game.away.record, w_logo)
			px = max(0, (w_logo - len(txt)*4)//2)
			graphics.DrawText(canvas, font, px, name_y, white, txt)
		if r_med and game.home.record:
			w_logo = r_med.size[0]
			txt = fit(game.home.record, w_logo)
			start_x = width - w_logo + max(0, (w_logo - len(txt)*4)//2)
			graphics.DrawText(canvas, font, start_x, name_y, white, txt)
		# Time top center (UTC -> Eastern)
		start_iso = getattr(game, 'start_time', None) or game.start_time
		show_time = ''
		if isinstance(start_iso, str) and 'T' in start_iso:
			iso_full = start_iso.strip()
			if iso_full.endswith('Z'):
				iso_full = iso_full[:-1] + '+00:00'
			try:
				dt = datetime.fromisoformat(iso_full)
				if dt.tzinfo is None and ZoneInfo:
					dt = dt.replace(tzinfo=ZoneInfo('UTC'))
				if ZoneInfo:
					local = dt.astimezone(ZoneInfo('America/New_York'))
					show_time = f"{local.hour:02d}:{local.minute:02d}"
				else:
					show_time = iso_full.split('T',1)[1][:5]
			except Exception:
				try:
					show_time = iso_full.split('T',1)[1][:5]
				except Exception:
					show_time = ''
		if not show_time:
			show_time = 'TBD'
		mx_time = center_x_width(show_time, 6)
		graphics.DrawText(canvas, bold_font, mx_time, 9, white, show_time)
		# Venue scroll bottom
		venue = (game.raw.get('venue') or '') or f"{game.away.abbr} @ {game.home.abbr}"
		scroll_text = f"  {venue.upper()}  "
		char_w = 4
		text_px = len(scroll_text)*char_w
		loop_px = text_px + width
		step_delay = 0.08
		frames = loop_px
		for frame in range(frames):
			# (No clear to preserve logos each frame -> redraw for smooth scroll)
			canvas.Clear()
			if l_med: blit_med(l_med, 0, 0)
			if r_med: blit_med(r_med, width - r_med.size[0], 0)
			# Records again
			if l_med and game.away.record:
				w_logo = l_med.size[0]; txt = fit(game.away.record, w_logo); px = max(0, (w_logo - len(txt)*4)//2)
				graphics.DrawText(canvas, font, px, name_y, white, txt)
			if r_med and game.home.record:
				w_logo = r_med.size[0]; txt = fit(game.home.record, w_logo); start_x = width - w_logo + max(0, (w_logo - len(txt)*4)//2)
				graphics.DrawText(canvas, font, start_x, name_y, white, txt)
			graphics.DrawText(canvas, bold_font, mx_time, 9, white, show_time)
			offset = frame % loop_px
			start_x_px = width - offset
			for idx, ch in enumerate(scroll_text):
				cx = start_x_px + idx*char_w
				if -char_w <= cx < width:
					graphics.DrawText(canvas, font, cx, height - 1, white, ch)
			canvas = matrix.SwapOnVSync(canvas)
			time.sleep(step_delay)
		return

	# Default/simple layout (in-progress, post, or no logos)
	lines_raw = game_leaders_lines(game) if leaders else game_primary_lines(game)
	lines = prepare_lines(lines_raw, max_lines=4, max_chars=15)
	draw_frame(canvas, lines)
	canvas = matrix.SwapOnVSync(canvas)
	time.sleep(hold)


def cycle_games(matrix, games: Iterable[NFLGame], *, show_leaders: bool = True, per_game_seconds: float = 5.0, pre_game_seconds: float = 3.0, show_logos: bool = True):
	for g in games:
		is_pre = getattr(g, 'state', '') == 'pre'
		base_hold = pre_game_seconds if is_pre else per_game_seconds
		render_game(matrix, g, leaders=False, hold=base_hold, show_logos=show_logos)
		if show_leaders and not is_pre:
			render_game(matrix, g, leaders=True, hold=base_hold / 2, show_logos=False)


__all__ = ["cycle_games", "render_game"]
