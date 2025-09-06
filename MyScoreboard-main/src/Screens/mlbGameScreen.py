"""MLB screen rendering for 64x32 panel."""
from __future__ import annotations
import time
from typing import Iterable, List
from datetime import datetime
try:
	from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
	ZoneInfo = None  # type: ignore
from ..GameClasses.mlbGame import MLBGame
from ..logo_cache import get_logo, get_logo_from_url, get_processed_logo
from .common import prepare_lines, draw_frame


def game_primary_lines(game: MLBGame) -> List[str]:
	base = [game.score_line(), game.status_line()]
	if game.last_play and game.state == 'in':
		base.append(game.last_play)
	return base


def game_leaders_lines(game: MLBGame) -> List[str]:
	return game.leaders_lines()



def _format_local_start_time(start_iso: str | None, target_tz: str = 'America/New_York') -> str:
	"""Convert an ISO 8601 UTC (or naive) time to HH:MM in target tz (default Eastern).
	Assumes UTC when naive. Returns '' on failure."""
	if not start_iso or 'T' not in start_iso:
		return ''
	iso = start_iso.strip()
	if iso.endswith('Z'):
		iso = iso[:-1] + '+00:00'
	try:
		dt = datetime.fromisoformat(iso)
		if dt.tzinfo is None and ZoneInfo:
			dt = dt.replace(tzinfo=ZoneInfo('UTC'))
		if ZoneInfo:
			local = dt.astimezone(ZoneInfo(target_tz))
			return f"{local.hour:02d}:{local.minute:02d}"
		return iso.split('T',1)[1][:5]
	except Exception:
		try:
			return iso.split('T',1)[1][:5]
		except Exception:
			return ''

