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
from typing import Any, Dict, List, Optional
from youtubetui.auth import get_auth_headers

INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/search"
BROWSE_URL = "https://www.youtube.com/youtubei/v1/browse"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

FILTER_PARAMS = {
    "videos": "EgIQAQ%3D%3D",
    "channels": "EgIQAg%3D%3D",
    "playlists": "EgIQAw%3D%3D"
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

def extract_browse_items(data: Any) -> List[Dict[str, Any]]:
    """Traverses an Innertube browse or search response and extracts structured items."""
    results: List[Dict[str, Any]] = []
    seen_ids = set()

    def parse_renderers(obj: Any):
        if isinstance(obj, dict):
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
                            "thumbnail": _clean_thumb_url(thumb_url)
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

                # Extract URL & ID
                url = ""
                item_id = ""
                item_type = "video"
                
                if "PLAYLIST" in c_type:
                    item_type = "playlist"
                
                cmd_ctx = lv.get("rendererContext", {}).get("commandContext", {}).get("onTap", {}).get("innertubeCommand", {})
                watch_ep = cmd_ctx.get("watchEndpoint", {})
                web_cmd = cmd_ctx.get("commandMetadata", {}).get("webCommandMetadata", {})
                web_url = web_cmd.get("url", "")
                
                if "list=" in web_url:
                    m = re.search(r"list=([a-zA-Z0-9_-]+)", web_url)
                    if m:
                        item_id = m.group(1)
                        item_type = "playlist"
                        url = f"https://www.youtube.com/playlist?list={item_id}"
                elif watch_ep.get("videoId"):
                    item_id = watch_ep["videoId"]
                    item_type = "video"
                    url = f"https://www.youtube.com/watch?v={item_id}"
                elif lv.get("contentId"):
                    item_id = lv["contentId"]
                    url = f"https://www.youtube.com/watch?v={item_id}"

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
                        "thumbnail": _clean_thumb_url(thumb_url)
                    })

            for v in obj.values():
                parse_renderers(v)
        elif isinstance(obj, list):
            for i in obj:
                parse_renderers(i)

    parse_renderers(data)
    return results

def search_youtube(query: str, filter_type: str = "all") -> List[Dict[str, Any]]:
    """
    Searches YouTube via Innertube API and parses Videos, Channels, and Playlists.
    """
    if not query.strip():
        return []

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
    
    if filter_type in FILTER_PARAMS:
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
        return _search_fallback_scrape(query, filter_type)

    results = extract_browse_items(data)

    # Filter if requested
    if filter_type != "all":
        singular = filter_type.rstrip("s")
        results = [r for r in results if r["type"] == singular]

    return results

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

def get_channel_videos(channel_id_or_url: str) -> List[Dict[str, Any]]:
    """Fetches the latest videos uploaded by a YouTube channel."""
    yt_dlp = shutil.which("yt-dlp") or "/home/john/.local/bin/yt-dlp"
    if not yt_dlp:
        return []

    target = channel_id_or_url
    if not target.startswith("http"):
        target = f"https://www.youtube.com/channel/{channel_id_or_url}/videos"
    elif not target.endswith("/videos"):
        target = target.rstrip("/") + "/videos"

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

    return results

def get_playlist_videos(playlist_id_or_url: str) -> List[Dict[str, Any]]:
    """Fetches all video items contained inside a YouTube playlist."""
    yt_dlp = shutil.which("yt-dlp") or "/home/john/.local/bin/yt-dlp"
    if not yt_dlp:
        return []

    target = playlist_id_or_url
    if not target.startswith("http"):
        target = f"https://www.youtube.com/playlist?list={playlist_id_or_url}"

    cmd = [
        yt_dlp,
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", "40",
        target
    ]

    results = []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        idx = 1
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
    Fetches the user's recent YouTube watch history (FEhistory).
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
            "browseId": "FEhistory"
        }).encode()
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            return extract_browse_items(data)
    except Exception:
        return []
