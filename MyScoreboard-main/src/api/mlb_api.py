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
        out = {
            "id": team_info.get("id"),
            "abbreviation": team_info.get("abbreviation"),
            "score": team_block.get("score", "0"),
            "record": record_summary,
            "logo": logo_url,
        }
        # Probable starting pitcher extraction.
        # Newer ESPN MLB scoreboard adds a 'probables' list under competitor with objects containing 'athlete'.
        prob_list = team_block.get("probables")
        if isinstance(prob_list, list) and prob_list:
            out["probables"] = prob_list
            # Take first athlete full/display name as probable_pitcher convenience field
            first = prob_list[0]
            if isinstance(first, dict):
                ath = first.get("athlete") or {}
                if isinstance(ath, dict):
                    out["probable_pitcher"] = ath.get("fullName") or ath.get("displayName") or ath.get("shortName")
                else:
                    # fallback direct
                    out["probable_pitcher"] = first.get("displayName") or first.get("fullName")
        # Some variants have a single 'probableStartingPitcher' object (as per user sample 'probableStartingPitcher')
        psp = team_block.get("probableStartingPitcher") or team_block.get("probableStartingPitcherId")
        if isinstance(psp, dict):
            ath_name = psp.get("fullName") or psp.get("displayName") or psp.get("shortName")
            if ath_name and not out.get("probable_pitcher"):
                out["probable_pitcher"] = ath_name
        return out

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
        # Some ESPN variants put shortDetail/detail inside type_block (e.g., "Top 5th"). Capture for fallback parsing.
        detail_texts = [
            type_block.get("shortDetail") or "",
            type_block.get("detail") or "",
            status_block.get("type", {}).get("shortDetail") or "",
            status_block.get("type", {}).get("detail") or "",
        ]
        competitors = comp.get("competitors", [])
        home_block = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0] if competitors else {})
        away_block = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1] if len(competitors) > 1 else {})
        situation = comp.get("situation", {})
        # Venue name (stadium) for pre-game display
        venue_block = comp.get("venue", {}) or {}
        venue_name = None
        if isinstance(venue_block, dict):
            venue_name = venue_block.get("fullName") or venue_block.get("name")
        # Extract richer situation data (inning half, outs, batter, pitcher)
        half = (situation.get("halfInning") or situation.get("inningHalf") or "").lower()
        if not half:
            # Fallback parse from textual detail (e.g., "Bot 4th", "Top 7th")
            import re
            joined = " | ".join(t for t in detail_texts if t)
            m = re.search(r"\b(Top|Bot|Bottom)\b", joined, re.IGNORECASE)
            if m:
                val = m.group(1).lower()
                if val.startswith("top"): half = "top"
                elif val.startswith("bot"): half = "bot"
                elif val.startswith("bottom"): half = "bot"
        inning_num = situation.get("inning") or status_block.get("period")
        if half and inning_num:
            if half.startswith("top"):
                display_inning = f"T{inning_num}"
            elif half.startswith("bot") or half.startswith("bottom"):
                display_inning = f"B{inning_num}"
            else:
                display_inning = f"In {inning_num}"
        else:
            display_inning = f"In {status_block.get('period')}" if status_block.get('period') else ''
        outs = situation.get("outs")
        outs_text = None
        if isinstance(outs, int):
            outs_text = f"{outs} OUT" if outs == 1 else f"{outs} OUTS"
        batter_block = situation.get("batter") or {}
        pitcher_block = situation.get("pitcher") or {}
        batter_name = batter_block.get("shortName") or batter_block.get("displayName")
        pitcher_name = pitcher_block.get("shortName") or pitcher_block.get("displayName")
        # Base occupancy + half inning
        on_first = bool(situation.get("onFirst"))
        on_second = bool(situation.get("onSecond"))
        on_third = bool(situation.get("onThird"))
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
            "display_inning": display_inning,
            "outs": outs,
            "outs_text": outs_text,
            "batter": batter_name,
            "pitcher": pitcher_name,
            "half": half,
            "on_first": on_first,
            "on_second": on_second,
            "on_third": on_third,
            # Include raw sub-dict for richer debugging / future use (arrow logic previously queried this)
            "situation_raw": situation,
            "venue": venue_name,
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