"""
MPV media player integration and URL clipboard dispatcher.
Interfaces with our smart deduplicating MPV wrapper to eliminate
URL bloat, prevent redundant windows in Hyprland, and stream VP9+Opus smoothly.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple
from youtubetui.auth import get_cookies_file

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

def play_url(url: str, audio_only: bool = False) -> Tuple[bool, str]:
    """
    Launches MPV asynchronously with the target YouTube URL.
    Returns (success, message).
    """
    if not url:
        return False, "No URL specified"
    
    mpv_bin = get_mpv_path()
    cmd = [mpv_bin]
    if audio_only:
        cmd.extend(["--no-video", "--ytdl-format=bestaudio/best"])
    
    cookies_path = get_cookies_file()
    if cookies_path:
        cmd.append(f"--ytdl-raw-options=cookies={cookies_path}")

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
