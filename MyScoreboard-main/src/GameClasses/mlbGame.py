from __future__ import annotations
from typing import List, Dict, Any
from .base import BaseGame


class MLBGame(BaseGame):
	sport = "mlb"

	def __init__(self, raw: Dict[str, Any]):
		super().__init__(raw)
		# Attach MLB-specific probable pitcher info to team sides (without polluting base TeamSide dataclass)
		for role, side in (("home", self.home), ("away", self.away)):
			team_raw = raw.get(f"{role}_team", {}) or {}
			probables = team_raw.get("probables") if isinstance(team_raw, dict) else None
			probable_name = team_raw.get("probable_pitcher") if isinstance(team_raw, dict) else None
			# Derive probable_name from probables list if absent
			if not probable_name and isinstance(probables, list) and probables:
				for item in probables:
					if not isinstance(item, dict):
						continue
					ath = item.get("athlete") or {}
					if isinstance(ath, dict):
						probable_name = ath.get("fullName") or ath.get("displayName") or ath.get("shortName")
					if probable_name:
						break
			# Set dynamic attributes for screen heuristics
			if probables:
				setattr(side, "probables", probables)
			if probable_name:
				setattr(side, "probable_pitcher", probable_name)

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

	@property
	def half(self) -> str:
		return (self.raw.get("half") or "").lower()

	@property
	def bases(self):
		return (
			bool(self.raw.get("on_first")),
			bool(self.raw.get("on_second")),
			bool(self.raw.get("on_third")),
		)

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
