"""NFL yards leader screens (passing, rushing, receiving) for 64x32 panel.

Uses NFLGame objects' leaders dict produced by api layer.
"""
from __future__ import annotations
import time
from typing import Iterable, List, Callable
from ..GameClasses.nflGame import NFLGame
from .common import prepare_lines, draw_frame


def _leader_fragment(game: NFLGame, key: str, label: str) -> str:
	info = game.leaders.get(key)
	if not info:
		return f"{label} --"
	athlete = info.get('athlete', '')
	display = info.get('display', '')
	# Trim verbose stats for compactness
	short = display.replace(' YDS', 'Y').replace('TD', 'T')
	return f"{label} {athlete} {short}"[:22]


def passing_line(game: NFLGame) -> List[str]:
	return [game.score_line(), _leader_fragment(game, 'passing', 'QB')]


def rushing_line(game: NFLGame) -> List[str]:
	return [game.score_line(), _leader_fragment(game, 'rushing', 'RB')]


def receiving_line(game: NFLGame) -> List[str]:
	return [game.score_line(), _leader_fragment(game, 'receiving', 'WR')]


def _render_matrix(matrix, lines_raw: List[str], hold: float):
	canvas = matrix.CreateFrameCanvas()
	lines = prepare_lines(lines_raw, max_lines=4, max_chars=15)
	draw_frame(canvas, lines)
	canvas = matrix.SwapOnVSync(canvas)
	time.sleep(hold)


def cycle_leaders(matrix, games: Iterable[NFLGame], *, mode: str = 'all', per_game_seconds: float = 4.0):
	"""Cycle through leader views.

	mode options:
	  'passing' | 'rushing' | 'receiving' | 'all'
	"""
	mode_funcs: dict[str, Callable[[NFLGame], List[str]]] = {
		'passing': passing_line,
		'rushing': rushing_line,
		'receiving': receiving_line,
	}
	for g in games:
		if mode == 'all':
			for key in ('passing', 'rushing', 'receiving'):
				_render_matrix(matrix, mode_funcs[key](g), hold=per_game_seconds / 3)
		else:
			fn = mode_funcs.get(mode, passing_line)
			_render_matrix(matrix, fn(g), hold=per_game_seconds)


__all__ = [
	'cycle_leaders', 'passing_line', 'rushing_line', 'receiving_line'
]
