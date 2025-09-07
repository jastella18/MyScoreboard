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

	# Enhanced FINAL (post-game) layout: large partially off-screen logos, side-by-side scores, FINAL under scores, scrolling leaders bottom
	if show_logos and (game.state or '') == 'post' and width >= 48 and height >= 24:
		from .common import graphics, FontManager
		font = FontManager.get_font()
		bold_font = FontManager.get_font(bold=True)
		white = graphics.Color(255,255,255)
		# Large logos (size 32) deliberately drawn partially off screen
		BIG = 32
		l_big = get_processed_logo('nfl', game.away.abbr, url=getattr(game.away, 'logo', None), size=BIG, remove_bg=True)
		r_big = get_processed_logo('nfl', game.home.abbr, url=getattr(game.home, 'logo', None), size=BIG, remove_bg=True)
		def blit_big(img, ox, oy=-2):
			if img is None: return
			try: has_alpha = img.mode == 'RGBA'
			except Exception: has_alpha = False
			w,h = img.size; pix = img.load()
			for y2 in range(h):
				py = oy + y2
				if py < 0 or py >= height: continue
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
		# Draw partially off (left extends -6, right extends beyond width+6)
		if l_big: blit_big(l_big, -6, -2)
		if r_big: blit_big(r_big, width - (r_big.size[0]-6), -2)
		# Scores near each logo (vertical mid-ish ~14)
		away_score_txt = str(game.away.score)
		home_score_txt = str(game.home.score)
		# Left score sits just to right of left visible boundary (x ~ 12)
		graphics.DrawText(canvas, bold_font, 12, 14, white, away_score_txt)
		# Right score sits left of right visible edge (x ~ width-18 depending on digits)
		rsx = width - 18
		if len(home_score_txt) == 1:
			rsx = width - 14
		graphics.DrawText(canvas, bold_font, rsx, 14, white, home_score_txt)
		# Small dash centered between scores (y~14)
		graphics.DrawText(canvas, font, width//2 - 2, 14, white, '-')
		# FINAL label under scores (y ~ 22)
		graphics.DrawText(canvas, font, width//2 - 10, 22, white, 'FINAL')
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
			if l_big: blit_big(l_big, -6, -2)
			if r_big: blit_big(r_big, width - (r_big.size[0]-6), -2)
			graphics.DrawText(canvas, bold_font, 12, 14, white, away_score_txt)
			graphics.DrawText(canvas, bold_font, rsx, 14, white, home_score_txt)
			graphics.DrawText(canvas, font, width//2 - 2, 14, white, '-')
			graphics.DrawText(canvas, font, width//2 - 10, 22, white, 'FINAL')
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
