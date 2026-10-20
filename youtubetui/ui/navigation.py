"""
Sidebar navigation widget mirroring Yazi's left pane and YouTube web's left drawer.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView
from youtubetui.theme import ACC0, ACC1, BG0, BG1, BG2, BG3, FG0, FG1

NAV_ITEMS = [
    ("explore_all", "  All Results"),
    ("explore_videos", "  Videos Only"),
    ("explore_channels", "  Channels Only"),
    ("explore_playlists", "  Playlists Only"),
    ("sep1", "── Feeds ──"),
    ("feed_trending", "  Trending"),
    ("feed_tech", "  Tech & Linux"),
    ("feed_music", "  Music & Lofi"),
    ("feed_gaming", "  Gaming"),
    ("feed_news", "  News & Science"),
]

class NavItem(ListItem):
    def __init__(self, item_id: str, label: str):
        super().__init__()
        self.item_id = item_id
        self.raw_label = label

    def compose(self) -> ComposeResult:
        if self.item_id.startswith("sep"):
            yield Label(Text(self.raw_label, style=f"bold {ACC1}"), classes="nav-separator")
        else:
            yield Label(self.raw_label, classes="nav-label")

class NavigationSidebar(Vertical):
    """Left drawer containing categories, filters, and feeds."""

    DEFAULT_CSS = f"""
    NavigationSidebar {{
        width: 24;
        height: 100%;
        background: {BG1};
        border-right: solid {BG3};
        padding: 0;
    }}
    #nav-title {{
        color: {ACC0};
        text-style: bold;
        padding: 1 1 0 1;
        background: {BG1};
    }}
    #nav-list {{
        background: {BG1};
        border: none;
        height: 1fr;
        padding: 0;
    }}
    #nav-list > ListItem {{
        height: 1;
        background: {BG1};
        color: {FG1};
        padding: 0 1;
    }}
    #nav-list > ListItem:hover {{
        background: {BG2};
        color: {ACC0};
    }}
    #nav-list > ListItem.-selected {{
        background: {ACC0};
        color: {BG0};
        text-style: bold;
    }}
    .nav-separator {{
        color: {FG1};
        text-style: bold;
    }}
    """

    def compose(self) -> ComposeResult:
        yield Label("NAVIGATE", id="nav-title")
        items = [NavItem(item_id, label) for item_id, label in NAV_ITEMS]
        yield ListView(*items, id="nav-list")
