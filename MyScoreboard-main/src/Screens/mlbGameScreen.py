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
		BIG = 28
		MEDIUM = 22
		SMALL = 14
		EXTRA_SMALL = 10
		# Fetch processed logos (background removed)
		left_img = get_processed_logo('mlb', game.away.abbr, url=game.away.logo, size=MEDIUM, remove_bg=True)
		right_img = get_processed_logo('mlb', game.home.abbr, url=game.home.logo, size=MEDIUM, remove_bg=True)
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
				py = y + 2  # slight vertical offset
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
		# Left logo partly off left edge
		blit(left_img, -4)
		# Right logo partly off right edge
		if right_img:
			blit(right_img, 64 - (BIG - 4))
		# New top-left stack layout per spec
		from ..Screens.common import graphics, FontManager
		font = FontManager.get_font()
		white = graphics.Color(255,255,255)
		# Line 1: T/B + inning number + outs (e.g., T6 2O)
		inning_line = game._period_text()
		half_char = 'T' if game.half.startswith('top') else ('B' if game.half.startswith('bot') else '')
		inning_num = ''.join(ch for ch in inning_line if ch.isdigit()) if inning_line else ''
		outs_val = game.raw.get('outs')
		outs_part = f" {outs_val}O" if isinstance(outs_val, int) else ''
		state_line = f"{half_char}{inning_num}{outs_part}"[:7]
		graphics.DrawText(canvas, font, 0, 7, white, state_line)
		# Line 2: Arrow pointing to batting team abbreviation
		batting_abbr = game.away.abbr if half_char == 'T' else game.home.abbr
		arrow_line = f"> {batting_abbr}"[:7]
		graphics.DrawText(canvas, font, 0, 13, white, arrow_line)
		# Line 3: Base diamond (using small 5x5 area) origin (0,14)
		b1,b2,b3 = game.bases
		occ = (255,215,0)  # gold
		emp = (70,70,70)
		def setp(x,y,color):
			try: canvas.SetPixel(x,y,*color)
			except Exception: pass
		# Coordinates shaped like diamond
		# Second base (2,15)
		setp(2,15, occ if b2 else emp)
		# First (4,17)
		setp(4,17, occ if b1 else emp)
		# Third (0,17)
		setp(0,17, occ if b3 else emp)
		# Home (2,19) faint when no runner
		setp(2,19, *( (180,180,180) ))
		# Optional connecting outline (light)
		for (x,y) in [(1,16),(2,17),(3,16),(2,15),(1,16)]:
			setp(x,y,(40,40,40))
		# Line 4: Score just below (0,25)
		score_combo = f"{game.away.score}-{game.home.score}"[:9]
		graphics.DrawText(canvas, font, 0, 25, white, score_combo)
		# Batter/Pitcher right side small labels (to avoid overlap with logos auto region)
		if game.batter:
			graphics.DrawText(canvas, font, 24, 11, white, game.batter[:8])
		if game.pitcher:
			graphics.DrawText(canvas, font, 24, 19, white, game.pitcher[:8])
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
