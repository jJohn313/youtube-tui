"""
Yazi-inspired theme definitions for YouTube-TUI.
Anchored directly to the Lain palette from ~/.config/yazi/theme.toml:
  bg0  = #000000 (backprimary)
  bg1  = #1A1A1A (backsecondary)
  bg2  = #2A2A2A (backtertiary)
  bg3  = #3A3A3A (backquaternary)
  fg0  = #CE7688 (foreprimary)
  fg1  = #A05969 (foretertiary)
  fg2  = #804654 (foresenary)
  acc0 = #C1B48E (highprimary)
  acc1 = #A49978 (hightertiary)
  peach= #FFDCB9 (selected/copied)
  red  = #930006 (cut/warning)
"""

# Palette Constants
BG0 = "#000000"
BG1 = "#1A1A1A"
BG2 = "#2A2A2A"
BG3 = "#3A3A3A"

FG0 = "#CE7688"
FG1 = "#A05969"
FG2 = "#804654"

ACC0 = "#C1B48E"
ACC1 = "#A49978"
PEACH = "#FFDCB9"
RED = "#930006"

# Powerline & Status ramp glyphs matching Yazi
RAMP_OPEN = "▓"
RAMP_CLOSE = "▓▒░"
BORDER_SYMBOL = "│"

# Type badges
BADGE_VIDEO = "[VID]"
BADGE_CHANNEL = "[CHN]"
BADGE_PLAYLIST = "[LIST]"

TCSS_THEME = f"""
Screen {{
    background: {BG0};
    color: {FG0};
}}

#app-grid {{
    layout: vertical;
    height: 100%;
    width: 100%;
    background: {BG0};
}}

#header-container {{
    dock: top;
    height: 3;
    background: {BG1};
    border-bottom: solid {BG3};
    padding: 0 1;
    layout: horizontal;
    align: left middle;
}}

#logo-badge {{
    width: 16;
    height: 1;
    background: {FG0};
    color: {BG0};
    text-style: bold;
    content-align: center middle;
    margin-right: 1;
}}

#search-input {{
    width: 1fr;
    height: 1;
    background: {BG2};
    border: none;
    color: {ACC0};
    padding: 0 1;
}}

#search-input:focus {{
    background: {BG3};
    color: {PEACH};
}}

#header-breadcrumbs {{
    width: auto;
    height: 1;
    color: {ACC1};
    text-style: bold;
    padding-left: 1;
}}

#header-keyhints {{
    width: auto;
    height: 1;
    color: {FG1};
    content-align: right middle;
    padding-right: 1;
}}

#main-columns {{
    layout: horizontal;
    height: 1fr;
    background: {BG0};
}}

#feed-container {{
    width: 1fr;
    height: 100%;
    background: {BG0};
    border-right: solid {BG3};
    layout: vertical;
}}

#feed-header {{
    height: 1;
    background: {BG1};
    color: {ACC0};
    text-style: bold;
    padding: 0 1;
    border-bottom: solid {BG3};
}}

#feed-list {{
    background: {BG0};
    border: none;
    height: 1fr;
    padding: 0;
}}

#feed-list > ListItem {{
    background: {BG0};
    border-bottom: solid {BG1};
    padding: 0 1;
    color: {FG0};
}}

#feed-list > ListItem:hover {{
    background: {BG1};
    color: {PEACH};
}}

#feed-list > ListItem.-highlight,
#feed-list > ListItem:focus,
#feed-list > ListItem.-selected {{
    background: {BG2};
    border-left: wide {ACC0};
    border-top: solid {BG3};
    border-bottom: solid {BG3};
}}

#feed-list > ListItem.-highlight .dim-text,
#feed-list > ListItem:focus .dim-text,
#feed-list > ListItem.-selected .dim-text {{
    color: {ACC0};
}}

#preview-container {{
    width: 48;
    height: 100%;
    background: {BG1};
    layout: vertical;
    padding: 0 1;
    overflow-y: auto;
}}

#preview-thumbnail-box {{
    height: 18;
    width: 100%;
    background: {BG0};
    border: round {BG3};
    margin-top: 1;
    align: center middle;
    content-align: center middle;
}}

#preview-title {{
    color: {ACC0};
    text-style: bold;
    margin-top: 1;
}}

#preview-channel {{
    color: {PEACH};
    text-style: bold;
    margin-top: 0;
}}

#preview-meta {{
    color: {FG1};
    margin-top: 0;
}}

#preview-divider {{
    color: {BG3};
    margin: 1 0;
}}

#preview-description {{
    color: {FG0};
    height: auto;
    overflow-y: auto;
}}

#preview-actions {{
    margin-top: 1;
    padding: 1;
    background: {BG2};
    border: round {BG3};
    color: {ACC0};
}}

#status-container {{
    dock: bottom;
    height: 1;
    background: {BG1};
    color: {FG0};
    layout: horizontal;
    border-top: solid {BG3};
}}

#status-mode {{
    width: 12;
    background: {FG0};
    color: {BG0};
    text-style: bold;
    content-align: center middle;
}}

#status-message {{
    width: 1fr;
    color: {ACC0};
    padding: 0 1;
}}

#status-right {{
    width: auto;
    color: {FG1};
    padding-right: 1;
}}

.loading-indicator {{
    color: {ACC0};
    text-style: italic;
    content-align: center middle;
    padding: 2;
}}
"""
