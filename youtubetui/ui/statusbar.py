"""
Bottom status bar widget mirroring Yazi's status bar.
Displays active mode, status notifications, item counters, and player engine status.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Static
from youtubetui.theme import ACC0, ACC1, BG0, BG1, BG2, BG3, FG0, FG1

class StatusBar(Horizontal):
    """Bottom status bar with Yazi styling."""

    DEFAULT_CSS = f"""
    StatusBar {{
        dock: bottom;
        height: 1;
        background: {BG1};
        color: {FG0};
        border-top: solid {BG3};
        layout: horizontal;
    }}
    #status-mode-box {{
        width: 10;
        background: {FG0};
        color: {BG0};
        text-style: bold;
        content-align: center middle;
    }}
    #status-msg-box {{
        width: 1fr;
        color: {ACC0};
        padding: 0 1;
    }}
    #status-engine-box {{
        width: auto;
        color: {FG1};
        padding-right: 1;
    }}
    #status-counter-box {{
        width: auto;
        color: {ACC1};
        padding-right: 1;
        text-style: bold;
    }}
    """

    def compose(self) -> ComposeResult:
        yield Static("NORMAL", id="status-mode-box")
        yield Label("Ready", id="status-msg-box")
        yield Label("VP9 + Opus | MPV Smart-Dedup", id="status-engine-box")
        yield Label("0/0", id="status-counter-box")

    def set_mode(self, mode: str) -> None:
        mode_box = self.query_one("#status-mode-box", Static)
        mode_box.update(mode.upper())
        if mode.upper() == "SEARCH":
            mode_box.styles.background = ACC0
            mode_box.styles.color = BG0
        elif mode.upper() == "PLAYING":
            mode_box.styles.background = "#FFDCB9"
            mode_box.styles.color = BG0
        else:
            mode_box.styles.background = FG0
            mode_box.styles.color = BG0

    def set_message(self, msg: str) -> None:
        self.query_one("#status-msg-box", Label).update(Text(str(msg)))

    def set_counter(self, current: int, total: int) -> None:
        self.query_one("#status-counter-box", Label).update(f"{current}/{total}")
