"""
Interactive Modal Dialog for adding videos to custom or synchronized YouTube playlists,
and creating new custom playlists on the fly.
"""

from typing import Any, Dict, Optional, Tuple
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView
from youtubetui.playlists import (
    get_all_user_playlists,
    create_custom_playlist,
    add_video_to_playlist
)
from youtubetui.theme import ACC0, ACC1, BG0, BG1, BG2, BG3, FG0, FG1, PEACH


class PlaylistModal(ModalScreen[Optional[Tuple[bool, str]]]):
    """Modal dialog allowing users to pick an existing playlist or create a new one."""

    BINDINGS = [
        Binding("escape", "cancel_modal", "Cancel", show=False),
    ]

    DEFAULT_CSS = f"""
    PlaylistModal {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #modal-container {{
        width: 65;
        height: 22;
        background: {BG1};
        border: heavy {ACC0};
        padding: 1 2;
        layout: vertical;
    }}

    #modal-title {{
        color: {ACC0};
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }}

    #modal-subtitle {{
        color: {FG1};
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }}

    #playlist-input {{
        background: {BG2};
        color: {FG0};
        border: round {BG3};
        margin-bottom: 1;
    }}

    #playlist-input:focus {{
        border: round {ACC0};
    }}

    #playlist-list {{
        background: {BG1};
        border: solid {BG3};
        height: 1fr;
        padding: 0;
    }}

    #playlist-list > ListItem {{
        height: 1;
        padding: 0 1;
        background: {BG1};
        color: {FG1};
    }}

    #playlist-list > ListItem:hover {{
        background: {BG2};
        color: {ACC0};
    }}

    #playlist-list > ListItem.-highlight,
    #playlist-list > ListItem:focus,
    #playlist-list > ListItem.-selected {{
        background: {ACC0};
        color: {BG0};
        text-style: bold;
    }}

    #modal-hint {{
        color: {FG1};
        text-align: center;
        margin-top: 1;
    }}
    """

    def __init__(self, video_item: Dict[str, Any]):
        super().__init__()
        self.video_item = video_item
        self.playlists = get_all_user_playlists()

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-container"):
            yield Label("ADD TO PLAYLIST", id="modal-title")
            title_trunc = self.video_item.get("title", "")[:50]
            yield Label(f"Video: {title_trunc}", id="modal-subtitle")
            yield Input(placeholder="Type to filter or enter new playlist name...", id="playlist-input")
            yield ListView(id="playlist-list")
            yield Label("Enter: Select / Create  •  Esc: Cancel", id="modal-hint")

    def on_mount(self) -> None:
        self.call_after_refresh(self._init_modal)

    def _init_modal(self) -> None:
        self.populate_list("")
        try:
            self.query_one("#playlist-input", Input).focus()
        except Exception:
            pass

    def populate_list(self, filter_text: str = "") -> None:
        list_view = self.query_one("#playlist-list", ListView)
        list_view.clear()

        clean_filter = filter_text.strip().lower()

        # Item 0: Option to create new playlist
        if clean_filter:
            create_label = f"➕ Create New Playlist: '{filter_text.strip()}'"
        else:
            create_label = "➕ Create New Playlist..."
        list_view.append(ListItem(Label(create_label), id="action_create"))

        # Playlist entries
        for p in self.playlists:
            p_title = p.get("title", "")
            if clean_filter and clean_filter not in p_title.lower():
                continue

            badge = "[CUSTOM]" if p.get("is_custom") else "[YOUTUBE]"
            duration = p.get("duration", "")
            label_text = f"{badge} {p_title} ({duration})"
            item = ListItem(Label(label_text))
            item._playlist_data = p
            list_view.append(item)

    def on_input_changed(self, event: Input.Changed) -> None:
        self.populate_list(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        if val:
            # Check if an existing playlist matches exactly
            for p in self.playlists:
                if p.get("title", "").lower() == val.lower():
                    ok, msg = add_video_to_playlist(p["id"], self.video_item)
                    self.dismiss((ok, msg))
                    return
            # Create a new playlist with this name
            new_pl = create_custom_playlist(val)
            ok, msg = add_video_to_playlist(new_pl["id"], self.video_item)
            self.dismiss((ok, msg))
        else:
            list_view = self.query_one("#playlist-list", ListView)
            list_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if getattr(event.item, "id", None) == "action_create":
            inp = self.query_one("#playlist-input", Input)
            val = inp.value.strip()
            if not val:
                inp.focus()
                return
            new_pl = create_custom_playlist(val)
            ok, msg = add_video_to_playlist(new_pl["id"], self.video_item)
            self.dismiss((ok, msg))
            return

        pl = getattr(event.item, "_playlist_data", None)
        if pl:
            ok, msg = add_video_to_playlist(pl["id"], self.video_item)
            self.dismiss((ok, msg))

    def action_cancel_modal(self) -> None:
        self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)


