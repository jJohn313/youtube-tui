"""
Watch History manager for YouTube-TUI.
Maintains a local persistent log of watched videos and integrates
with YouTube's cloud watch history.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List
from youtubetui.auth import CONFIG_DIR

HISTORY_FILE = CONFIG_DIR / "watch_history.json"
MAX_HISTORY_ENTRIES = 500


def record_watched_video(item: Dict[str, Any]) -> None:
    """
    Records or updates a video in local watch history upon playback.
    Places the newly watched item at the top of the history stack.
    """
    if not item or item.get("type") != "video":
        return

    vid = item.get("id") or item.get("video_id")
    url = item.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
    if not vid and url and "v=" in url:
        vid = url.split("v=")[1].split("&")[0]

    record = {
        "id": vid or url,
        "title": item.get("title", "Untitled Video"),
        "channel": item.get("channel", "Unknown Channel"),
        "channel_id": item.get("channel_id", ""),
        "duration": item.get("duration", ""),
        "thumbnail": item.get("thumbnail", ""),
        "url": url,
        "description": item.get("description", ""),
        "watched_at": int(time.time()),
        "watched_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "video"
    }

    history = get_local_watch_history()
    # Filter out previous entry if already present (jump to top)
    history = [h for h in history if (h.get("id") != record["id"] and h.get("url") != record["url"])]
    history.insert(0, record)
    if len(history) > MAX_HISTORY_ENTRIES:
        history = history[:MAX_HISTORY_ENTRIES]

    try:
        HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_local_watch_history() -> List[Dict[str, Any]]:
    """Returns local watch history list, newest first."""
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def clear_local_watch_history() -> None:
    """Clears local watch history."""
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink(missing_ok=True)
