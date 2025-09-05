from __future__ import annotations
from typing import List
from .base import BaseGame


class PremGame(BaseGame):
	sport = "prem"

	def _period_text(self) -> str:
		if self.period == 1:
			return "1H"
		if self.period == 2:
			return "2H"
		if self.period:
			return f"P{self.period}"
		return ""

	def leaders_lines(self) -> List[str]:
		# Use scoring leaders if present
		lines: List[str] = []
		# Different keys may exist; flatten all lists
		for key, val in self.leaders.items():
			if isinstance(val, list):
				for item in val[:3]:
					lines.append(f"G {item.get('athlete','')} {item.get('display','')}")
		return lines[:3]


__all__ = ["PremGame"]
