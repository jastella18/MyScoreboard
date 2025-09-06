"""Configuration loader for scoreboard.

Reads config.json at project root. Provides a dictionary with active mode
settings. Falls back to built-in defaults if file or keys are missing.
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    "rotation": ["nfl", "mlb", "prem"],
    "nfl": {"show_leaders": True, "leader_mode": "all", "per_game_seconds": 6},
    "mlb": {"show_batting": True, "per_game_seconds": 6, "show_logos": True},
    "prem": {"show_leaders": True, "per_game_seconds": 5},
    # Global multiplier applied to each sport's per_game_seconds (allows quick tuning)
    "duration_multiplier": 1.0,
}

def load_config(project_root: str) -> Dict[str, Any]:
    path = os.path.join(project_root, 'config.json')
    if not os.path.isfile(path):
        return DEFAULTS.copy()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except Exception:
        return DEFAULTS.copy()
    active_mode = raw.get('active_mode')
    modes = raw.get('modes', {})
    mode_cfg = modes.get(active_mode, {}) if isinstance(modes, dict) else {}
    merged = DEFAULTS.copy()
    # Shallow merge per section
    for k, v in mode_cfg.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            d = merged[k].copy()
            d.update(v)
            merged[k] = d
        else:
            merged[k] = v
    return merged

__all__ = ["load_config"]
