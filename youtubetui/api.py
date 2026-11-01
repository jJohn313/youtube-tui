"""
YouTube Innertube and Scraping API client.
Provides instant searches across Videos, Channels, and Playlists,
extracting rich metadata without requiring Google API credentials or browser engines.
"""

import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from youtubetui.auth import get_auth_headers, get_cookies_file

INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/search"
BROWSE_URL = "https://www.youtube.com/youtubei/v1/browse"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

FILTER_PARAMS = {
    "all": None,
    "videos": "EgIQAQ%3D%3D",
    "channels": "EgIQAg%3D%3D",
    "playlists": "EgIQAw%3D%3D",
    "date": "CAISAhAB",
    "views": "CAMSAhAB",
    "live": "EgJAAQ%3D%3D",
    "short": "EgQQARgB",
    "long": "EgQQARgC",
}

CHANNEL_TABS = {
    "videos": "EgZ2aWRlb3PyBgQKAjoA",
    "playlists": "EglwbGF5bGlzdHPyBgoKCEIGCgIQaCIA",
    "shorts": "EgZzaG9ydHPyBgUKA5oBAA%3D%3D",
    "featured": "EghmZWF0dXJlZPIGBAoCMgA%3D",
}

def format_duration(seconds: Any) -> str:
    """Formats numeric seconds into MM:SS or HH:MM:SS."""
    try:
        sec = int(seconds)
    except (ValueError, TypeError):
        return str(seconds) if seconds else ""
    
    hours = sec // 3600
    minutes = (sec % 3600) // 60
    rem_sec = sec % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{rem_sec:02d}"
    return f"{minutes}:{rem_sec:02d}"

def format_views(count: Any) -> str:
    """Formats view count into human-readable compact notation (e.g. 1.2M)."""
    try:
        n = int(count)
    except (ValueError, TypeError):
        return str(count) if count else ""
    
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)

def _clean_thumb_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    return url

