"""
Playlist management and synchronization for YouTube-TUI.
Supports:
1. Fetching & synchronizing user playlists created on YouTube (FEplaylist_aggregation).
2. Creating custom local playlists.
3. Adding videos to custom playlists or synchronized YouTube playlists (with cloud sync via Innertube edit_playlist).
"""

import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from youtubetui.auth import CONFIG_DIR, get_auth_headers, is_authenticated

SYNCED_PLAYLISTS_FILE = CONFIG_DIR / "synced_playlists.json"
CUSTOM_PLAYLISTS_FILE = CONFIG_DIR / "custom_playlists.json"
BROWSE_URL = "https://www.youtube.com/youtubei/v1/browse"
EDIT_PLAYLIST_URL = "https://www.youtube.com/youtubei/v1/browse/edit_playlist"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


def _load_custom_data() -> Dict[str, Any]:
    if not CUSTOM_PLAYLISTS_FILE.exists():
        return {"playlists": {}, "additions": {}}
    try:
        data = json.loads(CUSTOM_PLAYLISTS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"playlists": {}, "additions": {}}
        if "playlists" not in data:
            data["playlists"] = {}
        if "additions" not in data:
            data["additions"] = {}
        return data
    except Exception:
        return {"playlists": {}, "additions": {}}


def _save_custom_data(data: Dict[str, Any]) -> None:
    try:
        CUSTOM_PLAYLISTS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def fetch_synced_youtube_playlists() -> List[Dict[str, Any]]:
    """
    Fetches the authenticated user's YouTube playlists directly from Innertube.
    Parses both modern lockupViewModel grids and classic playlistRenderers.
    Caches results locally.
    """
    auth_headers = get_auth_headers()
    if not auth_headers:
        # Fall back to cached synced playlists if not authenticated or offline
        return _load_cached_synced_playlists()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }
    headers.update(auth_headers)

    req = urllib.request.Request(
        BROWSE_URL,
        headers=headers,
        data=json.dumps({
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "en", "gl": "US"}},
            "browseId": "FEplaylist_aggregation"
        }).encode()
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            playlists = _extract_playlists_from_innertube(data)
            if playlists:
                try:
                    SYNCED_PLAYLISTS_FILE.write_text(json.dumps(playlists, indent=2), encoding="utf-8")
                except Exception:
                    pass
                return playlists
    except Exception:
        pass

    return _load_cached_synced_playlists()


