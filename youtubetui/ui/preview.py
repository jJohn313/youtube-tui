"""
Preview inspector pane widget mirroring Yazi's right pane preview.
Displays inline high-res true-color thumbnail art via chafa,
rich metadata (views, duration, channel, upload date), and action keybindings.
"""

from typing import Any, Dict, Optional
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, Container
from textual.widgets import Label, Static
from youtubetui.theme import (
    ACC0, ACC1, BG0, BG1, BG2, BG3, FG0, FG1, PEACH, RAMP_OPEN, RAMP_CLOSE
)
from youtubetui.thumbnail import async_render_thumbnail, render_fallback_placeholder

class PreviewPane(Vertical):
    """Right-hand detailed preview pane."""

    DEFAULT_CSS = f"""
    PreviewPane {{
        width: 48;
        height: 100%;
        background: {BG1};
        padding: 0 1;
        overflow-y: auto;
    }}
    #thumb-container {{
        height: 16;
        width: 100%;
        background: {BG0};
        border: round {BG3};
        align: center middle;
        content-align: center middle;
        margin-top: 1;
    }}
    #preview-title-label {{
        color: {ACC0};
        text-style: bold;
        margin-top: 1;
        height: auto;
    }}
    #preview-channel-label {{
        color: {PEACH};
        text-style: bold;
        margin-top: 0;
    }}
    #preview-meta-label {{
        color: {FG1};
        margin-top: 0;
    }}
    #preview-desc-label {{
        color: {FG0};
        margin-top: 1;
        height: auto;
    }}
    #actions-panel {{
        margin-top: 1;
        margin-bottom: 1;
        padding: 0 1;
        background: {BG2};
        border: round {BG3};
        color: {ACC0};
        height: auto;
    }}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_item: Optional[Dict[str, Any]] = None
        self._current_render_id: str = ""

    def compose(self) -> ComposeResult:
        placeholder = render_fallback_placeholder(42, 14, "No Item Selected")
        yield Static(Text.from_ansi(placeholder), id="thumb-container")
        yield Label("Select an item to view preview", id="preview-title-label")
        yield Label("", id="preview-channel-label")
        yield Label("", id="preview-meta-label")
        yield Label("", id="preview-desc-label")
        
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
        yield Static(actions_text, id="actions-panel")

    async def update_item(self, item: Optional[Dict[str, Any]]) -> None:
        """Updates the metadata and asynchronously triggers thumbnail rendering."""
        self.current_item = item
        if not item:
            return

        item_id = item.get("id", "")
        self._current_render_id = item_id

        # Update text labels
        title_widget = self.query_one("#preview-title-label", Label)
        channel_widget = self.query_one("#preview-channel-label", Label)
        meta_widget = self.query_one("#preview-meta-label", Label)
        desc_widget = self.query_one("#preview-desc-label", Label)

        item_type = item.get("type", "video").upper()
        title_widget.update(Text(f"[{item_type}] {item.get('title', '')}"))
        
        ch_name = item.get("channel", "")
        channel_widget.update(Text(f"󰗃 {ch_name}" if ch_name else ""))

        meta_parts = []
        if item.get("duration"):
            meta_parts.append(f"⏱ {item['duration']}")
        if item.get("views"):
            meta_parts.append(f"👁 {item['views']}")
        if item.get("date"):
            meta_parts.append(f"📅 {item['date']}")
        meta_widget.update(Text("  •  ".join(meta_parts)))

        desc = item.get("description", "")
        if desc:
            desc_widget.update(Text(desc[:280] + ("..." if len(desc) > 280 else "")))
        else:
            desc_widget.update(Text(""))

        # Render thumbnail in background worker to ensure snappy scrolling
        thumb_box = self.query_one("#thumb-container", Static)
        thumb_url = item.get("thumbnail", "")

        initial_ph = render_fallback_placeholder(42, 14, "Loading Thumbnail...")
        thumb_box.update(Text.from_ansi(initial_ph))

        if thumb_url:
            self.run_worker(self._render_thumb_worker(thumb_url, item_id), exclusive=False)

    async def _render_thumb_worker(self, thumb_url: str, item_id: str) -> None:
        ansi = await async_render_thumbnail(thumb_url, item_id, width=42, height=14)
        if self._current_render_id == item_id:
            thumb_box = self.query_one("#thumb-container", Static)
            thumb_box.update(Text.from_ansi(ansi))