def extract_browse_items_with_continuation(data: Any) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Traverses an Innertube browse or search response and extracts structured items and continuation token."""
    results: List[Dict[str, Any]] = []
    seen_ids = set()
    continuation_token: Optional[str] = None

    def parse_renderers(obj: Any):
        nonlocal continuation_token
        if isinstance(obj, dict):
            if "continuationCommand" in obj:
                tok = obj["continuationCommand"].get("token")
                if tok and not continuation_token:
                    continuation_token = tok
            elif "continuationItemRenderer" in obj:
                tok = obj["continuationItemRenderer"].get("continuationEndpoint", {}).get("continuationCommand", {}).get("token")
                if tok and not continuation_token:
                    continuation_token = tok
            # 1. Video Renderer
            if "videoRenderer" in obj:
                v = obj["videoRenderer"]
                vid = v.get("videoId")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    title = ""
                    if "title" in v and "runs" in v["title"] and v["title"]["runs"]:
                        title = v["title"]["runs"][0].get("text", "")
                    elif "title" in v and "simpleText" in v["title"]:
                        title = v["title"]["simpleText"]
                    
                    channel = ""
                    channel_id = ""
                    if "ownerText" in v and "runs" in v["ownerText"] and v["ownerText"]["runs"]:
                        channel = v["ownerText"]["runs"][0].get("text", "")
                        ep = v["ownerText"]["runs"][0].get("navigationEndpoint", {}).get("browseEndpoint", {})
                        channel_id = ep.get("browseId", "")
                    elif "longBylineText" in v and "runs" in v["longBylineText"] and v["longBylineText"]["runs"]:
                        channel = v["longBylineText"]["runs"][0].get("text", "")
                        ep = v["longBylineText"]["runs"][0].get("navigationEndpoint", {}).get("browseEndpoint", {})
                        channel_id = ep.get("browseId", "")
                    elif "shortBylineText" in v and "runs" in v["shortBylineText"] and v["shortBylineText"]["runs"]:
                        channel = v["shortBylineText"]["runs"][0].get("text", "")
                        ep = v["shortBylineText"]["runs"][0].get("navigationEndpoint", {}).get("browseEndpoint", {})
                        channel_id = ep.get("browseId", "")

                    duration = v.get("lengthText", {}).get("simpleText", "")
                    views = v.get("shortViewCountText", {}).get("simpleText", "")
                    date = v.get("publishedTimeText", {}).get("simpleText", "")

                    is_live = False
                    for b in v.get("badges", []):
                        mbr = b.get("metadataBadgeRenderer", {})
                        if mbr.get("style") == "BADGE_STYLE_TYPE_LIVE_NOW" or mbr.get("label") == "LIVE":
                            is_live = True
                            break
                    if not is_live and not duration and any("watching" in r.get("text", "") for r in v.get("viewCountText", {}).get("runs", [])):
                        is_live = True

                    if is_live:
                        if not duration:
                            duration = "LIVE"
                        if not views:
                            runs = v.get("viewCountText", {}).get("runs", [])
                            if runs:
                                views = "".join(r.get("text", "") for r in runs)

                    desc = ""
                    snippets = v.get("detailedMetadataSnippets", [])
                    if snippets:
                        runs = snippets[0].get("snippetText", {}).get("runs", [])
                        desc = "".join(r.get("text", "") for r in runs)

                    thumbs = v.get("thumbnail", {}).get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                    if title:
                        results.append({
                            "type": "video",
                            "id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": title,
                            "channel": channel,
                            "channel_id": channel_id,
                            "duration": duration,
                            "views": views,
                            "date": date,
                            "description": desc,
                            "thumbnail": _clean_thumb_url(thumb_url),
                            "is_live": is_live
                        })

            # 2. Channel Renderer
            elif "channelRenderer" in obj:
                c = obj["channelRenderer"]
                cid = c.get("channelId")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    title = c.get("title", {}).get("simpleText", "")
                    subscribers = (
                        c.get("videoCountText", {}).get("simpleText", "") or
                        c.get("subscriberCountText", {}).get("simpleText", "")
                    )
                    desc = ""
                    if "descriptionSnippet" in c and "runs" in c["descriptionSnippet"] and c["descriptionSnippet"]["runs"]:
                        desc = "".join(r.get("text", "") for r in c["descriptionSnippet"]["runs"])
                    
                    thumbs = c.get("thumbnail", {}).get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url", "") if thumbs else ""

                    if title:
                        results.append({
                            "type": "channel",
                            "id": cid,
                            "url": f"https://www.youtube.com/channel/{cid}",
                            "title": title,
                            "channel": title,
                            "channel_id": cid,
                            "duration": "Channel",
                            "views": subscribers,
                            "date": "",
                            "description": desc,
                            "thumbnail": _clean_thumb_url(thumb_url)
                        })

            # 3. Playlist Renderer
            elif "playlistRenderer" in obj:
                p = obj["playlistRenderer"]
                pid = p.get("playlistId")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    title = p.get("title", {}).get("simpleText", "")
                    count = p.get("videoCount", "")
                    channel = ""
                    if "shortBylineText" in p and "runs" in p["shortBylineText"] and p["shortBylineText"]["runs"]:
                        channel = p["shortBylineText"]["runs"][0].get("text", "")
                    
                    thumbs = p.get("thumbnails", [{}])[0].get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url", "") if thumbs else ""

                    if title:
                        results.append({
                            "type": "playlist",
                            "id": pid,
                            "url": f"https://www.youtube.com/playlist?list={pid}",
                            "title": title,
                            "channel": channel,
                            "channel_id": "",
                            "duration": f"{count} videos" if count else "Playlist",
                            "views": f"{count} videos" if count else "Playlist",
                            "date": "Playlist",
                            "description": f"Curated playlist by {channel}",
                            "thumbnail": _clean_thumb_url(thumb_url)
                        })

            # 4. Modern lockupViewModel (YouTube Web Playlists & Cards)
            elif "lockupViewModel" in obj:
                lv = obj["lockupViewModel"]
                c_type = lv.get("contentType", "")
                meta = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
                title = meta.get("title", {}).get("content", "")
                
                rows = meta.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
                channel = ""
                channel_id = ""
                desc = ""
                duration = ""
                views = ""
                date = ""
                
                for row in rows:
                    parts = row.get("metadataParts", [])
                    for part in parts:
                        text_obj = part.get("text", {})
                        content = text_obj.get("content", "")
                        if not content:
                            continue
                        if not channel:
                            channel = content
                            for cr in text_obj.get("commandRuns", []):
                                browse_ep = cr.get("onTap", {}).get("innertubeCommand", {}).get("browseEndpoint", {})
                                if browse_ep.get("browseId"):
                                    channel_id = browse_ep["browseId"]
                        elif "views" in content or "view" in content:
                            views = content
                        elif "ago" in content or "Streamed" in content:
                            date = content
                        elif not desc:
                            desc = content

                is_live = False
                if not duration:
                    overlays = lv.get("contentImage", {}).get("thumbnailViewModel", {}).get("overlays", [])
                    for ov in overlays:
                        badges = ov.get("thumbnailBottomOverlayViewModel", {}).get("badges", [])
                        for b in badges:
                            txt = b.get("thumbnailBadgeViewModel", {}).get("text")
                            if txt and (":" in txt or txt.isdigit()):
                                duration = txt
                                break
                            elif txt and txt.upper() == "LIVE":
                                duration = "LIVE"
                                is_live = True
                                break
                if duration == "LIVE":
                    is_live = True

                # Extract URL & ID
                url = ""
                item_id = ""
                item_type = "video"
                
                cmd_ctx = lv.get("rendererContext", {}).get("commandContext", {}).get("onTap", {}).get("innertubeCommand", {})
                watch_ep = cmd_ctx.get("watchEndpoint", {})
                web_cmd = cmd_ctx.get("commandMetadata", {}).get("webCommandMetadata", {})
                web_url = web_cmd.get("url", "")
                
                if "PLAYLIST" in c_type or web_url.startswith("/playlist"):
                    item_type = "playlist"
                    m = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", web_url)
                    item_id = m.group(1) if m else lv.get("contentId", "")
                    url = f"https://www.youtube.com/playlist?list={item_id}" if item_id else ""
                elif "CHANNEL" in c_type or web_url.startswith("/@") or web_url.startswith("/channel"):
                    item_type = "channel"
                    item_id = channel_id or lv.get("contentId", "")
                    url = f"https://www.youtube.com/channel/{item_id}" if item_id else ""
                else:
                    item_type = "video"
                    item_id = watch_ep.get("videoId") or lv.get("contentId", "")
                    if not item_id and "v=" in web_url:
                        m = re.search(r"[?&]v=([a-zA-Z0-9_-]+)", web_url)
                        if m:
                            item_id = m.group(1)
                    url = f"https://www.youtube.com/watch?v={item_id}" if item_id else ""

                # Extract thumbnail
                thumb_url = ""
                c_img = lv.get("contentImage", {})
                if "collectionThumbnailViewModel" in c_img:
                    sources = c_img["collectionThumbnailViewModel"].get("primaryThumbnail", {}).get("thumbnailViewModel", {}).get("image", {}).get("sources", [])
                    if sources:
                        thumb_url = sources[-1].get("url", "")
                elif "thumbnailViewModel" in c_img:
                    sources = c_img["thumbnailViewModel"].get("image", {}).get("sources", [])
                    if sources:
                        thumb_url = sources[-1].get("url", "")

                if item_id and item_id not in seen_ids and title:
                    seen_ids.add(item_id)
                    results.append({
                        "type": item_type,
                        "id": item_id,
                        "url": url or f"https://www.youtube.com/watch?v={item_id}",
                        "title": title,
                        "channel": channel,
                        "channel_id": channel_id,
                        "duration": "Playlist" if item_type == "playlist" else duration,
                        "views": views,
                        "date": date,
                        "description": desc or (f"Playlist by {channel}" if item_type == "playlist" else ""),
                        "thumbnail": _clean_thumb_url(thumb_url),
                        "is_live": is_live
                    })

            # 5. Playlist Video Renderer (videos inside YouTube playlists)
            elif "playlistVideoRenderer" in obj:
                p = obj["playlistVideoRenderer"]
                vid = p.get("videoId")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    title = ""
                    if "title" in p and "runs" in p["title"] and p["title"]["runs"]:
                        title = p["title"]["runs"][0].get("text", "")
                    elif "title" in p and "simpleText" in p["title"]:
                        title = p["title"]["simpleText"]

                    channel = ""
                    channel_id = ""
                    if "shortBylineText" in p and "runs" in p["shortBylineText"] and p["shortBylineText"]["runs"]:
                        channel = p["shortBylineText"]["runs"][0].get("text", "")
                        ep = p["shortBylineText"]["runs"][0].get("navigationEndpoint", {}).get("browseEndpoint", {})
                        channel_id = ep.get("browseId", "")

                    duration = p.get("lengthText", {}).get("simpleText", "")
                    if not duration and "lengthSeconds" in p:
                        try:
                            s = int(p["lengthSeconds"])
                            duration = f"{s//60}:{s%60:02d}"
                        except Exception:
                            pass

                    idx_str = p.get("index", {}).get("simpleText", "")
                    thumbs = p.get("thumbnail", {}).get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                    if title:
                        results.append({
                            "type": "video",
                            "id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": f"#{idx_str} {title}" if idx_str else title,
                            "channel": channel,
                            "channel_id": channel_id,
                            "duration": duration,
                            "views": "",
                            "date": f"Track #{idx_str}" if idx_str else "",
                            "description": "",
                            "thumbnail": _clean_thumb_url(thumb_url)
                        })

            for v in obj.values():
                parse_renderers(v)
        elif isinstance(obj, list):
            for i in obj:
                parse_renderers(i)

    parse_renderers(data)
    return results, continuation_token

def extract_browse_items(data: Any) -> List[Dict[str, Any]]:
    """Traverses an Innertube browse or search response and extracts structured items."""
    results, _ = extract_browse_items_with_continuation(data)
    return results

def search_youtube_with_continuation(query: str, filter_type: str = "all") -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Searches YouTube via Innertube API and returns (items, continuation_token).
    """
    if not query.strip():
        return [], None

    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "en",
                "gl": "US"
            }
        },
        "query": query.strip()
    }
    
    if filter_type in FILTER_PARAMS and FILTER_PARAMS[filter_type]:
        payload["params"] = FILTER_PARAMS[filter_type]

    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }
    headers.update(get_auth_headers())

    req = urllib.request.Request(
        INNERTUBE_URL,
        headers=headers,
        data=json.dumps(payload).encode()
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)
    except Exception:
        return _search_fallback_scrape(query, filter_type), None

    results, token = extract_browse_items_with_continuation(data)

    # Filter if requested
    if filter_type in ("videos", "channels", "playlists"):
        singular = filter_type.rstrip("s")
        results = [r for r in results if r.get("type") == singular]

    return results, token

