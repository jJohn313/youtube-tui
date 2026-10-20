"""
Sidebar navigation widget placed on the right pillar,
containing feeds, categories, account sync, and quick action keybinding reference.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView, Static
from youtubetui.theme import ACC0, ACC1, BG0, BG1, BG2, BG3, FG0, FG1, PEACH

NAV_ITEMS = [
    ("feed_home", "  My Home"),
    ("feed_subs", "  Subscriptions"),
    ("feed_history", "  Watch History"),
    ("sep0", "── Explore ──"),
    ("explore_all", "  All Results"),
    ("explore_videos", "  Videos Only"),
    ("explore_channels", "  Channels Only"),
    ("explore_playlists", "  Playlists Only"),
    ("sep1", "── Curated ──"),
    ("feed_trending", "  Trending"),
    ("feed_tech", "  Tech & Linux"),
    ("feed_music", "  Music & Lofi"),
    ("feed_gaming", "  Gaming"),
    ("feed_news", "  News & Science"),
    ("sep2", "── Account ──"),
    ("action_sync_webflow", "  Sync Webflow"),
    ("action_sync_zen", "  Sync Zen"),
    ("action_sync_firefox", "  Sync Firefox"),
    ("action_sign_out", "  Sign Out / Guest"),
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
    """Right-hand navigation pillar containing categories, sync actions, and quick action hints."""

    DEFAULT_CSS = f"""
    NavigationSidebar {{
        width: 28;
        height: 100%;
        background: {BG1};
        border-left: solid {BG3};
        padding: 0;
        layout: vertical;
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
    #nav-list > ListItem.-highlight,
    #nav-list > ListItem:focus,
    #nav-list > ListItem.-selected {{
        background: {ACC0};
        color: {BG0};
        text-style: bold;
    }}
    .nav-separator {{
        color: {FG1};
        text-style: bold;
    }}
    #quick-actions-box {{
        margin: 1 1;
        padding: 0 1;
        background: {BG2};
        border: round {BG3};
        color: {ACC0};
        height: auto;
    }}
    """

    def compose(self) -> ComposeResult:
        yield Label("NAVIGATE", id="nav-title")
        items = [NavItem(item_id, label) for item_id, label in NAV_ITEMS]
        yield ListView(*items, id="nav-list")

        actions_text = Text()
        actions_text.append("QUICK ACTIONS\n", style=f"bold {ACC0}")
        actions_text.append(" Enter ", style=f"bold {PEACH}")
        actions_text.append(" Play in MPV / Browse\n", style=ACC1)
        actions_text.append(" m     ", style=f"bold {PEACH}")
        actions_text.append(" Audio Only MPV\n", style=ACC1)
        actions_text.append(" c     ", style=f"bold {PEACH}")
        actions_text.append(" Browse Channel\n", style=ACC1)
        actions_text.append(" p     ", style=f"bold {PEACH}")
        actions_text.append(" Browse Playlist\n", style=ACC1)
        actions_text.append(" y     ", style=f"bold {PEACH}")
        actions_text.append(" Copy URL (wl-copy)\n", style=ACC1)
        actions_text.append(" r     ", style=f"bold {PEACH}")
        actions_text.append(" Refresh Current Feed", style=ACC1)
        yield Static(actions_text, id="quick-actions-box")
