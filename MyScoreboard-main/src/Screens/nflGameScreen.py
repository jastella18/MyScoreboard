"""NFL screen rendering for tiny LED matrix.

Enhanced pre-game layout (logos, records, time + DOW, centered odds, venue scroll)
mirrors MLB concept.
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
		# Repositioned layout: time at 6, DOW at 12, odds centered (approx 19), records lower (~25)
		name_y = min(height - 7, 25)
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
		# Time top center (UTC -> Eastern) - dropped additional 3px (now y=13)
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
		graphics.DrawText(canvas, bold_font, mx_time, 13, white, show_time)
		# Day-of-week abbreviation under time
		dow = ''
		try:
			if 'local' in locals():
				dow = local.strftime('%a').upper()
		except Exception:
			pass
		if not dow and isinstance(start_iso, str) and 'T' in start_iso:
			try:
				from datetime import datetime as _dt
				dt2 = _dt.fromisoformat(start_iso.replace('Z','+00:00'))
				dow = dt2.strftime('%a').upper()
			except Exception: dow = ''
		if dow:
			mx_dow = center_x_width(dow, 4)
			# DOW dropped 4px (now y=16)
			graphics.DrawText(canvas, font, mx_dow, 16, white, dow)
		# Odds centered (compose concise odds line) - shifted down 5px (y=24)
		odds = game.raw.get('odds') or {}
		odds_line = ''
		if isinstance(odds, dict):
			details = odds.get('details')  # e.g. "NE -2.5"
			ou = odds.get('overUnder')
			if details and ou:
				odds_line = f"{details} O/U{ou}"
			elif details:
				odds_line = details
			elif ou:
				odds_line = f"O/U {ou}"
		# Fit odds line inside width (4px per char)
		max_chars = width // 4
		if len(odds_line) > max_chars:
			odds_line = odds_line[:max_chars]
		if odds_line:
			mx_odds = (width - len(odds_line)*4)//2
			graphics.DrawText(canvas, font, mx_odds, 24, white, odds_line)
		# Venue scroll bottom
		venue = (game.raw.get('venue') or '') or f"{game.away.abbr} @ {game.home.abbr}"
		scroll_text = f"  {venue.upper()}  "
		char_w = 4
		text_px = len(scroll_text)*char_w
		loop_px = text_px + width
		# Faster scroll for leaders (was 0.08)
		step_delay = 0.05
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
			# Time & DOW (time y=13, DOW y=16)
			graphics.DrawText(canvas, bold_font, mx_time, 9, white, show_time)
			if dow:
				graphics.DrawText(canvas, font, mx_dow, 15, white, dow)
			if odds_line:
				graphics.DrawText(canvas, font, mx_odds, 24, white, odds_line)
			offset = frame % loop_px
			start_x_px = width - offset
			for idx, ch in enumerate(scroll_text):
				cx = start_x_px + idx*char_w
				if -char_w <= cx < width:
					graphics.DrawText(canvas, font, cx, height - 1, white, ch)
			canvas = matrix.SwapOnVSync(canvas)
			time.sleep(step_delay)
		return

	# FINAL layout (post-game): small logos top corners, centered score, FINAL label, scrolling leaders bottom
	if show_logos and (game.state or '') == 'post' and width >= 48 and height >= 24:
		from .common import graphics, FontManager, center_x_width
		font = FontManager.get_font()
		bold_font = FontManager.get_font(bold=True)
		white = graphics.Color(255,255,255)
		SM = 14
		l_sm = get_processed_logo('nfl', game.away.abbr, url=getattr(game.away, 'logo', None), size=SM, remove_bg=True)
		r_sm = get_processed_logo('nfl', game.home.abbr, url=getattr(game.home, 'logo', None), size=SM, remove_bg=True)
		def blit_sm(img, ox, oy=0):
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
		if l_sm: blit_sm(l_sm, 0, 0)
		if r_sm: blit_sm(r_sm, width - r_sm.size[0], 0)
		# Centered numeric score only (no team abbreviations) mid-screen (y ~ 16)
		score_line = f"{game.away.score}-{game.home.score}"
		cx_score = center_x_width(score_line, 6)
		score_y = height // 2
		graphics.DrawText(canvas, bold_font, cx_score, score_y, white, score_line)
		# FINAL just below score
		final_label = 'FINAL'
		# Dynamically center FINAL (font assumed 4px glyph width)
		cx_final = center_x_width(final_label, 4)
		graphics.DrawText(canvas, font, cx_final, min(height - 9, score_y + 6), white, final_label)
		# Leaders scroll bottom
		leaders = getattr(game, 'leaders', {}) or {}
		def extract_yards(display: str) -> str:
			if not display: return ''
			import re
			m = re.search(r"(\d+)\s*YDS", display.upper())
			if m: return m.group(1)
			m2 = re.search(r"(\d+)", display)
			return m2.group(1) if m2 else ''
		parts = []
		if leaders.get('passing'):
			ld = leaders['passing']; yr = extract_yards(ld.get('display') or '')
			if ld.get('athlete') and yr: parts.append(f"P: {ld['athlete']} {yr} yds")
		if leaders.get('rushing'):
			ld = leaders['rushing']; yr = extract_yards(ld.get('display') or '')
			if ld.get('athlete') and yr: parts.append(f"RSH: {ld['athlete']} {yr} yds")
		if leaders.get('receiving'):
			ld = leaders['receiving']; yr = extract_yards(ld.get('display') or '')
			if ld.get('athlete') and yr: parts.append(f"REC: {ld['athlete']} {yr} yds")
		if not parts:
			parts.append('NO LEADERS DATA')
		scroll_text = '  '.join(parts).upper()
		scroll_text = f"  {scroll_text}  "
		char_w = 4
		loop_px = len(scroll_text)*char_w + width
		step_delay = 0.08
		for frame in range(loop_px):
			canvas.Clear()
			if l_sm: blit_sm(l_sm, 0, 0)
			if r_sm: blit_sm(r_sm, width - r_sm.size[0], 0)
			graphics.DrawText(canvas, bold_font, cx_score, score_y, white, score_line)
			graphics.DrawText(canvas, font, cx_final, min(height - 9, score_y + 6), white, final_label)
			offset = frame % (len(scroll_text)*char_w + width)
			start = width - offset
			for idx,ch in enumerate(scroll_text):
				cx = start + idx*char_w
				if -char_w <= cx < width:
					graphics.DrawText(canvas, font, cx, height-1, white, ch)
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
