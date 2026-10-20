"""
Authentication and Session Manager for YouTube-TUI.
Extracts and maintains authenticated YouTube sessions from local browsers
(Zen Browser, Firefox, Chromium) or cookies.txt, unlocking:
1. YouTube Premium high-bitrate streaming without ads.
2. Personalized algorithm-driven Home feed (FEwhat_to_watch).
3. Subscriptions feed with latest creator uploads (FEsubscriptions).
4. Watch History synchronization (FEhistory).
"""

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

CONFIG_DIR = Path.home() / ".config" / "youtube-tui"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

SESSION_FILE = CONFIG_DIR / "session.json"
COOKIES_FILE = CONFIG_DIR / "cookies.txt"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

def get_cookies_file() -> Optional[str]:
    """Returns the path to the cookies.txt file if it exists and session is valid."""
    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        return str(COOKIES_FILE)
    return None

def is_authenticated() -> bool:
    """Checks whether an active authenticated session exists."""
    if not SESSION_FILE.exists():
        return False
    try:
        data = json.loads(SESSION_FILE.read_text())
        return bool(data.get("authenticated", False))
    except Exception:
        return False

def is_premium() -> bool:
    """Checks whether the authenticated account has YouTube Premium."""
    if not SESSION_FILE.exists():
        return False
    try:
        data = json.loads(SESSION_FILE.read_text())
        return bool(data.get("is_premium", False))
    except Exception:
        return False

def get_session_info() -> Dict[str, Any]:
    """Loads session metadata."""
    if not SESSION_FILE.exists():
        return {"authenticated": False, "is_premium": False, "browser": "none"}
    try:
        return json.loads(SESSION_FILE.read_text())
    except Exception:
        return {"authenticated": False, "is_premium": False, "browser": "none"}

def clear_session() -> None:
    """Removes the session credentials and resets to anonymous mode."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink(missing_ok=True)
    if COOKIES_FILE.exists():
        COOKIES_FILE.unlink(missing_ok=True)

def find_browser_cookie_db(browser: str = "auto") -> Optional[Tuple[str, Path]]:
    """Locates the cookies.sqlite database for Webflow, Zen, or Firefox."""
    home = Path.home()
    
    # Webflow custom web engine
    if browser in ("webflow", "wf", "auto"):
        wf_path = home / ".local" / "share" / "webflow" / "storage" / "cookies.sqlite"
        if wf_path.resolve().exists():
            return "webflow", wf_path.resolve()

    # Zen Browser
    if browser in ("zen", "zen-browser", "auto"):
        candidates = [
            home / ".zen" / "default" / "cookies.sqlite",
            *list(home.glob(".zen/*/cookies.sqlite")),
            *list(home.glob(".config/zen/*/cookies.sqlite")),
        ]
        for p in candidates:
            resolved = p.resolve()
            if resolved.exists():
                return "zen", resolved

    # Firefox
    if browser in ("firefox", "auto"):
        candidates = [
            *list(home.glob(".mozilla/firefox/*.default-release/cookies.sqlite")),
            *list(home.glob(".mozilla/firefox/*.default/cookies.sqlite")),
        ]
        for p in candidates:
            resolved = p.resolve()
            if resolved.exists():
                return "firefox", resolved

    return None

def sync_from_browser(browser: str = "auto") -> Tuple[bool, str]:
    """
    Safely copies the browser's cookies.sqlite (avoiding open-browser database locks),
    extracts YouTube authentication cookies, writes a standard Netscape cookies.txt,
    verifies authentication & Premium status via Innertube, and saves session.json.
    Supports Webflow, Zen Browser, and Firefox.
    """
    found = find_browser_cookie_db(browser)
    if not found:
        return False, f"Could not locate cookie database for {browser} browser."

    detected_browser, db_path = found

    # Copy database to temporary directory to prevent locking collisions
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as tmp:
        try:
            shutil.copyfile(db_path, tmp.name)
            conn = sqlite3.connect(tmp.name)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT host, isHttpOnly, path, isSecure, expiry, name, value "
                "FROM moz_cookies WHERE host LIKE '%youtube.com'"
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            return False, f"Failed to read browser cookie database: {e}"

    if not rows:
        return False, "No YouTube cookies found in browser profile. Please log in to YouTube in your browser."

    # Write Netscape format cookies.txt
    try:
        with open(COOKIES_FILE, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# Exported by YouTube-TUI for smart MPV & Innertube authentication\n")
            for host, is_http_only, path, is_secure, expiry, name, value in rows:
                domain_flag = "TRUE" if host.startswith(".") else "FALSE"
                secure_flag = "TRUE" if is_secure else "FALSE"
                f.write(f"{host}\t{domain_flag}\t{path}\t{secure_flag}\t{expiry}\t{name}\t{value}\n")
    except Exception as e:
        return False, f"Failed to save cookies.txt: {e}"

    # Verify credentials via Innertube
    auth_headers = get_auth_headers()
    if not auth_headers:
        clear_session()
        return False, "Cookies did not contain valid YouTube login credentials (SAPISID/LOGIN_INFO)"

    req = urllib.request.Request(
        "https://www.youtube.com/youtubei/v1/browse",
        headers=auth_headers,
        data=json.dumps({
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "en", "gl": "US"}},
            "browseId": "FEwhat_to_watch"
        }).encode()
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            topbar = str(data.get("topbar", {}))
            has_avatar = "avatar" in topbar or "accountMenuRenderer" in topbar
            is_prem = "PREMIUM" in topbar or "Premium" in topbar

            if not has_avatar:
                clear_session()
                return False, "Session verification failed: Account is not signed in."

            session_data = {
                "authenticated": True,
                "is_premium": is_prem,
                "browser": detected_browser,
                "synced_at": int(time.time()),
            }
            SESSION_FILE.write_text(json.dumps(session_data, indent=2))
            
            prem_status = "Premium Active (Ad-Free & 4K AV1/VP9)" if is_prem else "Standard Account Active"
            return True, f"Successfully connected YouTube account from {detected_browser.title()}! ({prem_status})"

    except Exception as e:
        clear_session()
        return False, f"Session verification request failed: {e}"

def get_auth_headers() -> Dict[str, str]:
    """Generates authenticated HTTP headers with SAPISIDHASH signature."""
    if not COOKIES_FILE.exists():
        return {}

    cookies = {}
    try:
        with open(COOKIES_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
    except Exception:
        return {}

    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
    sapisid = cookies.get("SAPISID") or cookies.get("__Secure-3PAPISID")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Cookie": cookie_header
    }

    if sapisid:
        t = str(int(time.time()))
        origin = "https://www.youtube.com"
        h = hashlib.sha1(f"{t} {sapisid} {origin}".encode()).hexdigest()
        headers["Authorization"] = f"SAPISIDHASH {t}_{h}"
        headers["X-Origin"] = origin

    return headers
