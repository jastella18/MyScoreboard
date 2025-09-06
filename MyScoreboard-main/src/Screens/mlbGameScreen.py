"""MLB screen rendering for 64x32 panel."""
from __future__ import annotations
import time
from typing import Iterable, List
from ..GameClasses.mlbGame import MLBGame
from ..logo_cache import get_logo, get_logo_from_url
from .common import prepare_lines, draw_frame


def game_primary_lines(game: MLBGame) -> List[str]:
	base = [game.score_line(), game.status_line()]
	if game.last_play and game.state == 'in':
		base.append(game.last_play)
	return base


def game_leaders_lines(game: MLBGame) -> List[str]:
	return game.leaders_lines()



def render_game(matrix, game: MLBGame, leaders: bool = False, hold: float = 2.5, show_logos: bool = True):
	canvas = matrix.CreateFrameCanvas()
	lines_raw = game_leaders_lines(game) if leaders else game_primary_lines(game)
	# If logos, allow fewer chars (reserve ~16px each side -> ~32px taken -> 32px text area => 8 chars at 4px width)
	max_chars = 15 if not show_logos else 8
	lines = prepare_lines(lines_raw, max_lines=4, max_chars=max_chars)
	if show_logos:
		left = get_logo('mlb', game.away.abbr) or get_logo_from_url(game.away.logo or '', f"mlb:{game.away.abbr}")
		right = get_logo('mlb', game.home.abbr) or get_logo_from_url(game.home.logo or '', f"mlb:{game.home.abbr}")
		# Draw logos at y=0 if available
		if left is not None:
			try:
				canvas.SetImage(left, 0, 0)  # type: ignore[attr-defined]
			except Exception:
				pass
		if right is not None:
			try:
				# place at far right (64 - size)
				x = 64 - right.width
				canvas.SetImage(right, x, 0)  # type: ignore[attr-defined]
			except Exception:
				pass
		# Draw text lower to avoid overlapping logos
		draw_frame(canvas, lines, start_y=18, center=not show_logos or max_chars >= 12)
	else:
		draw_frame(canvas, lines)
	canvas = matrix.SwapOnVSync(canvas)
	time.sleep(hold)


def cycle_games(matrix, games: Iterable[MLBGame], *, show_leaders: bool = True, per_game_seconds: float = 5.0, show_logos: bool = True):
	for g in games:
		render_game(matrix, g, leaders=False, hold=per_game_seconds / (2 if show_leaders else 1), show_logos=show_logos)
		if show_leaders:
			render_game(matrix, g, leaders=True, hold=per_game_seconds / 2, show_logos=show_logos)


__all__ = ["cycle_games", "render_game"]
