"""
Feed pane widget displaying YouTube search results and feeds
with side-by-side thumbnail previews, rich video metadata cards,
and high-contrast keyboard selection highlighting.
"""

from typing import Any, Dict, List, Optional
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, ListItem, ListView, Static
from youtubetui.theme import (
    ACC0, ACC1, BG0, BG1, BG2, BG3, FG0, FG1, FG2, PEACH,
    BADGE_VIDEO, BADGE_CHANNEL, BADGE_PLAYLIST
)
from youtubetui.thumbnail import async_render_thumbnail

def make_mini_placeholder(width: int = 16, height: int = 5, item_type: str = "video") -> str:
    """Generates an aesthetic compact placeholder box for list cards."""
    icon = "▶" if item_type == "video" else ("" if item_type == "channel" else "󰲸")
    lines = []
    lines.append("╭" + "─" * (width - 2) + "╮")
    lines.append(f"│    {icon} {item_type[:4]:<4}   │")
    lines.append("│     16:9     │")
    lines.append("│              │")
    lines.append("╰" + "─" * (width - 2) + "╯")
    return "\n".join(lines[:height])

class FeedItemWidget(ListItem):
    """An individual video, channel, or playlist card with side-by-side preview and details."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.item_data = data
        self._rendered = False

    def compose(self) -> ComposeResult:
        item_type = self.item_data.get("type", "video")
        title = self.item_data.get("title", "Untitled")
        channel = self.item_data.get("channel", "")
        duration = self.item_data.get("duration", "")
        views = self.item_data.get("views", "")
        date = self.item_data.get("date", "")
        desc = self.item_data.get("description", "")

        # Type badge
        if item_type == "channel":
            badge = BADGE_CHANNEL
            badge_style = f"bold {ACC0}"
        elif item_type == "playlist":
            badge = BADGE_PLAYLIST
            badge_style = f"bold {PEACH}"
        else:
            badge = BADGE_VIDEO
            badge_style = f"bold {FG0}"

        with Horizontal(classes="card-container"):
            # Left side: Mini Thumbnail Box (16 cols x 5 rows)
            initial_thumb = make_mini_placeholder(16, 5, item_type)
            yield Static(Text.from_ansi(initial_thumb), classes="card-thumb")

            # Right side: Rich Details
            with Vertical(classes="card-details"):
                # Line 1: Badge + Title
                title_line = Text()
                title_line.append(f"{badge} ", style=badge_style)
                title_line.append(title, style=f"bold {ACC0}")
                yield Label(title_line, classes="card-title")

                # Line 2: Channel • Duration • Views • Date
                meta_parts = []
                if channel:
                    meta_parts.append(channel)
                if duration:
                    meta_parts.append(duration)
                if views:
                    meta_parts.append(views)
                if date:
                    meta_parts.append(date)
                meta_line = Text(" • ".join(meta_parts), style=ACC1)
                yield Label(meta_line, classes="card-meta")

                # Line 3: Description snippet
                if desc:
                    snippet = desc.replace("\n", " ").strip()
                    if len(snippet) > 100:
                        snippet = snippet[:100] + "..."
                    yield Label(Text(snippet, style=FG1), classes="card-desc")
                else:
                    yield Label(Text("", style=FG1), classes="card-desc")

    def on_mount(self) -> None:
        """Trigger background thumbnail render when mounted."""
        thumb_url = self.item_data.get("thumbnail", "")
        item_id = self.item_data.get("id", "")
        if thumb_url and not self._rendered:
            self.run_worker(self._fetch_mini_thumb(thumb_url, item_id), exclusive=False)

    async def _fetch_mini_thumb(self, thumb_url: str, item_id: str) -> None:
        ansi = await async_render_thumbnail(thumb_url, item_id, width=16, height=5)
        self._rendered = True
        try:
            thumb_box = self.query_one(".card-thumb", Static)
            thumb_box.update(Text.from_ansi(ansi))
        except Exception:
            pass

class FeedPane(Vertical):
    """Main feed column displaying YouTube items and top categories."""

    DEFAULT_CSS = f"""
    FeedPane {{
        width: 1fr;
        height: 100%;
        background: {BG0};
        border-right: solid {BG3};
        layout: vertical;
        padding: 0;
    }}
    #feed-category-bar {{
        height: 1;
        background: {BG1};
        border-bottom: solid {BG3};
        layout: horizontal;
        padding: 0 1;
        align: left middle;
    }}
    .cat-tab {{
        color: {FG1};
        padding: 0 1;
        text-style: bold;
    }}
    .cat-tab.-active {{
        background: {ACC0};
        color: {BG0};
        text-style: bold;
    }}
    #feed-header-bar {{
        height: 1;
        background: {BG1};
        color: {ACC0};
        text-style: bold;
        padding: 0 1;
        border-bottom: solid {BG3};
    }}
    #feed-list-view {{
        background: {BG0};
        border: none;
        height: 1fr;
        padding: 0;
    }}
    
    /* Card Container */
    #feed-list-view > ListItem {{
        background: {BG0};
        border-bottom: solid {BG1};
        padding: 0 1;
        height: 6;
        color: {FG0};
        border-left: wide transparent;
    }}
    
    #feed-list-view > ListItem:hover {{
        background: {BG1};
    }}

    /* Highlighted / Active Selection State (Arrow Key Navigation) */
    #feed-list-view > ListItem.-highlight,
    #feed-list-view > ListItem:focus,
    #feed-list-view > ListItem.-selected {{
        background: {BG2};
        border-left: wide {ACC0};
        border-top: solid {BG3};
        border-bottom: solid {BG3};
    }}
    
    #feed-list-view > ListItem.-highlight .card-title,
    #feed-list-view > ListItem:focus .card-title,
    #feed-list-view > ListItem.-selected .card-title {{
        color: {PEACH};
        text-style: bold;
    }}

    #feed-list-view > ListItem.-highlight .card-meta,
    #feed-list-view > ListItem:focus .card-meta,
    #feed-list-view > ListItem.-selected .card-meta {{
        color: {ACC0};
        text-style: bold;
    }}

    #feed-list-view > ListItem.-highlight .card-desc,
    #feed-list-view > ListItem:focus .card-desc,
    #feed-list-view > ListItem.-selected .card-desc {{
        color: {FG0};
    }}

    .card-container {{
        layout: horizontal;
        height: 5;
        width: 100%;
    }}

    .card-thumb {{
        width: 18;
        height: 5;
        background: {BG0};
        margin-right: 1;
        content-align: center middle;
    }}

    .card-details {{
        width: 1fr;
        height: 5;
        layout: vertical;
    }}

    .card-title {{
        height: 1;
        color: {ACC0};
        text-style: bold;
    }}

    .card-meta {{
        height: 1;
        color: {ACC1};
    }}

    .card-desc {{
        height: 2;
        color: {FG1};
    }}
    """

    CATEGORIES = [
        ("1", "Home", "home"),
        ("2", "Subscriptions", "subs"),
        ("3", "History", "history"),
        ("4", "Trending", "trending"),
        ("5", "Tech", "tech"),
        ("6", "Music", "music"),
        ("7", "Gaming", "gaming"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items: List[Dict[str, Any]] = []
        self.current_title: str = "RESULTS"
        self.active_category: str = "home"

    def compose(self) -> ComposeResult:
        with Horizontal(id="feed-category-bar"):
            for num, label, cat_id in self.CATEGORIES:
                is_active = "-active" if cat_id == self.active_category else ""
                classes = f"cat-tab {is_active}".strip()
                yield Label(f"[{num}] {label}", id=f"cat-{cat_id}", classes=classes)

        yield Label("RESULTS", id="feed-header-bar")
        yield ListView(id="feed-list-view")

    def set_active_category(self, cat_id: str) -> None:
        """Updates the highlighted category tab."""
        self.active_category = cat_id
        for _, _, cid in self.CATEGORIES:
            try:
                lbl = self.query_one(f"#cat-{cid}", Label)
                if cid == cat_id:
                    lbl.add_class("-active")
                else:
                    lbl.remove_class("-active")
            except Exception:
                pass

    def populate(self, items: List[Dict[str, Any]], title: str = "RESULTS") -> None:
        """Clears and loads new items into the feed list."""
        self.items = items
        self.current_title = title
        self.query_one("#feed-header-bar", Label).update(Text(f"{title} ({len(items)} items)"))
        list_view = self.query_one("#feed-list-view", ListView)
        list_view.clear()
        for item in items:
            list_view.append(FeedItemWidget(item))
        if items:
            list_view.index = 0
