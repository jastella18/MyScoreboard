"""MLB batting leaders screen.

Relies on MLBGame.leaders['batting'] produced by api layer (single leader entry).
If multiple batting leaders become available, can be extended easily.
"""
from __future__ import annotations
import time
from typing import Iterable, List
from ..GameClasses.mlbGame import MLBGame
from .common import prepare_lines, draw_frame


def batting_line(game: MLBGame) -> List[str]:
	batting = game.leaders.get('batting')
	if not batting:
		return [game.score_line(), 'BAT --']
	athlete = batting.get('athlete', '')
	display = batting.get('display', '')
	short = display.replace(' HR', 'HR').replace(' RBI', 'RBI')
	return [game.score_line(), f"BAT {athlete} {short}"]


def render_batting(matrix, game: MLBGame, hold: float = 3.0):
	canvas = matrix.CreateFrameCanvas()
	lines = prepare_lines(batting_line(game), max_lines=4, max_chars=15)
	draw_frame(canvas, lines)
	canvas = matrix.SwapOnVSync(canvas)
	time.sleep(hold)


def cycle_batting(matrix, games: Iterable[MLBGame], per_game_seconds: float = 4.0):
	for g in games:
		render_batting(matrix, g, hold=per_game_seconds)


__all__ = ["cycle_batting", "render_batting", "batting_line"]
