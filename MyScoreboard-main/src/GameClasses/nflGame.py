from __future__ import annotations
from typing import List
from .base import BaseGame


class NFLGame(BaseGame):
	sport = "nfl"

	def _period_text(self) -> str:
		if self.period:
			return f"Q{self.period}"
		return ""

	def leaders_lines(self) -> List[str]:
		lines: List[str] = []
		passing = self.leaders.get("passing")
		rushing = self.leaders.get("rushing")
		receiving = self.leaders.get("receiving")
		if passing:
			lines.append(f"QB {passing.get('athlete','')} {passing.get('display','')}")
		if rushing:
			lines.append(f"RB {rushing.get('athlete','')} {rushing.get('display','')}")
		if receiving:
			lines.append(f"WR {receiving.get('athlete','')} {receiving.get('display','')}")
		return lines[:3]


__all__ = ["NFLGame"]
