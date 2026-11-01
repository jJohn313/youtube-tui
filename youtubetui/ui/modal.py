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
