"""MLB screen rendering for 64x32 panel."""
from __future__ import annotations
import time
from typing import Iterable, List
from ..GameClasses.mlbGame import MLBGame
from .common import prepare_lines, draw_frame


def game_primary_lines(game: MLBGame) -> List[str]:
	base = [game.score_line(), game.status_line()]
	if game.last_play and game.state == 'in':
		base.append(game.last_play)
	return base


def game_leaders_lines(game: MLBGame) -> List[str]:
	return game.leaders_lines()


def render_game(matrix, game: MLBGame, leaders: bool = False, hold: float = 2.5):
	canvas = matrix.CreateFrameCanvas()
	lines_raw = game_leaders_lines(game) if leaders else game_primary_lines(game)
	lines = prepare_lines(lines_raw, max_lines=4, max_chars=15)
	draw_frame(canvas, lines)
	canvas = matrix.SwapOnVSync(canvas)
	time.sleep(hold)


def cycle_games(matrix, games: Iterable[MLBGame], *, show_leaders: bool = True, per_game_seconds: float = 5.0):
	for g in games:
		render_game(matrix, g, leaders=False, hold=per_game_seconds / (2 if show_leaders else 1))
		if show_leaders:
			render_game(matrix, g, leaders=True, hold=per_game_seconds / 2)


__all__ = ["cycle_games", "render_game"]