def render_game(matrix, game: MLBGame, leaders: bool = False, hold: float = 2.5, show_logos: bool = True, big_layout: bool = True, gamma_correct: bool = False):
	canvas = matrix.CreateFrameCanvas()
	# Detect actual canvas size (fallback to assumed 64x32)
	width = getattr(canvas, 'width', getattr(canvas, 'GetWidth', lambda: 64)()) if hasattr(canvas, 'width') else 64
	height = getattr(canvas, 'height', getattr(canvas, 'GetHeight', lambda: 32)()) if hasattr(canvas, 'height') else 32

	# Shared gamma correction helper (used for logos AND text)
	if gamma_correct:
		if not hasattr(render_game, "_gamma_lut"):
			g = 2.2
			render_game._gamma_lut = [int(((i / 255.0) ** g) * 255 + 0.5) for i in range(256)]
		LUT = render_game._gamma_lut  # type: ignore[attr-defined]
		def _gc(v: int) -> int: return LUT[v]
	else:
		def _gc(v: int) -> int: return v

	def gcolor(r: int, g: int, b: int):
		from ..Screens.common import graphics  # local import to avoid circular top-level
		return graphics.Color(_gc(r), _gc(g), _gc(b))

	# Ultra-small display handling (e.g., ~12x6). Provide compressed single-line output.
	if width <= 20 or height <= 8:
		from ..Screens.common import graphics, FontManager
		font = FontManager.get_font()
		white = gcolor(255,255,255)
		# Build compact token: A1-H2 (first letters) plus maybe inning if room
		a_chr = game.away.abbr[:1]
		h_chr = game.home.abbr[:1]
		token = f"{a_chr}{game.away.score}-{h_chr}{game.home.score}"[:width // 4]  # crude trim
		# Try to append inning indicator if space (e.g., '5')
		inn = str(game.period) if game.period else ''
		if inn and len(token)*4 + 4 <= width:
			token += inn
		# Center horizontally
		x = max(0, (width - len(token)*4)//2)
		y = min(height - 1, height - 1)  # Baseline at bottom
		graphics.DrawText(canvas, font, x, y, white, token)
		matrix.SwapOnVSync(canvas)
		time.sleep(hold)
		return

	if show_logos and big_layout and width >= 48 and height >= 24:
		# Determine state early so we can choose layout without drawing large logos twice
		state = game.state or ""
		# Pre-game: dedicated medium-logo layout (skip big logos)
		if state == 'pre':
			from ..Screens.common import graphics, FontManager, center_x_width
			font = FontManager.get_font()
			white = gcolor(255,255,255)
			MED = 18
			l_med = get_processed_logo('mlb', game.away.abbr, url=game.away.logo, size=MED, remove_bg=True)
			r_med = get_processed_logo('mlb', game.home.abbr, url=game.home.logo, size=MED, remove_bg=True)
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
						try: canvas.SetPixel(px, py, _gc(int(r)), _gc(int(g2)), _gc(int(b2)))
						except Exception: pass
			if l_med: blit_med(l_med, 0, 0)
			if r_med: blit_med(r_med, width - r_med.size[0], 0)
			def last_name(obj, role: str):
				"""Extract probable pitcher's last name from various possible structures.
				Supports attributes or dict keys: probable_pitcher, starting_pitcher, pitcher, probables(list)."""
				# 1. Direct attributes/dict entries
				candidates = []
				for attr in ("probable_pitcher", "starting_pitcher", "pitcher"):
					val = getattr(obj, attr, None)
					if not val and isinstance(obj, dict):
						val = obj.get(attr)
					if val:
						candidates.append(val)
				# 2. Probables list (ESPn style): obj.probables -> list of dicts with athlete.fullName / displayName
				prob_list = getattr(obj, 'probables', None)
				if not prob_list and isinstance(obj, dict):
					prob_list = obj.get('probables')
				if isinstance(prob_list, (list, tuple)) and prob_list:
					for item in prob_list:
						if not isinstance(item, dict):
							continue
						ath = item.get('athlete') or {}
						if isinstance(ath, dict):
							full = ath.get('fullName') or ath.get('displayName') or ath.get('shortName')
							if full:
								candidates.append(full)
						else:
							# maybe item itself has displayName
							dsp = item.get('displayName') or item.get('fullName')
							if dsp:
								candidates.append(dsp)
				# 2b. Fallback: search raw competitors structure if still empty
				if not candidates:
					raw = getattr(game, 'raw', {}) or {}
					comps = []
					# ESPN style sometimes under competitions[0].competitors
					if isinstance(raw, dict):
						if 'competitors' in raw:
							comps = raw.get('competitors') or []
						elif 'competitions' in raw:
							try:
								comps = (raw['competitions'][0] or {}).get('competitors', [])
							except Exception:
								comps = []
					if isinstance(comps, list):
						for c in comps:
							if not isinstance(c, dict):
								continue
							if c.get('homeAway') != role:
								continue
							# look in competitor probables
							plist = c.get('probables') or []
							for item in plist:
								if not isinstance(item, dict):
									continue
								ath = item.get('athlete') or {}
								if isinstance(ath, dict):
									full = ath.get('fullName') or ath.get('displayName') or ath.get('shortName')
									if full:
										candidates.append(full)
								else:
									# direct item names
									full = item.get('displayName') or item.get('fullName')
									if full:
										candidates.append(full)
				# 3. Reduce candidates to last name
				for name in candidates:
					if not name:
						continue
					# Nested dict candidate
					if isinstance(name, dict):
						for k in ("last_name","lname","name_last","last"):
							if k in name and name[k]:
								ln = str(name[k]).split()[-1]
								return ln[:8].upper()
						for k in ("display","full","name"):
							if k in name and name[k]:
								ln = str(name[k]).split()[-1]
								return ln[:8].upper()
					elif isinstance(name, str):
						parts = name.strip().split()
						if parts:
							return parts[-1][:8].upper()
				return ""
			away_p = last_name(game.away, 'away'); home_p = last_name(game.home, 'home')
			if l_med and away_p:
				w_logo = l_med.size[0]; px = max(0, (w_logo - len(away_p)*4)//2)
				graphics.DrawText(canvas, font, px, MED + 1, white, away_p)
			if r_med and home_p:
				w_logo = r_med.size[0]; start_x = width - w_logo + max(0, (w_logo - len(home_p)*4)//2)
				graphics.DrawText(canvas, font, start_x, MED + 1, white, home_p)
			bold_font = FontManager.get_font(bold=True)
			start_iso = getattr(game, 'start_time', None) or game.start_time
			show_time = _format_local_start_time(start_iso)
			if not show_time: show_time = 'TBD'
			mx_time = center_x_width(show_time, 6)
			graphics.DrawText(canvas, bold_font, mx_time, 30, white, show_time)
			canvas = matrix.SwapOnVSync(canvas); time.sleep(hold); return

		# Big side logo layout (non pre-game states)
		BIG = 26  # nominal target height
		left_img = get_processed_logo('mlb', game.away.abbr, url=game.away.logo, size=BIG, remove_bg=True)
		right_img = get_processed_logo('mlb', game.home.abbr, url=game.home.logo, size=BIG, remove_bg=True)
		# Draw with partial off-screen effect via per-pixel plot
		def blit(img, ox):
			if img is None:
				return
			try:
				has_alpha = img.mode == 'RGBA'
			except Exception:
				has_alpha = False
			w, h = img.size
			pix = img.load()
			for y in range(h):
				py = y + 4  # push logos down to free top rows for text
				if py >= 32:
					break
				for x in range(w):
					px = x + ox
					if px < 0 or px >= 64:
						continue
					val = pix[x, y]
					if has_alpha and len(val) == 4:
						r, g, b, a = val
						if a < 90:  # skip mostly transparent feather pixels
							continue
					else:
						r, g, b = val[:3]
					try:
						canvas.SetPixel(px, py, _gc(int(r)), _gc(int(g)), _gc(int(b)))  # type: ignore[attr-defined]
					except Exception:
						pass
		# Left & right logos (slightly shifted)
		blit(left_img, -6)
		if right_img:
			blit(right_img, 64 - (BIG - 6))
		from ..Screens.common import graphics, FontManager, center_x, center_x_width, draw_text_small_bold
		font = FontManager.get_font()  # base tiny font
		bold_font = FontManager.get_font(bold=True)  # taller real bold for score
		white = gcolor(255,255,255)
		state = game.state or ""
		# Pre-game: show only logos + @time
		if state == 'pre':
			# New pre-game layout: medium logos top corners, probable pitcher last names under logos,
			# bold start time bottom center.
			MED = 18
			# Re-fetch smaller logos for this layout to reduce vertical footprint
			l_med = get_processed_logo('mlb', game.away.abbr, url=game.away.logo, size=MED, remove_bg=True)
			r_med = get_processed_logo('mlb', game.home.abbr, url=game.home.logo, size=MED, remove_bg=True)
			def blit_med(img, ox, oy=0):
				if img is None:
					return
				try:
					has_alpha = img.mode == 'RGBA'
				except Exception:
					has_alpha = False
				w,h = img.size
				pix = img.load()
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
						try:
							canvas.SetPixel(px, py, _gc(int(r)), _gc(int(g2)), _gc(int(b2)))
						except Exception:
							pass
		# Position logos: left at x=0, right at width - logo_w
			if l_med:
				blit_med(l_med, 0, 0)
			if r_med:
				blit_med(r_med, width - r_med.size[0], 0)
			# Probable pitcher last names (fallback if not available)
			def last_name(obj, role: str):
				candidates = []
				for attr in ("probable_pitcher", "starting_pitcher", "pitcher"):
					val = getattr(obj, attr, None)
					if not val and isinstance(obj, dict):
						val = obj.get(attr)
					if val:
						candidates.append(val)
				prob_list = getattr(obj, 'probables', None)
				if not prob_list and isinstance(obj, dict):
					prob_list = obj.get('probables')
				if isinstance(prob_list, (list, tuple)) and prob_list:
					for item in prob_list:
						if not isinstance(item, dict):
							continue
						ath = item.get('athlete') or {}
						if isinstance(ath, dict):
							full = ath.get('fullName') or ath.get('displayName') or ath.get('shortName')
							if full:
								candidates.append(full)
						else:
							dsp = item.get('displayName') or item.get('fullName')
							if dsp:
								candidates.append(dsp)
				if not candidates:
					raw = getattr(game, 'raw', {}) or {}
					comps = []
					if isinstance(raw, dict):
						if 'competitors' in raw:
							comps = raw.get('competitors') or []
						elif 'competitions' in raw:
							try:
								comps = (raw['competitions'][0] or {}).get('competitors', [])
							except Exception:
								comps = []
					if isinstance(comps, list):
						for c in comps:
							if not isinstance(c, dict): continue
							if c.get('homeAway') != role: continue
							plist = c.get('probables') or []
							for item in plist:
								if not isinstance(item, dict): continue
								ath = item.get('athlete') or {}
								if isinstance(ath, dict):
									full = ath.get('fullName') or ath.get('displayName') or ath.get('shortName')
									if full: candidates.append(full)
								else:
									full = item.get('displayName') or item.get('fullName')
									if full: candidates.append(full)
				for name in candidates:
					if not name: continue
					if isinstance(name, dict):
						for k in ("last_name","lname","name_last","last"):
							if k in name and name[k]:
								ln = str(name[k]).split()[-1]
								return ln[:8].upper()
						for k in ("display","full","name"):
							if k in name and name[k]:
								ln = str(name[k]).split()[-1]
								return ln[:8].upper()
					elif isinstance(name, str):
						parts = name.strip().split()
						if parts:
							return parts[-1][:8].upper()
				return ""
			away_p = last_name(game.away, 'away')
			home_p = last_name(game.home, 'home')
			# Font metrics: tiny font char width 4 -> center under each logo width
			if l_med and away_p:
				w_logo = l_med.size[0]
				px = max(0, (w_logo - len(away_p)*4)//2)
				graphics.DrawText(canvas, font, px, MED + 1, white, away_p)
			if r_med and home_p:
				w_logo = r_med.size[0]
				start_x = width - w_logo + max(0, (w_logo - len(home_p)*4)//2)
				graphics.DrawText(canvas, font, start_x, MED + 1, white, home_p)
			# Time bottom center (bold) baseline y=30 (keeps a 1px margin at bottom for readability)
			bold_font = FontManager.get_font(bold=True)
			start_iso = getattr(game, 'start_time', None) or game.start_time
			show_time = _format_local_start_time(start_iso) or 'TBD'
			# Center bold time using 6px width assumption
			mx_time = center_x_width(show_time, 6)
			graphics.DrawText(canvas, bold_font, mx_time, 30, white, show_time)
			canvas = matrix.SwapOnVSync(canvas)
			time.sleep(hold)
			return
		# Final: logos + score + FINAL
		if state == 'post':
			score_combo = f"{game.away.score}-{game.home.score}"[:9]
			mxs = center_x_width(score_combo, 6)
			# Bold score baseline y=13 (keeps full 13px glyph visible: rows 1..13)
			graphics.DrawText(canvas, bold_font, mxs, 13, white, score_combo)
			final_txt = "FINAL"
			mxf = center_x_width(final_txt, 6)
			# FINAL at bottom baseline (31)
			graphics.DrawText(canvas, bold_font, mxf, height - 1, white, final_txt)
			canvas = matrix.SwapOnVSync(canvas)
			time.sleep(hold)
			return
		# In-progress layout (robust inning half extraction + reliable arrow)
		# 1. Determine inning + half robustly using processed fields
		display_inning = (game.raw.get('display_inning') or '').strip()
		# display_inning expected like 'T5' / 'B5' (our processor) or 'In 5'
		half_side = ''  # 'top' or 'bot'
		inning_num = ''
		if display_inning.startswith('T') and display_inning[1:].isdigit():
			half_side = 'top'
			inning_num = display_inning[1:]
		elif display_inning.startswith('B') and display_inning[1:].isdigit():
			half_side = 'bot'
			inning_num = display_inning[1:]
		else:
			# Fallbacks
			model_half = (game.half or '').lower()
			if model_half.startswith('top'): half_side = 'top'
			elif model_half.startswith('bot') or model_half.startswith('bottom'): half_side = 'bot'
			if game.period: inning_num = str(game.period)
		# Final safety: parse any digits out if still blank
		if not inning_num:
			digits = ''.join(ch for ch in display_inning if ch.isdigit())
			if digits: inning_num = digits
		# 2. Render TOP/BOT label (always ALL CAPS for consistency)
		if half_side == 'top': half_label = 'TOP'
		elif half_side == 'bot': half_label = 'BOT'
		else: half_label = ''
		state_line = f"{half_label} {inning_num}".strip()
		if state_line:
			mx = center_x(state_line[:10])
			# Inning/half line regular font
			graphics.DrawText(canvas, font, mx, 5, white, state_line[:10])
		# 3. Arrow: place next to batting team's logo (away: left side, home: right side)
		#    Direction: point inward toward the field/text.
		if half_side:
			arrow_y = 13
			if half_side == 'top':  # Away batting
				arrow_char = '>'  # point toward center from left logo
				arrow_x = 31  # tuned horizontal position; adjust if needed
			else:  # bottom -> home batting
				arrow_char = '<'
				arrow_x = 33  # a few pixels left of right logo cluster
			# try:
			# 	canvas.SetPixel(arrow_x, arrow_y, 255,255,255)  # anchor pixel to ensure visibility on some fonts
			# except Exception:
			# 	pass
			# Arrow small bold (horizontal embolden)
			draw_text_small_bold(canvas, font, arrow_x, arrow_y, white, arrow_char)
		# (Old centered arrow removed)
		# Bases diamond centered around (31,18) (shifted left 1) + outs dots above
		b1,b2,b3 = game.bases
		# Occupied base color changed to red per request
		occ = (255,0,0)
		emp = (60,60,60)
		def setp(x,y,color):
			try: canvas.SetPixel(x,y,*color)
			except Exception: pass
		base_center_x = 31
		base_center_y = 18
		outs_val = game.raw.get('outs') if isinstance(game.raw.get('outs'), int) else 0
		for i in range(3):
			dot_x = base_center_x - 2 + i*2
			dot_y = base_center_y - 4
			color = (255,0,0) if i < outs_val else (70,70,70)
			setp(dot_x, dot_y, color)
		setp(base_center_x, base_center_y-2, occ if b2 else emp)      # Second
		setp(base_center_x+2, base_center_y, occ if b1 else emp)      # First
		setp(base_center_x-2, base_center_y, occ if b3 else emp)      # Third
		setp(base_center_x, base_center_y+2, (180,180,180))           # Home
		for (dx,dy) in [(-1,-1),(0,-2),(1,-1),(2,0),(1,1),(0,2),(-1,1),(-2,0)]:
			setp(base_center_x+dx, base_center_y+dy, (40,40,40))
		# Score line (use real bold font) centered with 6px glyph width at row 31
		score_combo = f"{game.away.score}-{game.home.score}"[:9]
		mxs = center_x_width(score_combo, 6)
		graphics.DrawText(canvas, bold_font, mxs, 31, white, score_combo)
		# Batter/Pitcher not shown now (removed abbreviations per request)
	else:
		# Fallback layout (manually draw with gamma-corrected text if requested)
		lines_raw = game_leaders_lines(game) if leaders else game_primary_lines(game)
		lines = prepare_lines(lines_raw, max_lines=4, max_chars=15)
		from ..Screens.common import graphics, FontManager, center_x, draw_text_small_bold
		font = FontManager.get_font()
		white = gcolor(255,255,255)
		start_y = 6
		line_height = 8
		y = start_y
		for line in lines:
			mx = center_x(line)
			draw_text_small_bold(canvas, font, mx, y, white, line)
			y += line_height
	canvas = matrix.SwapOnVSync(canvas)
	time.sleep(hold)


def cycle_games(matrix, games: Iterable[MLBGame], *, show_leaders: bool = True, per_game_seconds: float = 3.0, pre_game_seconds: float = 1.0, show_logos: bool = True, gamma_correct: bool = False):
	"""Cycle through MLB games.

	per_game_seconds: default hold time for in-progress / post games.
	pre_game_seconds: faster hold for pre-game matchups so they rotate more quickly.
	"""
	for g in games:
		# Choose faster duration for pre-game
		base_hold = pre_game_seconds if (getattr(g, 'state', '') == 'pre') else per_game_seconds
		render_game(matrix, g, leaders=False, hold=base_hold, show_logos=show_logos, big_layout=show_logos, gamma_correct=gamma_correct)
		if show_leaders and not show_logos and getattr(g, 'state', '') != 'pre':  # skip leader frame for pre-game & big layout
			render_game(matrix, g, leaders=True, hold=base_hold / 2, show_logos=show_logos, big_layout=False, gamma_correct=gamma_correct)


__all__ = ["cycle_games", "render_game"]
