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
				py = y + 2  # slight vertical offset
				if py >= 32:
					break
				for x in range(w):
					px = x + ox
					if px < 0 or px >= 64:
						continue
					r, g, b, *rest = pix[x, y]
					if has_alpha and rest and rest[0] == 0:
						continue
					try:
						canvas.SetPixel(px, py, int(r), int(g), int(b))  # type: ignore[attr-defined]
					except Exception:
						pass
		# Left logo partly off left edge
		blit(left_img, -4)
		# Right logo partly off right edge
		if right_img:
			blit(right_img, 64 - (BIG - 4))
		# Construct middle/status and side texts with new layout requirements:
		# inning above score, outs below score
		inning_line = game._period_text()  # already condensed (e.g., T5, B7, In 1)
		outs_line = game.outs_text
		# Scores (center combined)
		score_left = f"{game.away.score}"
		score_right = f"{game.home.score}"
		# Choose leader line (batting or pitching) based on availability
		leader_left = ''
		leader_right = ''
		leaders = game.leaders
		# Determine which leader belongs to which teamId
		for key in ("batting", "pitching"):
			info = leaders.get(key)
			if isinstance(info, dict):
				tid = info.get('teamId')
				line = info.get('athlete', '') + ' ' + (info.get('display', '') or '')
				if tid == game.away.id and not leader_left:
					leader_left = line[:14]
				elif tid == game.home.id and not leader_right:
					leader_right = line[:14]
		# Fallback abbreviations
		away_abbr = game.away.abbr
		home_abbr = game.home.abbr
		from ..Screens.common import graphics, FontManager, center_x  # reuse font
		font = FontManager.get_font()
		white = graphics.Color(255,255,255)
		# Centered inning line
		if inning_line:
			mx_inn = center_x(inning_line[:6])
			graphics.DrawText(canvas, font, mx_inn, 8, white, inning_line[:6])
		# Score centered
		score_combo = f"{score_left}-{score_right}"[:9]
		mx_sc = center_x(score_combo)
		graphics.DrawText(canvas, font, mx_sc, 18, white, score_combo)
		# Outs line
		if outs_line:
			mx_out = center_x(outs_line[:8])
			graphics.DrawText(canvas, font, mx_out, 26, white, outs_line[:8])
		# Batter (left) under left logo, Pitcher (right) under right logo
		if game.batter:
			graphics.DrawText(canvas, font, 2, 30, white, game.batter[:12])
		if game.pitcher:
			graphics.DrawText(canvas, font, 64 - (len(game.pitcher[:12])*4) - 2, 30, white, game.pitcher[:12])
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
