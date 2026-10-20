"""
Header bar widget for YouTube-TUI reproducing YouTube web's top bar with Yazi aesthetics.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Label, Static
from youtubetui.theme import ACC0, ACC1, BG0, BG1, BG2, BG3, FG0, FG1, PEACH

class HeaderBar(Horizontal):
    """Top navigation and search bar."""
    
    DEFAULT_CSS = f"""
    HeaderBar {{
        height: 3;
        background: {BG1};
        border-bottom: solid {BG3};
        padding: 0 1;
        layout: horizontal;
        align: left middle;
    }}
    #logo-box {{
        width: 13;
        height: 1;
        background: {FG0};
        color: {BG0};
        text-style: bold;
        content-align: center middle;
        margin-right: 1;
    }}
    #search-box {{
        width: 1fr;
        height: 1;
        background: {BG2};
        color: {ACC0};
        border: none;
        padding: 0 1;
    }}
    #search-box:focus {{
        background: {BG3};
        color: {PEACH};
    }}
    #breadcrumb-box {{
        width: auto;
        height: 1;
        color: {ACC1};
        text-style: bold;
        padding-left: 2;
        content-align: left middle;
    }}
    #keyhint-box {{
        width: auto;
        height: 1;
        color: {FG1};
        padding-left: 2;
        content-align: right middle;
    }}
    """

    def compose(self) -> ComposeResult:
        yield Static("YouTube", id="logo-box")
        yield Input(placeholder="Search YouTube... (Press / to focus)", id="search-box")
        yield Label("Feed: Home", id="breadcrumb-box")
        yield Label(Text("[/] Search  [Enter] Open  [c] Channel  [y] Yank  [q] Quit"), id="keyhint-box")

    def update_breadcrumb(self, text: str) -> None:
        try:
            self.query_one("#breadcrumb-box", Label).update(Text(text))
        except Exception:
            pass
