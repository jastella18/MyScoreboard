"""MLB screen rendering for 64x32 panel."""
from __future__ import annotations
import time
from typing import Iterable, List
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



def render_game(matrix, game: MLBGame, leaders: bool = False, hold: float = 2.5, show_logos: bool = True, big_layout: bool = True):
	canvas = matrix.CreateFrameCanvas()
	# Detect actual canvas size (fallback to assumed 64x32)
	width = getattr(canvas, 'width', getattr(canvas, 'GetWidth', lambda: 64)()) if hasattr(canvas, 'width') else 64
	height = getattr(canvas, 'height', getattr(canvas, 'GetHeight', lambda: 32)()) if hasattr(canvas, 'height') else 32

	# Ultra-small display handling (e.g., ~12x6). Provide compressed single-line output.
	if width <= 20 or height <= 8:
		from ..Screens.common import graphics, FontManager
		font = FontManager.get_font()
		white = graphics.Color(255,255,255)
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
		# Big side logo layout
		BIG = 26  # nominal target height
		# Fetch processed logos (background removed)
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
						canvas.SetPixel(px, py, int(r), int(g), int(b))  # type: ignore[attr-defined]
					except Exception:
						pass
		# Left & right logos (slightly shifted)
		blit(left_img, -6)
		if right_img:
			blit(right_img, 64 - (BIG - 6))
		from ..Screens.common import graphics, FontManager, center_x
		font = FontManager.get_font()
		white = graphics.Color(255,255,255)
		state = game.state or ""
		# Pre-game: show only logos + @time
		if state == 'pre':
			# Extract HH:MM from start_time if present
			start_iso = getattr(game, 'start_time', None) or game.start_time
			show_time = ''
			if isinstance(start_iso, str) and 'T' in start_iso:
				# Rough parse
				try:
					clock_part = start_iso.split('T',1)[1]
					show_time = clock_part[:5]
				except Exception:
					show_time = ''
			line = f"@ {show_time}" if show_time else "@ TBD"
			mx = center_x(line[:8])
			graphics.DrawText(canvas, font, mx, 8, white, line[:8])
			canvas = matrix.SwapOnVSync(canvas)
			time.sleep(hold)
			return
		# Final: logos + score + FINAL
		if state == 'post':
			score_combo = f"{game.away.score}-{game.home.score}"[:9]
			mxs = center_x(score_combo)
			graphics.DrawText(canvas, font, mxs, 8, white, score_combo)
			final_txt = "FINAL"
			mxf = center_x(final_txt)
			graphics.DrawText(canvas, font, mxf, 16, white, final_txt)
			canvas = matrix.SwapOnVSync(canvas)
			time.sleep(hold)
			return
		# In-progress layout
		inning_line = game._period_text()
		half_char = 'T' if game.half.startswith('top') else ('B' if game.half.startswith('bot') else '')
		# If display inning like T6 convert to Top 6
		if inning_line and inning_line[0] in ('T','B') and inning_line[1:].isdigit():
			full_half = 'Top' if inning_line[0]=='T' else 'BOT'
			inning_num = inning_line[1:]
			state_line = f"{full_half} {inning_num}"
		else:
			inning_num = ''.join(ch for ch in inning_line if ch.isdigit()) if inning_line else ''
			full_half = 'Top' if half_char == 'T' else ('BOT' if half_char == 'B' else '')
			state_line = f"{full_half} {inning_num}".strip()
		if state_line:
			mx = center_x(state_line[:10])
			graphics.DrawText(canvas, font, mx, 6, white, state_line[:10])
		# Centered arrow pointing toward batting team's logo (row 12)
		arrow_y = 12
		arrow_line = '<' if half_char == 'T' else '>'  # Top inning: away batting -> left logo; Bottom: home -> right logo
		mx_arrow = center_x(arrow_line)
		graphics.DrawText(canvas, font, mx_arrow, arrow_y, white, arrow_line)
		# Bases diamond centered around (31,18) (shifted left 1) + outs dots above
		b1,b2,b3 = game.bases
		occ = (255,215,0)
		emp = (60,60,60)
		def setp(x,y,color):
			try: canvas.SetPixel(x,y,*color)
			except Exception: pass
		base_center_x = 31
		base_center_y = 18
		outs_val = game.raw.get('outs') if isinstance(game.raw.get('outs'), int) else 0
		for i in range(3):
			dot_x = base_center_x - 2 + i*2
			dot_y = base_center_y - 5
			color = (255,0,0) if i < outs_val else (70,70,70)
			setp(dot_x, dot_y, color)
		setp(base_center_x, base_center_y-2, occ if b2 else emp)      # Second
		setp(base_center_x+2, base_center_y, occ if b1 else emp)      # First
		setp(base_center_x-2, base_center_y, occ if b3 else emp)      # Third
		setp(base_center_x, base_center_y+2, (180,180,180))           # Home
		for (dx,dy) in [(-1,-1),(0,-2),(1,-1),(2,0),(1,1),(0,2),(-1,1),(-2,0)]:
			setp(base_center_x+dx, base_center_y+dy, (40,40,40))
		# Score line at row 26
		score_combo = f"{game.away.score}-{game.home.score}"[:9]
		mxs = center_x(score_combo)
		graphics.DrawText(canvas, font, mxs, 26, white, score_combo)
		# Batter/Pitcher not shown now (removed abbreviations per request)
	else:
		# Fallback to original compact layout
		lines_raw = game_leaders_lines(game) if leaders else game_primary_lines(game)
		lines = prepare_lines(lines_raw, max_lines=4, max_chars=15)
		draw_frame(canvas, lines)
	canvas = matrix.SwapOnVSync(canvas)
	time.sleep(hold)


def cycle_games(matrix, games: Iterable[MLBGame], *, show_leaders: bool = True, per_game_seconds: float = 5.0, show_logos: bool = True):
	for g in games:
		render_game(matrix, g, leaders=False, hold=per_game_seconds, show_logos=show_logos, big_layout=show_logos)
		if show_leaders and not show_logos:  # skip extra leader frame in big layout for now
			render_game(matrix, g, leaders=True, hold=per_game_seconds / 2, show_logos=show_logos, big_layout=False)


__all__ = ["cycle_games", "render_game"]
