from __future__ import annotations
from typing import List
from .base import BaseGame


class MLBGame(BaseGame):
	sport = "mlb"

	def _period_text(self) -> str:  # inning
		# Prefer explicit display_inning from raw if present
		disp = self.raw.get("display_inning")
		if disp:
			return disp
		if self.period:
			return f"In {self.period}"  # fallback
		return ""

	@property
	def outs_text(self) -> str:
		return self.raw.get("outs_text") or ""

	@property
	def batter(self) -> str:
		return (self.raw.get("batter") or "")[:14]

	@property
	def pitcher(self) -> str:
		return (self.raw.get("pitcher") or "")[:14]

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
