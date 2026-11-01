"""
MPV media player integration and URL clipboard dispatcher.
Interfaces with our smart deduplicating MPV wrapper to eliminate
URL bloat, prevent redundant windows in Hyprland, and stream VP9+Opus smoothly.
"""

import json
import os
import shutil
import socket
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from youtubetui.auth import get_cookies_file
from youtubetui.history import record_watched_video

def get_mpv_path() -> str:
    """Finds the best available mpv binary, prioritizing our smart wrapper."""
    local_bin = Path.home() / ".local" / "bin" / "mpv"
    if local_bin.exists() and os.access(local_bin, os.X_OK):
        return str(local_bin)
    
    repo_bin = Path(__file__).parent.parent / "bin" / "mpv"
    if repo_bin.exists() and os.access(repo_bin, os.X_OK):
        return str(repo_bin)
    
    system_mpv = shutil.which("mpv")
    if system_mpv:
        return system_mpv
    
    return "/usr/bin/mpv"

def play_url(url: str, audio_only: bool = False, video_item: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Launches MPV asynchronously with the target YouTube URL
    and records the item in local watch history.
    Returns (success, message).
    """
    if not url:
        return False, "No URL specified"

    if video_item:
        record_watched_video(video_item)
    else:
        record_watched_video({"url": url, "type": "video"})
    
    mpv_bin = get_mpv_path()
    cmd = [mpv_bin, "--input-ipc-server=/tmp/mpv-socket"]
    if audio_only:
        cmd.extend(["--no-video", "--ytdl-format=bestaudio/best"])
    
    cookies_path = get_cookies_file()
    if cookies_path:
        cmd.append(f"--ytdl-raw-options=cookies={cookies_path}")

    # For live streams, ensure continuous buffer playback without stalling or skipping
    if video_item and (video_item.get("is_live") or video_item.get("duration") == "LIVE"):
        cmd.extend(["--cache-pause=no", "--demuxer-readahead-secs=10"])

    cmd.append(url)

    try:
        subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        mode_str = "Audio" if audio_only else "Video"
        return True, f"Dispatched {mode_str} playback to MPV"
    except Exception as e:
        return False, f"Failed to launch MPV: {e}"

def enqueue_url(url: str, title: str = "", video_item: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Enqueues the URL into a running MPV instance via IPC unix socket.
    If MPV is not currently running or the socket fails, starts a fresh playback instance.
    """
    if not url:
        return False, "No URL specified"

    if video_item:
        record_watched_video(video_item)
    else:
        record_watched_video({"url": url, "type": "video"})

    ipc_socket = Path("/tmp/mpv-socket")
    if ipc_socket.exists():
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(1.0)
                client.connect(str(ipc_socket))
                cmd = json.dumps({"command": ["loadfile", url, "append-play"]}) + "\n"
                client.sendall(cmd.encode("utf-8"))
                if title:
                    osd_cmd = json.dumps({"command": ["show-text", f"Queued: {title}", 3000]}) + "\n"
                    client.sendall(osd_cmd.encode("utf-8"))
            display_title = title or url
            return True, f"Enqueued to MPV: {display_title}"
        except (socket.error, OSError):
            pass

    # Fallback to direct play if socket is inactive
    return play_url(url, audio_only=False, video_item=video_item)

def download_url(url: str, audio_only: bool = False, video_item: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Spawns background yt-dlp process to download video or extract audio,
    and sends desktop notifications on start and finish.
    """
    if not url:
        return False, "No URL specified"

    target_dir = Path.home() / ("Music" if audio_only else "Downloads")
    target_dir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(target_dir / "%(title)s.%(ext)s")

    cmd = ["yt-dlp", "--no-playlist", "-o", out_tmpl]
    if audio_only:
        cmd.extend(["-x", "--audio-format", "mp3"])
    else:
        cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])

    cookies_path = get_cookies_file()
    if cookies_path:
        cmd.extend(["--cookies", cookies_path])

    cmd.append(url)
    display_title = (video_item.get("title") if video_item else "") or url

    def _run_download():
        media_label = "Audio (MP3)" if audio_only else "Video"
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", "-a", "YouTube-TUI", f"Downloading {media_label}", display_title], check=False)
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if shutil.which("notify-send"):
            if proc.returncode == 0:
                subprocess.run(["notify-send", "-a", "YouTube-TUI", f"Downloaded {media_label}", display_title], check=False)
            else:
                subprocess.run(["notify-send", "-a", "YouTube-TUI", "Download Failed", display_title], check=False)

    t = threading.Thread(target=_run_download, daemon=True)
    t.start()

    media_label = "Audio (MP3)" if audio_only else "Video"
    return True, f"Started {media_label} download to ~/{target_dir.name}/: {display_title}"

def copy_to_clipboard(text: str) -> Tuple[bool, str]:
    """Copies the text to the Wayland/X11 clipboard."""
    if not text:
        return False, "Nothing to copy"
    
    wl_copy = shutil.which("wl-copy")
    if wl_copy:
        try:
            p = subprocess.run([wl_copy], input=text.encode(), timeout=2)
            if p.returncode == 0:
                return True, "Copied URL to clipboard"
        except Exception:
            pass
    
    xclip = shutil.which("xclip")
    if xclip:
        try:
            p = subprocess.run([xclip, "-selection", "clipboard"], input=text.encode(), timeout=2)
            if p.returncode == 0:
                return True, "Copied URL to clipboard"
        except Exception:
            pass

    return False, "Clipboard utility (wl-copy/xclip) not available"
