"""Logo caching utilities.

Looks for logos under assets/Logos/<SPORT>/<TEAM>/<TEAM>.png
Resizes to a target square (default 14x14) for the 64x32 panel.
Gracefully returns None if file missing.
"""
from __future__ import annotations
import os
from typing import Dict, Tuple, Optional, Deque
from collections import deque
import threading
import time
import requests

try:
    from PIL import Image  # type: ignore
except Exception:  # Pillow missing or not installed
    Image = None  # type: ignore

_CACHE: Dict[Tuple[str, int], object] = {}
_URL_CACHE: Dict[Tuple[str, int], object] = {}
_LOCK = threading.Lock()
_URL_EXPIRY: Dict[Tuple[str, int], float] = {}
URL_TTL = 3600  # refresh remote logos hourly

def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def logo_path(sport: str, team_abbr: str) -> str:
    sport_dir = sport.upper()
    team = team_abbr.upper()
    return os.path.join(_project_root(), 'assets', 'Logos', sport_dir, team, f'{team}.png')

def get_logo(sport: str, team_abbr: str, size: int = 14):
    if Image is None:
        return None
    key = (f"{sport}:{team_abbr}".upper(), size)
    if key in _CACHE:
        return _CACHE[key]
    path = logo_path(sport, team_abbr)
    if not os.path.isfile(path):
        # Try remote download if we have a previously captured URL in team meta (passed separately later)
        return None
    try:
        img = Image.open(path).convert('RGB')
        if img.width != size or img.height != size:
            img = img.resize((size, size), Image.LANCZOS)
        _CACHE[key] = img
        return img
    except Exception:
        return None

def get_logo_from_url(url: str, cache_key: str, size: int = 14):
    if Image is None or not url:
        return None
    key = (f"URL:{cache_key}".upper(), size)
    with _LOCK:
        exp = _URL_EXPIRY.get(key, 0)
        if key in _URL_CACHE and time.time() < exp:
            return _URL_CACHE[key]
    try:
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        from io import BytesIO
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        if img.width != size or img.height != size:
            img = img.resize((size, size), Image.LANCZOS)
        with _LOCK:
            _URL_CACHE[key] = img
            _URL_EXPIRY[key] = time.time() + URL_TTL
        return img
    except Exception:
        return None

def _remove_bg(img, tolerance: int = 38):
    """Background removal tuned for sports logos.

    Rules:
    - If image already has any transparency, keep it (assume proper PNG provided) to avoid destroying anti-aliased edges.
    - Otherwise perform a corner flood-fill (4 corners as seeds) and remove ONLY contiguous regions within tolerance.
      This avoids wiping interior colors similar to background.
    - Tolerance is sum of absolute RGB diffs (Manhattan distance).
    """
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return img
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')

    # Preserve images that already contain transparency
    if img.mode == 'RGBA':
        alpha = img.getchannel('A')
        # If any pixel fully transparent we assume author-supplied transparency is correct.
        if any(a == 0 for a in alpha.getdata()):
            return img  # Trust original
        # else treat as opaque RGBA -> treat like RGB by converting
        img = img.convert('RGB')

    w, h = img.size
    src = img.load()
    # Collect corner colors
    corners = [src[0,0], src[w-1,0], src[0,h-1], src[w-1,h-1]]
    # Use average corner color as baseline (helps with gradient corners)
    avg = tuple(sum(c[i] for c in corners)//4 for i in range(3))

    def similar(c):
        r,g,b = c
        return abs(r-avg[0]) + abs(g-avg[1]) + abs(b-avg[2]) <= tolerance

    visited = [[False]*w for _ in range(h)]
    q: Deque[Tuple[int,int]] = deque()
    # Seed corners
    for (cx, cy) in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]:
        if similar(src[cx,cy]):
            q.append((cx,cy))
            visited[cy][cx] = True

    transparent = set()
    while q:
        x,y = q.popleft()
        transparent.add((x,y))
        for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                if similar(src[nx,ny]):
                    visited[ny][nx] = True
                    q.append((nx,ny))
    # Build RGBA output, only removing flood area
    out = Image.new('RGBA', (w,h))
    dst = out.load()
    for y in range(h):
        for x in range(w):
            r,g,b = src[x,y][:3]
            if (x,y) in transparent:
                dst[x,y] = (0,0,0,0)
            else:
                dst[x,y] = (r,g,b,255)
    return out

_PROC_CACHE: Dict[Tuple[str, int, str, int], object] = {}
_BG_ALGO_VERSION = 2

def get_processed_logo(sport: str, team_abbr: str, *, url: Optional[str], size: int, remove_bg: bool) -> Optional[object]:
    """High-level accessor returning possibly background-removed, resized logo.

    Order: local cached asset -> remote fetch -> processing -> cache.
    """
    base_key = f"{sport}:{team_abbr}".upper()
    proc_key = (base_key, size, 'nobg' if remove_bg else 'raw', _BG_ALGO_VERSION)
    if proc_key in _PROC_CACHE:
        return _PROC_CACHE[proc_key]
    img = get_logo(sport, team_abbr, size=size)
    if img is None and url:
        img = get_logo_from_url(url, base_key, size=size)
    if img is None:
        return None
    if remove_bg:
        img = _remove_bg(img)
    _PROC_CACHE[proc_key] = img
    return img

__all__ = ["get_logo", "get_logo_from_url", "get_processed_logo"]

__all__ = ["get_logo"]
