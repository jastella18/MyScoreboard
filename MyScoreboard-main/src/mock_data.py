"""Static mock event data for offline / demo mode.

Normalized structures match the API wrappers' `get_all_events_data` output
so downstream code (GameClasses + Screens) can operate unchanged.

Enable via: `python -m src.main --mock`
"""
from __future__ import annotations
from datetime import datetime, timedelta

# Simple helper to build ISO times relative to now (keeps 'today' context)
def _iso(minutes_from_now: int) -> str:
    return (datetime.utcnow() + timedelta(minutes=minutes_from_now)).isoformat(timespec="minutes") + "Z"

mock_events = {
    "nfl": [
        {
            "id": "nfl_pre_1",
            "sport": "nfl",
            "status": "Scheduled",
            "state": "pre",
            "clock": "",
            "period": None,
            "start_time": _iso(60),
            "home_team": {"id": "1", "abbreviation": "KC", "score": "0", "record": "0-0"},
            "away_team": {"id": "2", "abbreviation": "BUF", "score": "0", "record": "0-0"},
            "leaders": {},
            "last_play": None,
            "situation": {"downDistanceText": None, "possession": None},
        },
        {
            "id": "nfl_in_1",
            "sport": "nfl",
            "status": "In Progress",
            "state": "in",
            "clock": "05:12",
            "period": 2,
            "start_time": _iso(-40),
            "home_team": {"id": "3", "abbreviation": "PHI", "score": "10", "record": "0-0"},
            "away_team": {"id": "4", "abbreviation": "DAL", "score": "13", "record": "0-0"},
            "leaders": {"passing": {"athlete": "J.Hurts", "display": "145Y 1TD", "teamId": "3"}},
            "last_play": "Hurts pass short left to Brown for 8 yards",
            "situation": {"downDistanceText": "2nd & 2", "possession": "PHI"},
        },
        {
            "id": "nfl_post_1",
            "sport": "nfl",
            "status": "Final",
            "state": "post",
            "clock": "",
            "period": 4,
            "start_time": _iso(-180),
            "home_team": {"id": "5", "abbreviation": "NYJ", "score": "17", "record": "1-0"},
            "away_team": {"id": "6", "abbreviation": "NE", "score": "14", "record": "0-1"},
            "leaders": {"passing": {"athlete": "A.Rodgers", "display": "230Y 2TD", "teamId": "5"}},
            "last_play": None,
            "situation": {"downDistanceText": None, "possession": None},
        },
    ],
    "mlb": [
        # In-progress snapshot derived from provided CHC vs WSH JSON (assumptions where truncated)
        {
            "id": "401697025_in",
            "sport": "mlb",
            "status": "In Progress",
            "state": "in",
            "clock": "",
            "period": 6,  # assume mid-game live inning
            "start_time": _iso(-60),  # started an hour ago
            "home_team": {"id": "16", "abbreviation": "CHC", "score": "11", "record": "81-60", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/chc.png"},
            # Away portion of snippet truncated: using reasonable placeholder values
            "away_team": {"id": "20", "abbreviation": "WSH", "score": "4", "record": "65-76", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/wsh.png"},
            # Linescores from provided home data; away fabricated partial for demo
            "linescore": {"home": [5,1,0,2,0,2], "away": [1,0,1,0,1,1]},
            "leaders": {
                # Map one of the batting leaders (homeRuns) to batting; no pitching leader in snippet portion
                "batting": {"athlete": "R.McGuire", "display": "2-4 HR RBI R", "teamId": "16"},
            },
            "last_play": "Swanson doubles to deep left, Hoerner scores.",
            "display_inning": "T6",  # assume top 6th
            "outs": 1,
            "outs_text": "1 OUT",
            "batter": "P.Crow-Armstr",
            "pitcher": "J.Assad",
            "half": "top",
            "on_first": True,
            "on_second": False,
            "on_third": False,
            "situation_raw": {},
        },
        # Final snapshot of same game
        {
            "id": "401697025_final",
            "sport": "mlb",
            "status": "Final",
            "state": "post",
            "clock": "",
            "period": 9,
            "start_time": _iso(-180),
            "home_team": {"id": "16", "abbreviation": "CHC", "score": "11", "record": "82-60", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/chc.png"},
            "away_team": {"id": "20", "abbreviation": "WSH", "score": "5", "record": "65-77", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/wsh.png"},
            "linescore": {"home": [5,1,0,2,0,2,0,1], "away": [1,0,1,0,1,1,0,1]},
            "leaders": {
                "batting": {"athlete": "N.Hoerner", "display": "2-4 HR 2B 2RBI", "teamId": "16"},
                # Provide a pseudo pitching line
                "pitching": {"athlete": "J.Assad", "display": "6.0 IP 2ER 7K", "teamId": "16"},
            },
            "last_play": None,
            "display_inning": "",
            "outs": 0,
            "outs_text": None,
            "batter": None,
            "pitcher": None,
            "half": "",
            "on_first": False,
            "on_second": False,
            "on_third": False,
            "situation_raw": {},
        },
        # Upcoming (pre) mock using same teams for variety
        {
            "id": "401697025_pre",
            "sport": "mlb",
            "status": "Scheduled",
            "state": "pre",
            "clock": "",
            "period": None,
            "start_time": _iso(30),
            "home_team": {"id": "16", "abbreviation": "CHC", "score": "0", "record": "82-60", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/chc.png"},
            "away_team": {"id": "20", "abbreviation": "WSH", "score": "0", "record": "65-77", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/scoreboard/wsh.png"},
            "linescore": {"home": [], "away": []},
            "leaders": {},
            "last_play": None,
            "display_inning": "",
            "outs": 0,
            "outs_text": None,
            "batter": None,
            "pitcher": None,
            "half": "",
            "on_first": False,
            "on_second": False,
            "on_third": False,
            "situation_raw": {},
        },
    ],
    "prem": [
        {
            "id": "prem_in_1",
            "sport": "prem",
            "status": "45'",
            "state": "in",
            "clock": "45:00",
            "period": 1,
            "start_time": _iso(-50),
            "home_team": {"id": "20", "abbreviation": "ARS", "score": "1", "record": "0-0-0"},
            "away_team": {"id": "21", "abbreviation": "CHE", "score": "0", "record": "0-0-0"},
            "leaders": {"scoringLeader": [{"athlete": "Saka", "display": "1 G"}]},
            "last_play": "Saka scores with left footed shot.",
        },
        {
            "id": "prem_pre_1",
            "sport": "prem",
            "status": "Scheduled",
            "state": "pre",
            "clock": "",
            "period": None,
            "start_time": _iso(120),
            "home_team": {"id": "22", "abbreviation": "MCI", "score": "0", "record": "0-0-0"},
            "away_team": {"id": "23", "abbreviation": "LIV", "score": "0", "record": "0-0-0"},
            "leaders": {},
            "last_play": None,
        },
        {
            "id": "prem_post_1",
            "sport": "prem",
            "status": "Final",
            "state": "post",
            "clock": "",
            "period": 2,
            "start_time": _iso(-200),
            "home_team": {"id": "24", "abbreviation": "MUN", "score": "2", "record": "1-0-0"},
            "away_team": {"id": "25", "abbreviation": "TOT", "score": "2", "record": "0-1-0"},
            "leaders": {},
            "last_play": None,
        },
    ],
}

__all__ = ["mock_events"]
