# 📺 YouTube TUI (youtube-tui)

A terminal-first, lightweight YouTube client for Linux recreating the YouTube web interface inside modern terminals like Kitty, Foot, and Ghostty with **Yazi-inspired** aesthetics, side-by-side video cards, and hardware-accelerated MPV streaming.

---

## ⚡ Features

- **YouTube Web Experience in Terminal**:
  - **2-Column Layout**: Left navigation sidebar eliminated for maximum horizontal space. Clean split between the **Main Feed** (with side-by-side thumbnails and metadata) and the **Detail & Actions Inspector** on the right.
  - **Lain Color Aesthetic**: Directly mirrors Yazi's palette (`#000000` base, `#1A1A1A` panels, `#3A3A3A` borders, `#CE7688` rose highlights, `#C1B48E` gold cursor).
  - **Side-by-Side Video Cards**: Replicates the YouTube web layout — each card features a true-color thumbnail preview next to the title, channel name, duration badge, view count, and description snippet.
  - **100% Keyboard-Driven with Visible Highlighting**: Arrow keys (`Up`/`Down`) and Vi keys (`j`/`k`) navigate items with an unmistakable gold cursor border (`border-left: wide #C1B48E`) and highlighted card styling.
  - **Interactive Category Bar**: Switch instantly between feeds using number keys `1`-`7` or cycle with `Tab` / `Shift+Tab`:
    - `[1] Home`: Your algorithmic YouTube recommendation feed.
    - `[2] Subscriptions`: Live recent uploads from channels you follow.
    - `[3] History`: Your synchronized YouTube watch history.
    - `[4] Trending`: Global popular videos and breaking content.
    - `[5] Tech`: Technology, Linux, and FOSS topics.
    - `[6] Music`: Lofi, ambient, and synthwave study streams.
    - `[7] Gaming`: Benchmarks and gameplay.

- **Webflow & Browser Account Sync**:
  - **Webflow Integration**: Seamlessly syncs authenticated YouTube sessions from your custom **Webflow** web engine (`~/.local/share/webflow/storage/cookies.sqlite`) via <kbd>w</kbd>.
  - **Zen Browser & Firefox**: Sync from Zen Browser (<kbd>a</kbd>) or Firefox with one keystroke without browser database locking conflicts.
  - **YouTube Premium Benefits**: Automatically attaches session credentials to MPV for ad-free playback, 4K VP9/AV1 video, and high-bitrate Opus audio.

- **Multi-Type Search**:
  - Queries YouTube Innertube directly for **Videos**, **Channels**, and **Playlists** without API quotas.
  - Selecting a channel (<kbd>c</kbd> or <kbd>Enter</kbd>) loads their upload feed.
  - Selecting a playlist (<kbd>p</kbd> or <kbd>Enter</kbd>) expands all playlist video items.

- **Smart MPV Pipeline**:
  - Custom deduplicating wrapper (`~/.local/bin/mpv`) strips playlist tracking tokens and prevents redundant player windows by focusing existing Hyprland windows.

---

## 🛠 Dependencies

- **python-textual** (`extra/python-textual`)
- **mpv** (`extra/mpv`)
- **yt-dlp** (`yt-dlp`)
- **chafa** (`extra/chafa` for terminal graphics)
- **wl-clipboard** (`extra/wl-clipboard` for URL yank)

---

## 🎮 Keybindings

| Key | Action |
| --- | --- |
| `1` – `7` | Jump directly to category (*Home, Subscriptions, History, Trending, Tech, Music, Gaming*) |
| `Tab` / `Shift+Tab` | Cycle next / previous category |
| `/` | Focus search bar |
| `Enter` | Play video in MPV / Browse channel / Expand playlist |
| `w` | Sync account from **Webflow** web engine |
| `a` | Sync account from **Zen Browser** |
| `c` | Browse channel of highlighted video |
| `p` | Browse playlist of highlighted item |
| `m` | Play audio-only stream in MPV |
| `y` | Yank / Copy YouTube URL to clipboard (`wl-copy`) |
| `Esc` | Unfocus search bar / Return to previous search results |
| `r` | Refresh current feed or search |
| `j` / `k` or `Down` / `Up` | Move cursor in feed list (with distinct active highlight) |
| `?` | Show quick help |
| `q` | Quit |

---

## 🚀 Usage

```bash
# Launch interactive YouTube TUI
youtube

# Search YouTube directly from CLI
youtube "arch linux gaming"
youtube "veritasium"

# Legacy ytfzf fallback (if desired)
youtube --legacy "ambient music"
```
