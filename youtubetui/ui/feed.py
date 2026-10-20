"""
Center feed pane widget displaying YouTube search results and feeds
with Yazi-style item cards, selection highlights, and indicator padding ramps.
"""

from typing import Any, Dict, List
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView
from youtubetui.theme import (
    ACC0, ACC1, BG0, BG1, BG2, BG3, FG0, FG1, FG2, PEACH,
    BADGE_VIDEO, BADGE_CHANNEL, BADGE_PLAYLIST, RAMP_OPEN, RAMP_CLOSE
)

class FeedItemWidget(ListItem):
    """An individual video, channel, or playlist card in the center feed."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.item_data = data

    def compose(self) -> ComposeResult:
        item_type = self.item_data.get("type", "video")
        title = self.item_data.get("title", "Untitled")
        channel = self.item_data.get("channel", "")
        duration = self.item_data.get("duration", "")
        views = self.item_data.get("views", "")
        date = self.item_data.get("date", "")

        # Color-coded badge
        if item_type == "channel":
            badge = BADGE_CHANNEL
            badge_style = f"bold {ACC0}"
        elif item_type == "playlist":
            badge = BADGE_PLAYLIST
            badge_style = f"bold {PEACH}"
        else:
            badge = BADGE_VIDEO
            badge_style = f"bold {FG0}"

        line1 = Text()
        line1.append(f"{badge} ", style=badge_style)
        line1.append(title, style=f"bold {ACC0}")

        line2_parts = []
        if channel:
            line2_parts.append(channel)
        if duration:
            line2_parts.append(duration)
        if views:
            line2_parts.append(views)
        if date:
            line2_parts.append(date)

        line2 = Text("   " + " • ".join(line2_parts), style=FG1)

        yield Label(line1, classes="item-line1")
        yield Label(line2, classes="item-line2")

class FeedPane(Vertical):
    """Center column containing YouTube feed items."""

    DEFAULT_CSS = f"""
    FeedPane {{
        width: 1fr;
        height: 100%;
        background: {BG0};
        border-right: solid {BG3};
        layout: vertical;
        padding: 0;
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
    #feed-list-view > ListItem {{
        background: {BG0};
        border-bottom: solid {BG1};
        padding: 0 1;
        height: 2;
        color: {FG0};
    }}
    #feed-list-view > ListItem:hover {{
        background: {BG1};
    }}
    #feed-list-view > ListItem.-selected {{
        background: {ACC0};
        color: {BG0};
    }}
    #feed-list-view > ListItem.-selected .item-line1 {{
        color: {BG0};
        text-style: bold;
    }}
    #feed-list-view > ListItem.-selected .item-line2 {{
        color: {BG2};
    }}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Label("RESULTS", id="feed-header-bar")
        yield ListView(id="feed-list-view")

    def populate(self, items: List[Dict[str, Any]], title: str = "RESULTS") -> None:
        """Clears and loads new items into the feed list."""
        self.items = items
        self.query_one("#feed-header-bar", Label).update(Text(f"{title} ({len(items)} items)"))
        list_view = self.query_one("#feed-list-view", ListView)
        list_view.clear()
        for item in items:
            list_view.append(FeedItemWidget(item))
        if items:
            list_view.index = 0
