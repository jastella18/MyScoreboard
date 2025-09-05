#!/bin/bash
# Usage: ./switch_mode.sh all|nfl_focus|prem_morning
MODE="$1"
if [ -z "$MODE" ]; then
  echo "Provide mode name (e.g. all, nfl_focus, prem_morning)" >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF="${SCRIPT_DIR}/config.json"
if [ ! -f "$CONF" ]; then
  echo "config.json not found" >&2
  exit 1
fi
# Use jq if available; otherwise simple sed fallback.
if command -v jq >/dev/null 2>&1; then
  TMP="${CONF}.tmp"
  jq --arg m "$MODE" '.active_mode=$m' "$CONF" > "$TMP" && mv "$TMP" "$CONF"
else
  # naive replacement; assumes key appears once
  sed -i.bak -E "s/\"active_mode\"\s*:\s*\"[^"]+\"/\"active_mode\": \"$MODE\"/" "$CONF"
fi
echo "Switched active_mode to $MODE"
