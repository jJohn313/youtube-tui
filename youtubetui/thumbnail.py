"""
Thumbnail fetching and true-color terminal graphics rendering via chafa.
Caches downloaded image files to ~/.cache/youtube-tui/thumbnails/
and keeps rendered ANSI buffers in memory for zero-latency scroll previews.
"""

import asyncio
import hashlib
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Optional

CACHE_DIR = Path.home() / ".cache" / "youtube-tui" / "thumbnails"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory LRU-like cache: key -> ANSI string
_RENDER_CACHE: Dict[str, str] = {}
_MAX_CACHE_SIZE = 120

def _get_cache_path(url: str, item_id: str) -> Path:
    if item_id:
        safe_id = "".join(c for c in item_id if c.isalnum() or c in ("-", "_"))
        return CACHE_DIR / f"{safe_id}.jpg"
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{h}.jpg"

def render_fallback_placeholder(width: int, height: int, title: str = "No Preview") -> str:
    """Generates an aesthetic placeholder matching the Lain theme."""
    lines = []
    lines.append("╭" + "─" * (width - 2) + "╮")
    pad_top = (height - 3) // 2
    for _ in range(pad_top):
        lines.append("│" + " " * (width - 2) + "│")
    
    label = f" {title[:width - 6]} "
    pad_left = (width - 2 - len(label)) // 2
    pad_right = width - 2 - len(label) - pad_left
    lines.append("│" + " " * pad_left + label + " " * pad_right + "│")
    
    pad_bot = height - 3 - pad_top
    for _ in range(pad_bot):
        lines.append("│" + " " * (width - 2) + "│")
    lines.append("╰" + "─" * (width - 2) + "╯")
    return "\n".join(lines)

def sync_render_thumbnail(url: str, item_id: str = "", width: int = 42, height: int = 16) -> str:
    """Synchronously downloads and executes chafa for a thumbnail image."""
    if not url:
        return render_fallback_placeholder(width, height, "No Thumbnail")
    
    cache_key = f"{item_id}:{url}:{width}x{height}"
    if cache_key in _RENDER_CACHE:
        return _RENDER_CACHE[cache_key]

    chafa_bin = shutil.which("chafa") or "/home/john/.local/bin/chafa"
    if not os.path.exists(chafa_bin):
        return render_fallback_placeholder(width, height, "chafa not installed")

    cache_file = _get_cache_path(url, item_id)
    if not cache_file.exists() or cache_file.stat().st_size == 0:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
                cache_file.write_bytes(data)
        except Exception:
            return render_fallback_placeholder(width, height, "Download failed")

    # Execute chafa to convert JPEG into true-color half-block ANSI
    # Note: --probe=off and stdin=DEVNULL are mandatory to prevent chafa from probing /dev/tty
    # and leaking escape query responses into the terminal stdin / search input!
    cmd = [
        chafa_bin,
        "--probe=off",
        "--format=symbols",
        "--symbols=vhalf",
        "--colors=truecolor",
        f"--size={width}x{height}",
        str(cache_file)
    ]

    try:
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            rendered = res.stdout
            if len(_RENDER_CACHE) >= _MAX_CACHE_SIZE:
                _RENDER_CACHE.pop(next(iter(_RENDER_CACHE)))
            _RENDER_CACHE[cache_key] = rendered
            return rendered
    except Exception:
        pass

    return render_fallback_placeholder(width, height, "Render error")

async def async_render_thumbnail(url: str, item_id: str = "", width: int = 42, height: int = 16) -> str:
    """Asynchronous wrapper running chafa in a background thread."""
    cache_key = f"{item_id}:{url}:{width}x{height}"
    if cache_key in _RENDER_CACHE:
        return _RENDER_CACHE[cache_key]
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, sync_render_thumbnail, url, item_id, width, height)
