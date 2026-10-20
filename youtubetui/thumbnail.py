"""
Thumbnail fetching and true-color terminal graphics rendering via chafa.
Caches downloaded image files to ~/.cache/youtube-tui/thumbnails/
and persists rendered ANSI buffers on disk and in memory for zero-latency UI scrolling.
"""

import asyncio
import hashlib
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Optional
from rich.text import Text

CACHE_DIR = Path.home() / ".cache" / "youtube-tui" / "thumbnails"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory LRU cache: key -> pre-parsed rich.text.Text object
_RENDER_CACHE: Dict[str, Text] = {}
_MAX_CACHE_SIZE = 150
_SEMAPHORES: Dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = {}

def get_render_semaphore() -> asyncio.Semaphore:
    """Limits concurrent background thumbnail processing to preserve UI fluidity."""
    loop = asyncio.get_running_loop()
    if loop not in _SEMAPHORES:
        _SEMAPHORES[loop] = asyncio.Semaphore(3)
    return _SEMAPHORES[loop]

def _get_cache_path(url: str, item_id: str) -> Path:
    if item_id:
        safe_id = "".join(c for c in item_id if c.isalnum() or c in ("-", "_"))
        return CACHE_DIR / f"{safe_id}.jpg"
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{h}.jpg"

def _get_ansi_cache_path(url: str, item_id: str, width: int, height: int) -> Path:
    if item_id:
        safe_id = "".join(c for c in item_id if c.isalnum() or c in ("-", "_"))
        return CACHE_DIR / f"{safe_id}_{width}x{height}.ansi"
    h = hashlib.sha256(f"{url}:{width}x{height}".encode()).hexdigest()[:16]
    return CACHE_DIR / f"{h}_{width}x{height}.ansi"

def render_fallback_placeholder(width: int, height: int, title: str = "No Preview") -> str:
    """Generates an aesthetic placeholder matching the Lain theme."""
    lines = []
    lines.append("╭" + "─" * (width - 2) + "╮")
    pad_top = max(0, (height - 3) // 2)
    for _ in range(pad_top):
        lines.append("│" + " " * (width - 2) + "│")
    
    label = f" {title[:max(1, width - 6)]} "
    pad_left = max(0, (width - 2 - len(label)) // 2)
    pad_right = max(0, width - 2 - len(label) - pad_left)
    lines.append("│" + " " * pad_left + label + " " * pad_right + "│")
    
    pad_bot = max(0, height - 3 - pad_top)
    for _ in range(pad_bot):
        lines.append("│" + " " * (width - 2) + "│")
    lines.append("╰" + "─" * (width - 2) + "╯")
    return "\n".join(lines[:height])

def sync_render_thumbnail(url: str, item_id: str = "", width: int = 28, height: int = 7) -> Text:
    """Synchronously downloads, executes chafa, and parses Rich Text off the main thread."""
    if not url:
        return Text.from_ansi(render_fallback_placeholder(width, height, "No Thumbnail"))
    
    cache_key = f"{item_id}:{url}:{width}x{height}"
    if cache_key in _RENDER_CACHE:
        return _RENDER_CACHE[cache_key]

    # Check on-disk rendered ANSI cache for instantaneous reload
    ansi_cache = _get_ansi_cache_path(url, item_id, width, height)
    if ansi_cache.exists() and ansi_cache.stat().st_size > 0:
        try:
            rendered = ansi_cache.read_text(encoding="utf-8")
            parsed = Text.from_ansi(rendered)
            if len(_RENDER_CACHE) >= _MAX_CACHE_SIZE:
                _RENDER_CACHE.pop(next(iter(_RENDER_CACHE)))
            _RENDER_CACHE[cache_key] = parsed
            return parsed
        except Exception:
            pass

    chafa_bin = shutil.which("chafa") or "/home/john/.local/bin/chafa"
    if not os.path.exists(chafa_bin):
        return Text.from_ansi(render_fallback_placeholder(width, height, "chafa missing"))

    cache_file = _get_cache_path(url, item_id)
    if not cache_file.exists() or cache_file.stat().st_size == 0:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                cache_file.write_bytes(data)
        except Exception:
            return Text.from_ansi(render_fallback_placeholder(width, height, "Download failed"))

    # Execute chafa to convert JPEG into true-color sextant/quadrant ANSI
    # Note: --probe=off and stdin=DEVNULL prevent chafa from probing /dev/tty
    cmd = [
        chafa_bin,
        "--probe=off",
        "--format=symbols",
        "--symbols=sextant+quad+half",
        "--colors=truecolor",
        f"--size={width}x{height}",
        str(cache_file)
    ]

    try:
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            rendered = res.stdout
            try:
                ansi_cache.write_text(rendered, encoding="utf-8")
            except Exception:
                pass

            parsed = Text.from_ansi(rendered)
            if len(_RENDER_CACHE) >= _MAX_CACHE_SIZE:
                _RENDER_CACHE.pop(next(iter(_RENDER_CACHE)))
            _RENDER_CACHE[cache_key] = parsed
            return parsed
    except Exception:
        pass

    return Text.from_ansi(render_fallback_placeholder(width, height, "Render error"))

async def async_render_thumbnail(url: str, item_id: str = "", width: int = 28, height: int = 7) -> Text:
    """Asynchronous wrapper running chafa in a background thread with concurrency limiting."""
    cache_key = f"{item_id}:{url}:{width}x{height}"
    if cache_key in _RENDER_CACHE:
        return _RENDER_CACHE[cache_key]

    sem = get_render_semaphore()
    async with sem:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, sync_render_thumbnail, url, item_id, width, height)
