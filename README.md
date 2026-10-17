# 📺 YouTube in Terminal (youtube-tui) `[WIP]`

> ⚠️ **Status: Work In Progress (WIP)**  
> This tool is currently under active development and being consolidated into a standalone package. Core playback and search work, but additional features (playlist manager, history synchronization, and unified config) are in progress.

A terminal-first, lightweight YouTube search and streaming client for Linux. Built around `ytfzf`, `mpv`, and `yt-dlp` to deliver instantaneous video search with inline Kitty/Chafa thumbnail art and hardware-accelerated, ad-free streaming with zero browser overhead.

---

## ⚡ Features

- **Interactive Terminal Search**: Run `youtube "<query>"` or just `youtube` to fuzzy-search YouTube directly from your terminal.
- **True-Color Thumbnails**: Displays video previews in the terminal via `chafa` (compatible with Kitty, WezTerm, Ghostty, Foot, etc.).
- **Smart MPV Instance Manager**: Custom `mpv` wrapper cleans tracking tokens from URLs, strips playlist baggage for fast extraction, and prevents duplicate player windows by focusing the existing Hyprland window.
- **Zero Browser Memory**: Watch high-bitrate 4K/60fps VP9/AV1 videos using a fraction of the RAM of a modern web browser.
- **Direct Scraper**: Scrapes YouTube directly without relying on flaky or rate-limited public Invidious instances.

---

## 🛠 Dependencies

- **ytfzf** (`ytfzf` via AUR / package manager)
- **mpv** (`mpv`)
- **yt-dlp** (`yt-dlp`)
- **chafa** (`chafa` for terminal graphics)
- **jq** & **fzf**

---

## 🎮 Usage

```bash
# Search YouTube with interactive thumbnail browser
youtube "linux gaming benchmarks"

# Open interactive search prompt
youtube

# Play direct video URL through the smart deduplicating MPV wrapper
mpv "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

## 📂 Structure

```text
youtube-tui/
├── bin/
│   ├── youtube              # Search & thumbnail CLI wrapper
│   └── mpv                  # Smart deduplicator & Hyprland window focuser
├── config/
│   └── ytfzf/
│       └── conf.sh          # Scraper & playback configuration
└── README.md
```
