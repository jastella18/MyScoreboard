"""Premier League scoreboard API wrapper with normalized event schema.

Schema matches nfl_api where possible:
{
  'id': str,
  'sport': 'prem',
  'status': str,
  'state': str,
  'clock': str,
  'period': int|None,        # soccer period (1/2, may include extra time periods)
  'start_time': str|None,
  'home_team': { 'id': str, 'abbreviation': str, 'score': str, 'record': str|None },
  'away_team': { ... },
  'leaders': { 'scoring': [ { 'athlete': str, 'display': str } ] } (if available),
  'last_play': str|None,
}
"""

from __future__ import annotations
import requests
from typing import Any, Dict, List

API_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"


class prem_api:
    @staticmethod
    def fetch_prem_scores() -> Dict[str, Any]:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _extract_team(team_block: Dict[str, Any]) -> Dict[str, Any]:
        team_info = team_block.get("team", {})
        record_list = team_block.get("record", [])
        record_summary = record_list[0].get("summary") if record_list else None
        return {
            "id": team_info.get("id"),
            "abbreviation": team_info.get("abbreviation"),
            "score": team_block.get("score", "0"),
            "record": record_summary,
        }

    @staticmethod
    def _extract_leaders(comp: Dict[str, Any]) -> Dict[str, Any]:
        # Soccer endpoint rarely provides a simple leaders block like NFL; ignore if absent.
        leaders_out: Dict[str, Any] = {}
        for entry in comp.get("leaders", []):
            name = entry.get("name")
            group = []
            for l in entry.get("leaders", [])[:3]:
                athlete = l.get("athlete", {})
                group.append({
                    "athlete": athlete.get("shortName") or athlete.get("displayName"),
                    "display": l.get("displayValue"),
                })
            if group:
                leaders_out[name or "scoring"] = group
        return leaders_out

    @staticmethod
    def process_event(event: Dict[str, Any]) -> Dict[str, Any]:
        competitions = event.get("competitions", [])
        comp = competitions[0] if competitions else {}
        status_block = comp.get("status", {})
        type_block = status_block.get("type", {})
        competitors = comp.get("competitors", [])
        home_block = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0] if competitors else {})
        away_block = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1] if len(competitors) > 1 else {})
        situation = comp.get("situation", {})

        return {
            "id": event.get("id"),
            "sport": "prem",
            "status": type_block.get("description"),
            "state": type_block.get("state"),
            "clock": status_block.get("displayClock", ""),
            "period": status_block.get("period"),
            "start_time": comp.get("startDate"),
            "home_team": prem_api._extract_team(home_block),
            "away_team": prem_api._extract_team(away_block),
            "leaders": prem_api._extract_leaders(comp),
            "last_play": (situation.get("lastPlay") or {}).get("text"),
        }

    @staticmethod
    def get_all_events_data() -> List[Dict[str, Any]]:
        data = prem_api.fetch_prem_scores()
        events = data.get("events", [])
        return [prem_api.process_event(ev) for ev in events]


if __name__ == "__main__":
    try:
        for ev in prem_api.get_all_events_data()[:3]:
            print(ev["home_team"]["abbreviation"], "vs", ev["away_team"]["abbreviation"], ev["status"], ev["clock"])    
    except Exception as exc:
        print("Premier League API test failed:", exc)