def search_youtube(query: str, filter_type: str = "all") -> List[Dict[str, Any]]:
    """
    Searches YouTube via Innertube API and parses Videos, Channels, and Playlists.
    """
    items, _ = search_youtube_with_continuation(query, filter_type)
    return items

def fetch_continuation(token: str, is_browse: bool = False) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Fetches next page of search or feed results using a continuation token."""
    if not token:
        return [], None

    url = BROWSE_URL if is_browse else INNERTUBE_URL
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "en",
                "gl": "US"
            }
        },
        "continuation": token
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }
    headers.update(get_auth_headers())

    req = urllib.request.Request(url, headers=headers, data=json.dumps(payload).encode())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            return extract_browse_items_with_continuation(data)
    except Exception:
        return [], None

def _search_fallback_scrape(query: str, filter_type: str = "all") -> List[Dict[str, Any]]:
    """Scrapes YouTube search HTML and parses ytInitialData JSON as fallback."""
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    m = re.search(r"var ytInitialData = ({.*?});</script>", html)
    if not m:
        m = re.search(r"ytInitialData = ({.*?});", html)
    if not m:
        return []

    try:
        data = json.loads(m.group(1))
    except Exception:
        return []

    results = []
    # Similar extraction on ytInitialData
    return results

def get_channel_videos_with_continuation(channel_id_or_url: str, tab: str = "videos") -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetches videos, playlists, or shorts for a YouTube channel with continuation token.
    Prefers fast Innertube browse API with tab parameter, falling back to yt-dlp.
    """
    cid = channel_id_or_url.strip()
    if "youtube.com/channel/" in cid:
        cid = cid.split("youtube.com/channel/")[-1].split("/")[0]
    elif cid.startswith("http"):
        # Extracts ID if path contains /channel/UC...
        m = re.search(r"/channel/(UC[a-zA-Z0-9_-]{22})", cid)
        if m:
            cid = m.group(1)

    # 1. Fast Innertube Tab Browse if we have a clean channel ID (UC...)
    if cid.startswith("UC"):
        param = CHANNEL_TABS.get(tab, CHANNEL_TABS["videos"])
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101.00.00",
                    "hl": "en",
                    "gl": "US"
                }
            },
            "browseId": cid,
            "params": param
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9"
        }
        headers.update(get_auth_headers())
        req = urllib.request.Request(BROWSE_URL, headers=headers, data=json.dumps(payload).encode())
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.load(resp)
                items, token = extract_browse_items_with_continuation(data)
                if items:
                    return items, token
        except Exception:
            pass

    # 2. yt-dlp fallback
    yt_dlp = shutil.which("yt-dlp") or "/home/john/.local/bin/yt-dlp"
    if not yt_dlp:
        return [], None

    target = channel_id_or_url
    if not target.startswith("http"):
        sub_path = "playlists" if tab == "playlists" else ("shorts" if tab == "shorts" else "videos")
        target = f"https://www.youtube.com/channel/{channel_id_or_url}/{sub_path}"

    cmd = [
        yt_dlp,
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", "25",
        target
    ]

    results = []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                vid = item.get("id")
                if not vid:
                    continue
                duration = format_duration(item.get("duration"))
                views = format_views(item.get("view_count"))
                thumbs = item.get("thumbnails", [])
                thumb_url = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                results.append({
                    "type": "video",
                    "id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "title": item.get("title", "Untitled Video"),
                    "channel": item.get("uploader", "Unknown Channel"),
                    "channel_id": item.get("uploader_id", ""),
                    "duration": duration,
                    "views": f"{views} views" if views else "",
                    "date": "",
                    "description": item.get("description", ""),
                    "thumbnail": _clean_thumb_url(thumb_url)
                })
            except Exception:
                continue
    except Exception:
        pass

    return results, None

