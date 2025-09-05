from __future__ import annotations
from typing import List
from .base import BaseGame


class MLBGame(BaseGame):
	sport = "mlb"

	def _period_text(self) -> str:  # inning
		if self.period:
			return f"In {self.period}"  # Keep short for display matrix
		return ""

	def leaders_lines(self) -> List[str]:
		lines: List[str] = []
		pitching = self.leaders.get("pitching")
		batting = self.leaders.get("batting")
		if pitching:
			lines.append(f"P {pitching.get('athlete','')} {pitching.get('display','')}")
		if batting:
			lines.append(f"B {batting.get('athlete','')} {batting.get('display','')}")
		return lines[:3]


__all__ = ["MLBGame"]