class FilterModal(ModalScreen[Optional[str]]):
    """Modal dialog allowing users to pick search sort or filter criteria."""

    BINDINGS = [
        Binding("escape", "cancel_modal", "Cancel", show=False),
        Binding("q", "cancel_modal", "Cancel", show=False),
    ]

    DEFAULT_CSS = f"""
    FilterModal {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #filter-container {{
        width: 65;
        height: 18;
        background: {BG1};
        border: heavy {ACC0};
        padding: 1 2;
        layout: vertical;
    }}

    #filter-title {{
        color: {ACC0};
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }}

    #filter-list {{
        background: {BG1};
        height: 1fr;
    }}

    #filter-list > ListItem {{
        padding: 0 1;
        color: {FG0};
    }}

    #filter-list > ListItem:hover {{
        background: {BG2};
    }}

    #filter-list > ListItem.-selected {{
        background: {ACC0};
        color: {BG0};
        text-style: bold;
    }}
    """

    OPTIONS = [
        ("all", "Relevance (Default)", "Standard YouTube ranking"),
        ("date", "Upload Date (Latest)", "Sort strictly by newly uploaded"),
        ("views", "View Count (Most Viewed)", "Sort by all-time popularity"),
        ("live", "Live Streams Only", "Active broadcasts only"),
        ("short", "Short Videos (<4 min)", "Under 4 minutes duration"),
        ("long", "Long Videos (>20 min)", "Deep-dives over 20 minutes"),
        ("channels", "Channels Only", "Channel creator profiles only"),
        ("playlists", "Playlists Only", "Curated playlist collections"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="filter-container"):
            yield Label("⚡ Search Filter & Sorting", id="filter-title")
            with ListView(id="filter-list"):
                for key, label, desc in self.OPTIONS:
                    line = Text()
                    line.append(f"{label:<26} ", style=f"bold {PEACH}")
                    line.append(f"• {desc}", style=FG1)
                    item = ListItem(Label(line))
                    item._filter_key = key
                    yield item

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        key = getattr(event.item, "_filter_key", "all")
        self.dismiss(key)

    def action_cancel_modal(self) -> None:
        self.dismiss(None)


class CommentsModal(ModalScreen[None]):
    """Modal dialog displaying top comments and user discussions for a video."""

    BINDINGS = [
        Binding("escape", "cancel_modal", "Close", show=False),
        Binding("q", "cancel_modal", "Close", show=False),
    ]

    DEFAULT_CSS = f"""
    CommentsModal {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #comments-container {{
        width: 86;
        height: 28;
        background: {BG1};
        border: heavy {ACC0};
        padding: 1 2;
        layout: vertical;
    }}

    #comments-title {{
        color: {ACC0};
        text-style: bold;
        text-align: center;
        width: 100%;
    }}

    #comments-sub {{
        color: {FG1};
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }}

    #comments-list {{
        background: {BG1};
        height: 1fr;
    }}

    .comment-item {{
        padding: 0 1;
        margin-bottom: 1;
        background: {BG2};
        border-left: solid {ACC0};
    }}

    .comment-item.-selected {{
        background: {BG3};
        border-left: heavy {PEACH};
    }}
    """

    def __init__(self, title: str, comments: list[dict[str, Any]]):
        super().__init__()
        self.video_title = title
        self.comments = comments

    def compose(self) -> ComposeResult:
        with Vertical(id="comments-container"):
            yield Label("💬 Top Comments & Discussion", id="comments-title")
            yield Label(f"Video: {self.video_title[:65]} (Esc/q to close)", id="comments-sub")
            with ListView(id="comments-list"):
                if not self.comments:
                    yield ListItem(Label("No comments found or comments are disabled for this video."))
                for c in self.comments:
                    author = c.get("author", "Anonymous")
                    published = c.get("published", "")
                    likes = c.get("likes", "0")
                    content = c.get("content", "").replace("\n", " ").strip()

                    card = Text()
                    card.append(f"{author} ", style=f"bold {PEACH}")
                    if published:
                        card.append(f"• {published} ", style=FG1)
                    if likes and likes != "0":
                        card.append(f"• ❤ {likes} ", style=f"bold {ACC0}")
                    card.append(f"\n{content}")
                    item = ListItem(Label(card), classes="comment-item")
                    yield item

    def action_cancel_modal(self) -> None:
        self.dismiss(None)