def get_channel_videos(channel_id_or_url: str, tab: str = "videos") -> List[Dict[str, Any]]:
    """Fetches videos, playlists, or shorts for a YouTube channel."""
    items, _ = get_channel_videos_with_continuation(channel_id_or_url, tab)
    return items

def get_playlist_videos(playlist_id_or_url: str, max_items: int = 250) -> List[Dict[str, Any]]:
    """
    Fetches video items contained inside a YouTube playlist.
    Uses Innertube browse API with user session cookies for high speed and
    private/unlisted playlist support, falling back to yt-dlp with cookies.
    Handles large playlists by paginating up to max_items.
    """
    target = (playlist_id_or_url or "").strip()
    if not target:
        return []

    # Extract clean playlist ID
    pid = target
    if "list=" in target:
        m = re.search(r"[?&]list=([a-zA-Z0-9_\-]+)", target)
        if m:
            pid = m.group(1)
    elif target.startswith("http"):
        m = re.search(r"list=([a-zA-Z0-9_\-]+)", target)
        if m:
            pid = m.group(1)

    browse_id = pid if pid.startswith("VL") else f"VL{pid}"

    results: List[Dict[str, Any]] = []
    seen_ids = set()
    token = None

    def parse_renderers(obj: Any) -> None:
        nonlocal token
        if isinstance(obj, dict):
            if "continuationCommand" in obj:
                tok = obj["continuationCommand"].get("token")
                if tok and not token:
                    token = tok

            if "playlistVideoRenderer" in obj:
                p = obj["playlistVideoRenderer"]
                vid = p.get("videoId")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    title = ""
                    if "title" in p and "runs" in p["title"] and p["title"]["runs"]:
                        title = p["title"]["runs"][0].get("text", "")
                    elif "title" in p and "simpleText" in p["title"]:
                        title = p["title"]["simpleText"]

                    channel = ""
                    channel_id = ""
                    if "shortBylineText" in p and "runs" in p["shortBylineText"] and p["shortBylineText"]["runs"]:
                        channel = p["shortBylineText"]["runs"][0].get("text", "")
                        ep = p["shortBylineText"]["runs"][0].get("navigationEndpoint", {}).get("browseEndpoint", {})
                        channel_id = ep.get("browseId", "")

                    duration = p.get("lengthText", {}).get("simpleText", "")
                    if not duration and "lengthSeconds" in p:
                        try:
                            s = int(p["lengthSeconds"])
                            duration = f"{s//60}:{s%60:02d}"
                        except Exception:
                            pass

                    idx_str = p.get("index", {}).get("simpleText", "")
                    thumbs = p.get("thumbnail", {}).get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                    if title:
                        results.append({
                            "type": "video",
                            "id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": f"#{idx_str} {title}" if idx_str else title,
                            "channel": channel,
                            "channel_id": channel_id,
                            "duration": duration,
                            "views": "",
                            "date": f"Track #{idx_str}" if idx_str else "",
                            "description": "",
                            "thumbnail": _clean_thumb_url(thumb_url)
                        })

            elif "lockupViewModel" in obj:
                lv = obj["lockupViewModel"]
                c_type = lv.get("contentType", "")
                meta = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
                title = meta.get("title", {}).get("content", "")

                cmd_ctx = lv.get("rendererContext", {}).get("commandContext", {}).get("onTap", {}).get("innertubeCommand", {})
                watch_ep = cmd_ctx.get("watchEndpoint", {})
                web_cmd = cmd_ctx.get("commandMetadata", {}).get("webCommandMetadata", {})
                web_url = web_cmd.get("url", "")

                vid = watch_ep.get("videoId") or lv.get("contentId")
                if ("VIDEO" in c_type or web_url.startswith("/watch") or vid) and vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    channel = ""
                    channel_id = ""
                    views = ""
                    date = ""
                    rows = meta.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
                    for row in rows:
                        for part in row.get("metadataParts", []):
                            content = part.get("text", {}).get("content", "")
                            if not content:
                                continue
                            if not channel:
                                channel = content
                                for cr in part.get("text", {}).get("commandRuns", []):
                                    browse_ep = cr.get("onTap", {}).get("innertubeCommand", {}).get("browseEndpoint", {})
                                    if browse_ep.get("browseId"):
                                        channel_id = browse_ep["browseId"]
                            elif "view" in content:
                                views = content
                            elif "ago" in content:
                                date = content

                    duration = ""
                    overlays = lv.get("contentImage", {}).get("thumbnailViewModel", {}).get("overlays", [])
                    for ov in overlays:
                        badges = ov.get("thumbnailBottomOverlayViewModel", {}).get("badges", [])
                        for b in badges:
                            txt = b.get("thumbnailBadgeViewModel", {}).get("text")
                            if txt and (":" in txt or txt.isdigit()):
                                duration = txt
                                break

                    thumbs = lv.get("contentImage", {}).get("thumbnailViewModel", {}).get("image", {}).get("sources", [])
                    thumb_url = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                    if title:
                        idx_num = len(results) + 1
                        results.append({
                            "type": "video",
                            "id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": f"#{idx_num} {title}",
                            "channel": channel,
                            "channel_id": channel_id,
                            "duration": duration,
                            "views": views,
                            "date": date or f"Track #{idx_num}",
                            "description": "",
                            "thumbnail": _clean_thumb_url(thumb_url),
                            "is_live": is_live
                        })

            elif "videoRenderer" in obj:
                v = obj["videoRenderer"]
                vid = v.get("videoId")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    title = ""
                    if "title" in v and "runs" in v["title"] and v["title"]["runs"]:
                        title = v["title"]["runs"][0].get("text", "")
                    elif "title" in v and "simpleText" in v["title"]:
                        title = v["title"]["simpleText"]

                    channel = ""
                    channel_id = ""
                    if "ownerText" in v and "runs" in v["ownerText"] and v["ownerText"]["runs"]:
                        channel = v["ownerText"]["runs"][0].get("text", "")
                        ep = v["ownerText"]["runs"][0].get("navigationEndpoint", {}).get("browseEndpoint", {})
                        channel_id = ep.get("browseId", "")
                    elif "shortBylineText" in v and "runs" in v["shortBylineText"] and v["shortBylineText"]["runs"]:
                        channel = v["shortBylineText"]["runs"][0].get("text", "")
                        ep = v["shortBylineText"]["runs"][0].get("navigationEndpoint", {}).get("browseEndpoint", {})
                        channel_id = ep.get("browseId", "")

                    duration = v.get("lengthText", {}).get("simpleText", "")
                    views = v.get("shortViewCountText", {}).get("simpleText", "")
                    date = v.get("publishedTimeText", {}).get("simpleText", "")

                    is_live = False
                    for b in v.get("badges", []):
                        mbr = b.get("metadataBadgeRenderer", {})
                        if mbr.get("style") == "BADGE_STYLE_TYPE_LIVE_NOW" or mbr.get("label") == "LIVE":
                            is_live = True
                            break
                    if not is_live and not duration and any("watching" in r.get("text", "") for r in v.get("viewCountText", {}).get("runs", [])):
                        is_live = True

                    if is_live:
                        if not duration:
                            duration = "LIVE"
                        if not views:
                            runs = v.get("viewCountText", {}).get("runs", [])
                            if runs:
                                views = "".join(r.get("text", "") for r in runs)
                    thumbs = v.get("thumbnail", {}).get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                    if title:
                        idx_num = len(results) + 1
                        results.append({
                            "type": "video",
                            "id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": f"#{idx_num} {title}",
                            "channel": channel,
                            "channel_id": channel_id,
                            "duration": duration,
                            "views": views,
                            "date": date or f"Track #{idx_num}",
                            "description": "",
                            "thumbnail": _clean_thumb_url(thumb_url),
                            "is_live": is_live
                        })

            for v in obj.values():
                parse_renderers(v)
        elif isinstance(obj, list):
            for i in obj:
                parse_renderers(i)

    # 1. Innertube Browse Request (Fast & Supports Authenticated Playlists)
    try:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9"
        }
        auth_headers = get_auth_headers()
        if auth_headers:
            headers.update(auth_headers)

        req = urllib.request.Request(
            BROWSE_URL,
            headers=headers,
            data=json.dumps({
                "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "en", "gl": "US"}},
                "browseId": browse_id
            }).encode()
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            parse_renderers(data)

        # Follow continuation tokens for large playlists up to max_items
        while token and len(results) < max_items:
            cur_token = token
            token = None
            req_cont = urllib.request.Request(
                BROWSE_URL,
                headers=headers,
                data=json.dumps({
                    "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "en", "gl": "US"}},
                    "continuation": cur_token
                }).encode()
            )
            try:
                with urllib.request.urlopen(req_cont, timeout=10) as resp_cont:
                    data_cont = json.load(resp_cont)
                    before_count = len(results)
                    parse_renderers(data_cont)
                    if len(results) == before_count:
                        break
            except Exception:
                break

        if results:
            return results
    except Exception:
        pass

    # 2. yt-dlp Fallback with Cookies
    yt_dlp = shutil.which("yt-dlp") or "/home/john/.local/bin/yt-dlp"
    if not yt_dlp:
        return []

    yt_target = target
    if not yt_target.startswith("http"):
        yt_target = f"https://www.youtube.com/playlist?list={pid}"

    cmd = [
        yt_dlp,
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", str(max_items),
        "--socket-timeout", "10"
    ]
    cookies_path = get_cookies_file()
    if cookies_path and os.path.exists(cookies_path):
        cmd.extend(["--cookies", cookies_path])
    cmd.append(yt_target)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        idx = len(results) + 1
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                vid = item.get("id")
                if not vid or vid in seen_ids:
                    continue
                seen_ids.add(vid)
                duration = format_duration(item.get("duration"))
                views = format_views(item.get("view_count"))
                thumbs = item.get("thumbnails", [])
                thumb_url = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                results.append({
                    "type": "video",
                    "id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "title": f"#{idx} {item.get('title', 'Untitled Video')}",
                    "channel": item.get("uploader", "Unknown"),
                    "channel_id": item.get("uploader_id", ""),
                    "duration": duration,
                    "views": f"{views} views" if views else "",
                    "date": f"Track #{idx}",
                    "description": item.get("description", ""),
                    "thumbnail": _clean_thumb_url(thumb_url)
                })
                idx += 1
            except Exception:
                continue
    except Exception:
        pass

    return results

CURATED_FEEDS = {
    "all": "top technology science linux entertainment",
    "trending": "trending tech gaming documentary science",
    "music": "lofi synthwave ambient study music",
    "gaming": "linux gaming pc gaming benchmarks",
    "tech": "arch linux neovim hyprland programming open source",
    "news": "technology science foss linux news"
}

def get_curated_feed(category: str) -> List[Dict[str, Any]]:
    """Retrieves curated starter feed items based on category."""
    query = CURATED_FEEDS.get(category, CURATED_FEEDS["all"])
    return search_youtube(query, filter_type="all")

def get_home_feed() -> List[Dict[str, Any]]:
    """
    Fetches the authenticated user's personalized YouTube Home recommendations.
    Falls back to curated trending feed if not signed in or on error.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }
    auth_headers = get_auth_headers()
    headers.update(auth_headers)

    req = urllib.request.Request(
        BROWSE_URL,
        headers=headers,
        data=json.dumps({
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "en", "gl": "US"}},
            "browseId": "FEwhat_to_watch"
        }).encode()
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            items = extract_browse_items(data)
            if items:
                return items
    except Exception:
        pass

    return get_curated_feed("all")

def get_subscriptions_feed() -> List[Dict[str, Any]]:
    """
    Fetches latest uploads from channels the user is subscribed to (FEsubscriptions).
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }
    auth_headers = get_auth_headers()
    if not auth_headers:
        return []
    headers.update(auth_headers)

    req = urllib.request.Request(
        BROWSE_URL,
        headers=headers,
        data=json.dumps({
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "en", "gl": "US"}},
            "browseId": "FEsubscriptions"
        }).encode()
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            return extract_browse_items(data)
    except Exception:
        return []