def _load_cached_synced_playlists() -> List[Dict[str, Any]]:
    if not SYNCED_PLAYLISTS_FILE.exists():
        return []
    try:
        return json.loads(SYNCED_PLAYLISTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _extract_playlists_from_innertube(data: Any) -> List[Dict[str, Any]]:
    results = []
    seen_ids = set()

    def search_tree(obj: Any):
        if isinstance(obj, dict):
            # Modern lockupViewModel
            if "lockupViewModel" in obj:
                lv = obj["lockupViewModel"]
                cid = lv.get("contentId")
                ctype = lv.get("contentType", "")
                if cid and ("PLAYLIST" in ctype or cid.startswith("PL") or cid in ("WL", "LL")):
                    if cid not in seen_ids:
                        title = lv.get("metadata", {}).get("lockupMetadataViewModel", {}).get("title", {}).get("content", "")
                        thumb = ""
                        try:
                            thumb = lv["contentImage"]["collectionThumbnailViewModel"]["primaryThumbnail"]["thumbnailViewModel"]["image"]["sources"][-1]["url"]
                        except Exception:
                            pass
                        count_str = ""
                        try:
                            badges = lv["contentImage"]["collectionThumbnailViewModel"]["primaryThumbnail"]["thumbnailViewModel"]["overlays"]
                            for o in badges:
                                b_list = o.get("thumbnailOverlayBadgeViewModel", {}).get("thumbnailBadges", [])
                                for b in b_list:
                                    txt = b.get("thumbnailBadgeViewModel", {}).get("text")
                                    if txt:
                                        count_str = txt
                        except Exception:
                            pass
                        seen_ids.add(cid)
                        results.append({
                            "id": cid,
                            "title": title or f"Playlist {cid}",
                            "channel": "YouTube",
                            "duration": count_str or "Playlist",
                            "thumbnail": thumb,
                            "type": "playlist",
                            "url": f"https://www.youtube.com/playlist?list={cid}",
                            "is_synced": True,
                            "is_custom": False,
                            "description": f"YouTube Playlist • {count_str or 'Synced'}"
                        })

            # Classic gridPlaylistRenderer or playlistRenderer
            elif "gridPlaylistRenderer" in obj:
                gp = obj["gridPlaylistRenderer"]
                pid = gp.get("playlistId")
                if pid and pid not in seen_ids:
                    title = ""
                    if "title" in gp:
                        if "runs" in gp["title"]:
                            title = "".join(r.get("text", "") for r in gp["title"]["runs"])
                        elif "simpleText" in gp["title"]:
                            title = gp["title"]["simpleText"]
                    count_str = ""
                    if "videoCountShortText" in gp:
                        if "runs" in gp["videoCountShortText"]:
                            count_str = "".join(r.get("text", "") for r in gp["videoCountShortText"]["runs"])
                        elif "simpleText" in gp["videoCountShortText"]:
                            count_str = gp["videoCountShortText"]["simpleText"]
                    thumb = ""
                    try:
                        thumb = gp["thumbnail"]["thumbnails"][-1]["url"]
                    except Exception:
                        pass
                    seen_ids.add(pid)
                    results.append({
                        "id": pid,
                        "title": title or f"Playlist {pid}",
                        "channel": "YouTube",
                        "duration": count_str or "Playlist",
                        "thumbnail": thumb,
                        "type": "playlist",
                        "url": f"https://www.youtube.com/playlist?list={pid}",
                        "is_synced": True,
                        "is_custom": False,
                        "description": f"YouTube Playlist • {count_str or 'Synced'}"
                    })

            for v in obj.values():
                search_tree(v)
        elif isinstance(obj, list):
            for item in obj:
                search_tree(item)

    search_tree(data)
    return results


def get_custom_playlists() -> List[Dict[str, Any]]:
    """Returns all custom local playlists formatted as feed items."""
    data = _load_custom_data()
    playlists = []
    for pid, p in data.get("playlists", {}).items():
        count = len(p.get("videos", []))
        playlists.append({
            "id": pid,
            "title": p.get("title", "Untitled Playlist"),
            "channel": "Custom / Local",
            "duration": f"{count} video{'s' if count != 1 else ''}",
            "thumbnail": p.get("thumbnail", ""),
            "type": "playlist",
            "url": f"custom://playlist/{pid}",
            "is_synced": False,
            "is_custom": True,
            "description": p.get("description") or f"Custom YouTube TUI Playlist • {count} videos"
        })
    return playlists


def get_all_user_playlists(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Returns both custom local playlists and synchronized YouTube playlists.
    Custom playlists appear first, followed by synced YouTube playlists.
    """
    custom = get_custom_playlists()
    if force_refresh or not SYNCED_PLAYLISTS_FILE.exists():
        synced = fetch_synced_youtube_playlists()
    else:
        synced = _load_cached_synced_playlists()
        if not synced and is_authenticated():
            synced = fetch_synced_youtube_playlists()

    # Prepend custom playlists
    return custom + synced


def create_custom_playlist(title: str, description: str = "") -> Dict[str, Any]:
    """Creates a new custom local playlist."""
    clean_title = title.strip()
    if not clean_title:
        clean_title = "My Playlist"

    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", clean_title.lower()).strip("_")
    pid = f"custom_{slug}_{int(time.time())}"

    data = _load_custom_data()
    new_entry = {
        "id": pid,
        "title": clean_title,
        "description": description or f"Custom playlist '{clean_title}'",
        "created_at": int(time.time()),
        "thumbnail": "",
        "videos": []
    }
    data["playlists"][pid] = new_entry
    _save_custom_data(data)

    return {
        "id": pid,
        "title": clean_title,
        "channel": "Custom / Local",
        "duration": "0 videos",
        "thumbnail": "",
        "type": "playlist",
        "url": f"custom://playlist/{pid}",
        "is_synced": False,
        "is_custom": True,
        "description": new_entry["description"]
    }


def add_video_to_playlist(playlist_id: str, video: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Adds a video to either a custom playlist or a synchronized YouTube playlist.
    If the target is a YouTube playlist and the session is authenticated,
    it also syncs the addition to YouTube via Innertube edit_playlist.
    """
    if not video or video.get("type") != "video":
        return False, "Selected item is not a valid video"

    vid = video.get("id") or video.get("video_id")
    url = video.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
    if not vid and url and "v=" in url:
        vid = url.split("v=")[1].split("&")[0]

    video_entry = {
        "id": vid or url,
        "title": video.get("title", "Untitled Video"),
        "channel": video.get("channel", "Unknown Channel"),
        "channel_id": video.get("channel_id", ""),
        "duration": video.get("duration", ""),
        "thumbnail": video.get("thumbnail", ""),
        "url": url,
        "description": video.get("description", ""),
        "type": "video",
        "added_at": int(time.time())
    }

    data = _load_custom_data()

    # Case 1: Custom local playlist
    if playlist_id in data.get("playlists", {}):
        pl = data["playlists"][playlist_id]
        existing = [v for v in pl.get("videos", []) if v.get("id") == video_entry["id"] or v.get("url") == video_entry["url"]]
        if existing:
            return True, f"Video already in custom playlist '{pl.get('title')}'"

        pl["videos"].append(video_entry)
        if not pl.get("thumbnail") and video_entry.get("thumbnail"):
            pl["thumbnail"] = video_entry["thumbnail"]
        _save_custom_data(data)
        return True, f"[+] Added to custom playlist '{pl.get('title')}'"

    # Case 2: Synchronized YouTube playlist (or Watch Later 'WL')
    # Save locally to additions
    if "additions" not in data:
        data["additions"] = {}
    if playlist_id not in data["additions"]:
        data["additions"][playlist_id] = []

    existing_local = [v for v in data["additions"][playlist_id] if v.get("id") == video_entry["id"] or v.get("url") == video_entry["url"]]
    if not existing_local:
        data["additions"][playlist_id].insert(0, video_entry)
        _save_custom_data(data)

    # Cloud synchronization with YouTube if authenticated
    cloud_synced = False
    if vid and is_authenticated():
        auth_headers = get_auth_headers()
        if auth_headers:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9"
            }
            headers.update(auth_headers)
            payload = {
                "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "en", "gl": "US"}},
                "playlistId": playlist_id,
                "actions": [
                    {
                        "action": "ACTION_ADD_VIDEO",
                        "addedVideoId": vid
                    }
                ]
            }
            try:
                req = urllib.request.Request(
                    EDIT_PLAYLIST_URL,
                    headers=headers,
                    data=json.dumps(payload).encode()
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    res = json.load(resp)
                    if res.get("status") == "STATUS_SUCCEEDED":
                        cloud_synced = True
            except Exception:
                pass

    status_suffix = " (Synced to YouTube)" if cloud_synced else " (Saved locally)"
    return True, f"[+] Added video to playlist {playlist_id}{status_suffix}"


def get_playlist_videos_with_local(playlist_id: str) -> List[Dict[str, Any]]:
    """
    Returns all videos for a playlist:
    - If custom: returns stored videos.
    - If YouTube playlist: queries YouTube and merges with local additions.
    """
    data = _load_custom_data()

    # Custom playlist (handles raw id or custom:// URI)
    clean_id = playlist_id.replace("custom://playlist/", "") if playlist_id else ""
    if clean_id in data.get("playlists", {}):
        return list(data["playlists"][clean_id].get("videos", []))
    if playlist_id in data.get("playlists", {}):
        return list(data["playlists"][playlist_id].get("videos", []))

    # Synced YouTube playlist: fetch from api and prepend local additions
    from youtubetui.api import get_playlist_videos
    yt_videos = get_playlist_videos(playlist_id)

    local_adds = data.get("additions", {}).get(playlist_id, [])
    if not local_adds:
        return yt_videos

    seen_ids = {v.get("id") for v in yt_videos if v.get("id")}
    combined = []
    for item in local_adds:
        if item.get("id") not in seen_ids:
            combined.append(item)
            seen_ids.add(item.get("id"))

    combined.extend(yt_videos)
    return combined
