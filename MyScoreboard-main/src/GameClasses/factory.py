"""Factory utilities to build Game objects from normalized api event dicts."""
from __future__ import annotations
from typing import Dict, Any, Type
from .base import BaseGame
from .nflGame import NFLGame
from .mlbGame import MLBGame
from .premGame import PremGame

SPORT_CLASS_MAP = {
    "nfl": NFLGame,
    "mlb": MLBGame,
    "prem": PremGame,
}

def game_from_event(event: Dict[str, Any]) -> BaseGame:
    cls: Type[BaseGame] = SPORT_CLASS_MAP.get(event.get("sport"), BaseGame)  # type: ignore
    return cls.from_event(event)

__all__ = ["game_from_event", "SPORT_CLASS_MAP"]
