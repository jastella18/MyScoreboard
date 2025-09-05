"""NFL scoreboard API wrapper producing normalized event dictionaries.

Returned event schema (per item in list returned by get_all_events_data):
{
  'id': str,
  'sport': 'nfl',
  'status': str,          # Human description e.g. 'In Progress', 'Final', 'Scheduled'
  'state': str,           # raw state: pre|in|post
  'clock': str,           # Display clock, may be '' pregame or after final
  'period': int|None,     # Quarter number
  'start_time': str|None, # ISO start datetime
  'home_team': { 'id': str, 'abbreviation': str, 'score': str, 'record': str|None },
  'away_team': { ... },
  'leaders': { 'passing': {...}, 'rushing': {...}, 'receiving': {...} } (optional keys present only if data available),
  'last_play': str|None,
  'situation': { 'downDistanceText': str|None, 'possession': str|None } (subset),
}
"""

from __future__ import annotations
import requests
from typing import Any, Dict, List

API_URL = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"


class nfl_api:
    @staticmethod
    def fetch_nfl_scores() -> Dict[str, Any]:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _extract_team(team_block: Dict[str, Any]) -> Dict[str, Any]:
        team_info = team_block.get("team", {})
        record_list = team_block.get("record", [])
        record_summary = None
        if record_list:
            record_summary = record_list[0].get("summary")
        return {
            "id": team_info.get("id"),
            "abbreviation": team_info.get("abbreviation"),
            "score": team_block.get("score", "0"),
            "record": record_summary,
        }

    @staticmethod
    def _extract_leaders(comp: Dict[str, Any]) -> Dict[str, Any]:
        leaders_out: Dict[str, Any] = {}
        for entry in comp.get("leaders", []):
            name = entry.get("name")
            if not entry.get("leaders"):
                continue
            first = entry["leaders"][0]
            athlete = first.get("athlete", {})
            leader_obj = {
                "athlete": athlete.get("shortName") or athlete.get("displayName"),
                "display": first.get("displayValue"),
                "teamId": (first.get("team") or {}).get("id"),
            }
            if name == "passingLeader":
                leaders_out["passing"] = leader_obj
            elif name == "rushingLeader":
                leaders_out["rushing"] = leader_obj
            elif name == "receivingLeader":
                leaders_out["receiving"] = leader_obj
        return leaders_out

    @staticmethod
    def process_event(event: Dict[str, Any]) -> Dict[str, Any]:
        competitions = event.get("competitions", [])
        comp = competitions[0] if competitions else {}
        status_block = comp.get("status", {})
        type_block = status_block.get("type", {})
        situation = comp.get("situation", {})
        competitors = comp.get("competitors", [])
        home_block = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0] if competitors else {})
        away_block = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1] if len(competitors) > 1 else {})

        return {
            "id": event.get("id"),
            "sport": "nfl",
            "status": type_block.get("description"),
            "state": type_block.get("state"),
            "clock": status_block.get("displayClock", ""),
            "period": status_block.get("period"),
            "start_time": comp.get("startDate"),
            "home_team": nfl_api._extract_team(home_block),
            "away_team": nfl_api._extract_team(away_block),
            "leaders": nfl_api._extract_leaders(comp),
            "last_play": (situation.get("lastPlay") or {}).get("text"),
            "situation": {
                "downDistanceText": situation.get("downDistanceText"),
                "possession": situation.get("possession"),
            },
        }

    @staticmethod
    def get_all_events_data() -> List[Dict[str, Any]]:
        data = nfl_api.fetch_nfl_scores()
        events = data.get("events", [])
        return [nfl_api.process_event(ev) for ev in events]


if __name__ == "__main__":  # Simple manual test
    try:
        for ev in nfl_api.get_all_events_data()[:3]:
            print(ev["home_team"]["abbreviation"], "vs", ev["away_team"]["abbreviation"], ev["status"], ev["clock"])    
    except Exception as exc:
        print("NFL API test failed:", exc)