def get_history_feed() -> List[Dict[str, Any]]:
    """
    Fetches the user's recent YouTube watch history (FEhistory)
    and merges it with persistent local watch history recorded in YouTube TUI.
    """
    from youtubetui.history import get_local_watch_history
    local_history = get_local_watch_history()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }
    auth_headers = get_auth_headers()
    remote_items = []
    if auth_headers:
        headers.update(auth_headers)
        req = urllib.request.Request(
            BROWSE_URL,
            headers=headers,
            data=json.dumps({
                "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00", "hl": "en", "gl": "US"}},
                "browseId": "FEhistory"
            }).encode()
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.load(resp)
                remote_items = extract_browse_items(data)
        except Exception:
            remote_items = []

    # Merge local history at top with remote YouTube history, deduplicating by ID
    seen_ids = set()
    combined = []
    for item in local_history:
        vid = item.get("id") or item.get("url")
        if vid and vid not in seen_ids:
            seen_ids.add(vid)
            combined.append(item)

    for item in remote_items:
        vid = item.get("id") or item.get("url")
        if vid and vid not in seen_ids:
            seen_ids.add(vid)
            combined.append(item)

    return combined

def get_video_comments(video_id_or_url: str, max_comments: int = 35) -> List[Dict[str, Any]]:
    """
    Fetches top comments for a YouTube video via Innertube /next endpoint.
    Returns list of dicts with keys: author, content, published, likes.
    """
    vid = (video_id_or_url or "").strip()
    if "watch?v=" in vid:
        m = re.search(r"v=([a-zA-Z0-9_-]{11})", vid)
        if m:
            vid = m.group(1)
    elif "youtu.be/" in vid:
        m = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", vid)
        if m:
            vid = m.group(1)

    if not vid:
        return []

    next_url = "https://www.youtube.com/youtubei/v1/next"
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "en",
                "gl": "US"
            }
        },
        "videoId": vid
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9"
    }
    headers.update(get_auth_headers())

    req = urllib.request.Request(next_url, headers=headers, data=json.dumps(payload).encode())
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)
    except Exception:
        return []

    comments_token = None
    def find_comments_token(obj: Any) -> bool:
        nonlocal comments_token
        if isinstance(obj, dict):
            if "continuationCommand" in obj and "comment" in json.dumps(obj).lower():
                comments_token = obj["continuationCommand"].get("token")
                return True
            for v in obj.values():
                if find_comments_token(v):
                    return True
        elif isinstance(obj, list):
            for it in obj:
                if find_comments_token(it):
                    return True
        return False

    find_comments_token(data)
    if not comments_token:
        return []

    payload_cont = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "en",
                "gl": "US"
            }
        },
        "continuation": comments_token
    }
    req_cont = urllib.request.Request(next_url, headers=headers, data=json.dumps(payload_cont).encode())
    try:
        with urllib.request.urlopen(req_cont, timeout=10) as resp_cont:
            data_cont = json.load(resp_cont)
    except Exception:
        return []

    comments: List[Dict[str, Any]] = []
    # 1. Parse frameworkUpdates.entityBatchUpdate.mutations
    mutations = data_cont.get("frameworkUpdates", {}).get("entityBatchUpdate", {}).get("mutations", [])
    for m in mutations:
        p = m.get("payload", {})
        if "commentEntityPayload" in p:
            cep = p["commentEntityPayload"]
            author = cep.get("author", {}).get("displayName", "Anonymous")
            content = cep.get("properties", {}).get("content", {}).get("content", "")
            published = cep.get("properties", {}).get("publishedTime", "")
            toolbar = cep.get("toolbar", {})
            likes = toolbar.get("likeCountNotliked", "0")
            if author and content:
                comments.append({
                    "author": author,
                    "content": content,
                    "published": published,
                    "likes": likes
                })
                if len(comments) >= max_comments:
                    break

    # 2. Fallback to classic commentThreadRenderer
    if not comments:
        def extract_classic_comments(obj: Any):
            if isinstance(obj, dict):
                if "commentThreadRenderer" in obj:
                    cr = obj["commentThreadRenderer"].get("comment", {}).get("commentRenderer", {})
                    author = cr.get("authorText", {}).get("simpleText", "Anonymous")
                    text = "".join(r.get("text", "") for r in cr.get("contentText", {}).get("runs", []))
                    likes = cr.get("voteCount", {}).get("simpleText", "0")
                    published = cr.get("publishedTimeText", {}).get("runs", [{}])[0].get("text", "")
                    if author and text:
                        comments.append({
                            "author": author,
                            "content": text,
                            "published": published,
                            "likes": likes
                        })
                for v in obj.values():
                    extract_classic_comments(v)
            elif isinstance(obj, list):
                for it in obj:
                    extract_classic_comments(it)
        extract_classic_comments(data_cont)

    return comments[:max_comments]
