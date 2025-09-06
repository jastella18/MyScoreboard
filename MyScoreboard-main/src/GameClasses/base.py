"""Base game model and utilities for scoreboard presentation.

Each concrete Game class wraps a normalized event dict (from api layer) and
exposes convenience properties + formatted lines for display screens.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Type, TypeVar, Optional


@dataclass
class TeamSide:
    id: Optional[str]
    abbr: str
    score: str
    record: Optional[str]
    logo: Optional[str] = None  # URL if available

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TeamSide":
        return TeamSide(
            id=d.get("id"),
            abbr=d.get("abbreviation") or "???",
            score=str(d.get("score", "0")),
            record=d.get("record"),
            logo=d.get("logo"),
        )


T = TypeVar("T", bound="BaseGame")


class BaseGame:
    sport: str = "generic"

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.id: str = raw.get("id")
        self.state: str = raw.get("state")
        self.status: str = raw.get("status")
        self.clock: str = raw.get("clock", "")
        self.period = raw.get("period")
        self.start_time: str = raw.get("start_time")
        self.home = TeamSide.from_dict(raw.get("home_team", {}))
        self.away = TeamSide.from_dict(raw.get("away_team", {}))
        self.leaders: Dict[str, Any] = raw.get("leaders", {})
        self.last_play: Optional[str] = raw.get("last_play")

    # ---------- Factories ----------
    @classmethod
    def from_event(cls: Type[T], event: Dict[str, Any]) -> T:
        return cls(event)

    # ---------- Presentation helpers ----------
    def score_line(self) -> str:
        return f"{self.away.abbr} {self.away.score} - {self.home.score} {self.home.abbr}"

    def status_line(self) -> str:
        if self.state == "pre":
            return self.status or "Scheduled"
        if self.state == "post":
            return self.status or "Final"
        # in-progress
        period_txt = self._period_text()
        return f"{period_txt} {self.clock}".strip()

    def leaders_lines(self) -> List[str]:
        # Base version: compress generic leaders dict
        lines: List[str] = []
        for key, info in self.leaders.items():
            if isinstance(info, dict):
                lines.append(f"{key[:3].upper()} {info.get('athlete','')} {info.get('display','')}")
            elif isinstance(info, list):  # list of dicts (prem scoring leaders)
                for item in info[:3]:
                    lines.append(f"{key[:3].upper()} {item.get('athlete','')} {item.get('display','')}")
        return lines[:3]

    def detail_lines(self) -> List[str]:
        lines = [self.score_line(), self.status_line()]
        if self.last_play and self.state == "in":
            lines.append(self.last_play[:48])
        return lines

    # ---------- Internal helpers ----------
    def _period_text(self) -> str:
        return f"P{self.period}" if self.period is not None else ""

    # ---------- Generic mapping for screen usage ----------
    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sport": self.sport,
            "score_line": self.score_line(),
            "status_line": self.status_line(),
            "leaders": self.leaders_lines(),
            "detail_lines": self.detail_lines(),
        }


__all__ = ["BaseGame", "TeamSide"]
