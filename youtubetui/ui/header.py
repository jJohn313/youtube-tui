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
    #account-badge {{
        width: auto;
        height: 1;
        padding: 0 1;
        margin-right: 1;
        text-style: bold;
        content-align: center middle;
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
        from youtubetui.auth import is_authenticated, is_premium
        yield Static("YouTube", id="logo-box")
        
        badge_text, badge_style = self._get_badge_info(is_authenticated(), is_premium())
        yield Static(badge_text, id="account-badge")
        
        yield Input(placeholder="Search YouTube... (Press / to focus)", id="search-box")
        yield Label("Feed: Home", id="breadcrumb-box")
        yield Label(Text("[/] Search  [Enter] Open  [c] Channel  [a] Account  [y] Yank  [q] Quit"), id="keyhint-box")

    def _get_badge_info(self, authenticated: bool, premium: bool) -> tuple[Text, str]:
        if premium:
            return Text("★ PREMIUM", style=f"bold {ACC0}"), f"background: {BG2}; color: {ACC0};"
        elif authenticated:
            return Text("● SIGNED IN", style=f"bold {FG0}"), f"background: {BG2}; color: {FG0};"
        else:
            return Text("○ GUEST", style=FG1), f"background: {BG1}; color: {FG1};"

    def update_account_status(self) -> None:
        """Refreshes the account status badge."""
        from youtubetui.auth import is_authenticated, is_premium
        badge_text, _ = self._get_badge_info(is_authenticated(), is_premium())
        try:
            self.query_one("#account-badge", Static).update(badge_text)
        except Exception:
            pass

    def update_breadcrumb(self, text: str) -> None:
        try:
            self.query_one("#breadcrumb-box", Label).update(Text(text))
        except Exception:
            pass
