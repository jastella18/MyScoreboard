"""Scheduling and rotation utilities for multi-sport scoreboard.

Provides:
 - Cached fetching per sport (NFL, MLB, Premier League)
 - Conversion to Game objects via factory
 - Rotation helpers yielding sequences of games in a configured order
 - Simple filtering hooks (e.g., in-progress first)

Assumptions: All API wrappers return normalized event dicts with 'sport' key.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Iterable, Iterator, Sequence, Callable, Optional

from .api.nfl_api import nfl_api
from .api.mlb_api import mlb_api
from .api.prem_api import prem_api
from .GameClasses.factory import game_from_event
from .GameClasses.base import BaseGame

# --------------------------- Configuration ---------------------------------
DEFAULT_ROTATION: Sequence[str] = ("nfl", "mlb", "prem")
CACHE_TTL_SECONDS = 30  # reasonable compromise for near-real-time without hammering APIs

# ----------------------------- Cache Layer ---------------------------------
_cache: Dict[str, Dict[str, object]] = {
	# sport: { 'timestamp': datetime, 'events': [event_dicts] }
}


def _expired(ts: datetime) -> bool:
	return datetime.utcnow() - ts > timedelta(seconds=CACHE_TTL_SECONDS)


def _fetch_sport_raw(sport: str) -> List[dict]:
	if sport == "nfl":
		return nfl_api.get_all_events_data()
	if sport == "mlb":
		return mlb_api.get_all_events_data()
	if sport == "prem":
		return prem_api.get_all_events_data()
	return []


def get_events_for_sport(sport: str, force_refresh: bool = False) -> List[dict]:
	"""Return list of normalized event dicts for given sport with caching."""
	sport = sport.lower()
	entry = _cache.get(sport)
	if (not force_refresh) and entry and isinstance(entry.get('timestamp'), datetime) and not _expired(entry['timestamp']):
		return entry.get('events', [])  # type: ignore
	try:
		events = _fetch_sport_raw(sport)
	except Exception:
		# On error return stale if present
		if entry:
			return entry.get('events', [])  # type: ignore
		return []
	_cache[sport] = { 'timestamp': datetime.utcnow(), 'events': events }
	return events


def get_games_for_sport(sport: str, *, force_refresh: bool = False, filter_fn: Optional[Callable[[BaseGame], bool]] = None) -> List[BaseGame]:
	events = get_events_for_sport(sport, force_refresh=force_refresh)
	games: List[BaseGame] = [game_from_event(ev) for ev in events]
	if filter_fn:
		games = [g for g in games if filter_fn(g)]
	return games


# -------------------------- Rotation Utilities ------------------------------
def rotation_iterator(
	rotation: Sequence[str] = DEFAULT_ROTATION,
	*,
	prioritize_in_progress: bool = True,
	include_empty: bool = False,
	dynamic_reorder: bool = True,
) -> Iterator[List[BaseGame]]:
	"""Yield batches of games per sport.

	Enhancements:
	  - Within a sport: in-progress first, then pre, then post (if prioritize_in_progress)
	  - Across sports (if dynamic_reorder): sports with at least one in-progress game
		are yielded before those without, preserving original relative order inside each group.
	"""
	while True:
		if dynamic_reorder:
			active_pairs = []  # sports that currently have an in-progress game
			inactive_pairs = []
			for sport in rotation:
				games = get_games_for_sport(sport, force_refresh=False)
				if prioritize_in_progress:
					in_prog = [g for g in games if g.state == 'in']
					post = [g for g in games if g.state == 'post']
					pre = [g for g in games if g.state == 'pre']
					games = in_prog + pre + post
				target = active_pairs if any(g.state == 'in' for g in games) else inactive_pairs
				if games or include_empty:
					target.append((sport, games))
			ordered = active_pairs + inactive_pairs
			for _, games in ordered:
				yield games
		else:
			for sport in rotation:
				games = get_games_for_sport(sport, force_refresh=False)
				if prioritize_in_progress:
					in_prog = [g for g in games if g.state == 'in']
					post = [g for g in games if g.state == 'post']
					pre = [g for g in games if g.state == 'pre']
					games = in_prog + pre + post
				if games or include_empty:
					yield games


def next_rotation_snapshot(rotation: Sequence[str] = DEFAULT_ROTATION) -> Dict[str, List[BaseGame]]:
	"""Return a one-time snapshot mapping sport->games (no infinite loop)."""
	snapshot: Dict[str, List[BaseGame]] = {}
	for sport in rotation:
		snapshot[sport] = get_games_for_sport(sport)
	return snapshot


# ---------------------------- Day Filtering ---------------------------------
def games_for_today(sport: str) -> List[BaseGame]:
	"""Return games scheduled today (simple date match on start_time)."""
	today = datetime.utcnow().date()
	games = get_games_for_sport(sport)
	filtered: List[BaseGame] = []
	for g in games:
		try:
			if g.start_time and datetime.fromisoformat(g.start_time.replace('Z', '+00:00')).date() == today:
				filtered.append(g)
		except Exception:
			# Ignore parse error, skip game
			pass
	return filtered


# ---------------------------- Demo / CLI ------------------------------------
def _demo_print_snapshot():  # pragma: no cover (dev utility)
	snap = next_rotation_snapshot()
	for sport, games in snap.items():
		print(f"=== {sport.upper()} ({len(games)} games) ===")
		for g in games[:5]:
			print(" ", g.score_line(), '|', g.status_line())


if __name__ == "__main__":  # simple manual demo
	_demo_print_snapshot()

