"""MLB scoreboard API wrapper with normalized event schema aligning to nfl_api.

MLB endpoint specifics: innings instead of quarters, potential linescores per inning.
Event dict:
{
  'id': str,
  'sport': 'mlb',
  'status': str,
  'state': str,
  'clock': str,          # often '' or counts (may show 'Bot 5th' via detail; kept minimal here)
  'period': int|None,    # current inning number
  'start_time': str|None,
  'home_team': { 'id': str, 'abbreviation': str, 'score': str, 'record': str|None },
  'away_team': { ... },
  'linescore': { 'home': [int,...], 'away': [int,...] } (if available),
  'leaders': { 'pitching': {...}, 'batting': {...} } (subset if available),
  'last_play': str|None,
}
"""

from __future__ import annotations
import requests
from typing import Any, Dict, List

API_URL = "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"


class mlb_api:
    @staticmethod
    def fetch_mlb_scores() -> Dict[str, Any]:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _extract_team(team_block: Dict[str, Any]) -> Dict[str, Any]:
        team_info = team_block.get("team", {})
        record_list = team_block.get("record", [])
        record_summary = record_list[0].get("summary") if record_list else None
        # ESPN often supplies multiple logo sizes in 'logos'; prefer first.
        logo_url = None
        logos = team_info.get("logos") or []
        if logos and isinstance(logos, list):
            logo_url = logos[0].get("href")
        if not logo_url:
            # Some endpoints may have a single 'logo' field.
            logo_url = team_info.get("logo")
        return {
            "id": team_info.get("id"),
            "abbreviation": team_info.get("abbreviation"),
            "score": team_block.get("score", "0"),
            "record": record_summary,
            "logo": logo_url,
        }

    @staticmethod
    def _extract_linescore(comp: Dict[str, Any]) -> Dict[str, List[int]]:
        ls = comp.get("linescores", [])
        # Format differs from NFL; each competitor has linescores array inside competitor in some endpoints
        out = {"home": [], "away": []}
        competitors = comp.get("competitors", [])
        for c in competitors:
            key = c.get("homeAway")
            innings = []
            for inn in c.get("linescores", []):
                val = inn.get("value")
                if isinstance(val, int):
                    innings.append(val)
            if key == "home":
                out["home"] = innings
            elif key == "away":
                out["away"] = innings
        return out

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
            # Map MLB-specific buckets into generic keys
            if name and "pitch" in name.lower():
                leaders_out["pitching"] = leader_obj
            elif name and ("hit" in name.lower() or "bat" in name.lower()):
                leaders_out["batting"] = leader_obj
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
            "sport": "mlb",
            "status": type_block.get("description"),
            "state": type_block.get("state"),
            "clock": status_block.get("displayClock", ""),  # seldom used
            "period": status_block.get("period"),  # inning
            "start_time": comp.get("startDate"),
            "home_team": mlb_api._extract_team(home_block),
            "away_team": mlb_api._extract_team(away_block),
            "linescore": mlb_api._extract_linescore(comp),
            "leaders": mlb_api._extract_leaders(comp),
            "last_play": (situation.get("lastPlay") or {}).get("text"),
        }

    @staticmethod
    def get_all_events_data() -> List[Dict[str, Any]]:
        data = mlb_api.fetch_mlb_scores()
        events = data.get("events", [])
        return [mlb_api.process_event(ev) for ev in events]


if __name__ == "__main__":
    try:
        for ev in mlb_api.get_all_events_data()[:3]:
            print(ev["home_team"]["abbreviation"], "vs", ev["away_team"]["abbreviation"], ev["status"], ev.get("period"))
    except Exception as exc:
        print("MLB API test failed:", exc)