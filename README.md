# 📺 YouTube TUI (youtube-tui)

A terminal-first, lightweight YouTube client for Linux recreating the YouTube web interface inside modern terminals like Kitty, Foot, and Ghostty with **Yazi-inspired** aesthetics and hardware-accelerated MPV streaming.

---

## ⚡ Features

- **YouTube Web Experience in TUI**:
  - **3-Column Yazi Layout**: Left navigation drawer, center rich results feed, and right detailed metadata & thumbnail inspector.
  - **Lain Color Aesthetic**: Directly mirrors Yazi's palette (`#000000` base, `#1A1A1A` panels, `#3A3A3A` borders, `#CE7688` rose highlights, `#C1B48E` gold cursor).
  - **Multi-Type Search**: Instant search across **Videos**, **Channels**, and **Playlists** via Innertube API without API keys or browser engines.
  - **Channel & Playlist Browsing**: Select a channel to view their recent uploads, or expand a playlist into track lists.
- **True-Color Inline Thumbnails**:
  - High-resolution true-color terminal art rendered asynchronously via `chafa`.
  - Non-blocking background worker caching for zero-latency list navigation.
- **Smart MPV Pipeline**:
  - Custom deduplicating `mpv` wrapper strips playlist tracking tokens and prevents redundant windows by focusing existing Hyprland windows.
  - Hardware-accelerated VP9/AV1 + high-bitrate Opus streaming.
- **Vi Navigation & Keybindings**:
  - Full keyboard-driven navigation (`h`/`j`/`k`/`l`, `/`, `Enter`, `c`, `p`, `y`, `q`).

---

## 🛠 Dependencies

- **python-textual** (`extra/python-textual`)
- **mpv** (`extra/mpv`)
- **yt-dlp** (`yt-dlp`)
- **chafa** (`extra/chafa`)
- **wl-clipboard** (`extra/wl-clipboard` for URL yank)

---

## 🎮 Keybindings

| Key | Action |
| --- | --- |
| `/` | Focus search bar |
| `Enter` | Play video in MPV / Browse channel / Expand playlist |
| `c` | Browse channel of highlighted video |
| `p` | Browse playlist of highlighted item |
| `m` | Play audio-only stream in MPV |
| `y` | Yank / Copy YouTube URL to clipboard |
| `Esc` | Blur search / Return to previous search results |
| `r` | Refresh current feed or search |
| `j` / `k` / `Down` / `Up` | Move cursor in list |
| `h` / `l` / `Left` / `Right`| Switch between Sidebar and Feed |
| `?` | Show quick help |
| `q` | Quit |

---

## 🚀 Usage

```bash
# Launch interactive YouTube TUI
youtube

# Search YouTube directly from CLI
youtube "linux gaming benchmarks"
youtube "veritasium"

# Legacy ytfzf fallback (if desired)
youtube --legacy "ambient music"
```
