"""Screen helper for displaying Premier League goal scorers (leaders lines).

Consumes PremGame objects for rendering.
"""
from __future__ import annotations
from typing import List
from ..GameClasses.premGame import PremGame


def goal_scorer_lines(game: PremGame) -> List[str]:
	lines = [game.score_line(), game.status_line()]
	lines.extend(game.leaders_lines())
	return lines[:6]


__all__ = ["goal_scorer_lines"]
