# 📺 YouTube TUI (youtube-tui)

A terminal-first, lightweight YouTube client for Linux recreating the YouTube web interface inside modern terminals like Kitty, Foot, and Ghostty with **Yazi-inspired** aesthetics, side-by-side video cards, and hardware-accelerated MPV streaming.

---

## ⚡ Features

- **YouTube Web Experience in Terminal**:
  - **2-Column Layout**: Clean split between the **Main Feed** on the left and the **Navigation & Quick Actions Pillar** on the right.
  - **Side-by-Side Video Cards**: Replicates the YouTube web layout — each card features a true-color thumbnail preview next to the title, channel name, duration badge, view count, and description snippet.
  - **Right Navigation Pillar**: Persistent right-hand pillar containing your categories (*My Home, Subscriptions, Watch History*), explore filters (*Videos, Channels, Playlists*), curated topics, account sync actions, and the **Quick Actions** reference box.
  - **Lain Color Aesthetic**: Directly mirrors Yazi's palette (`#000000` base, `#1A1A1A` panels, `#3A3A3A` borders, `#CE7688` rose highlights, `#C1B48E` gold cursor).
  - **100% Keyboard-Driven with Visible Highlighting**: Arrow keys (`Up`/`Down`) and Vi keys (`j`/`k`) navigate items with an unmistakable gold cursor border (`border-left: heavy #C1B48E`) and highlighted card styling. Switch columns smoothly with `h`/`l` or `Left`/`Right`.

- **Webflow & Browser Account Sync**:
  - **Webflow Integration**: Seamlessly syncs authenticated YouTube sessions from your custom **Webflow** web engine (`~/.local/share/webflow/storage/cookies.sqlite`) via <kbd>w</kbd> or from the right pillar.
  - **Zen Browser & Firefox**: Sync from Zen Browser (<kbd>a</kbd>) or Firefox with one keystroke without browser database locking conflicts.
  - **YouTube Premium Benefits**: Automatically attaches session credentials to MPV for ad-free playback, 4K VP9/AV1 video, and high-bitrate Opus audio.

- **Multi-Type Search & Infinite Scroll**:
  - Queries YouTube Innertube directly for **Videos**, **Channels**, and **Playlists** without API quotas.
  - **Infinite Scroll / Pagination**: Seamlessly fetches next batches on scrolling to feed end via YouTube continuation tokens.
  - **Search Filtering & Sorting**: Press <kbd>f</kbd> to filter searches by upload date, view count, live streams, shorts, and long-form videos.
  - **Channel Tabs**: Press <kbd>c</kbd> on a channel to browse and cycle between **Videos**, **Playlists**, and **Shorts** tabs.
  - **Top Comments Viewer**: Press <kbd>k</kbd> to inspect the top comments and discussions directly inside a modal.

- **Background Downloads & MPV Queueing**:
  - **MPV IPC Queueing**: Press <kbd>Q</kbd> to enqueue videos to your running MPV player instance on-the-fly without interrupting playback.
  - **Background Downloads**: Press <kbd>d</kbd> to download video or <kbd>D</kbd> to download audio (MP3) in background via `yt-dlp` with desktop notifications.

- **Watch History & Playlist Synchronization**:
  - **Persistent Watch History**: Automatically logs every video watched in YouTube TUI locally (`~/.config/youtube-tui/watch_history.json`) and merges with cloud YouTube Watch History (`FEhistory`).
  - **YouTube Playlist Synchronization**: Automatically pulls in all user playlists created on YouTube (`FEplaylist_aggregation`) under **My Playlists**.
  - **Custom Local Playlists & Cloud Sync**: Create custom playlists anytime via <kbd>b</kbd> and add videos to existing custom or synchronized YouTube playlists. Adding to YouTube playlists dispatches cloud sync requests directly to YouTube via Innertube.

- **Smart MPV Pipeline**:
  - Custom deduplicating wrapper (`~/.local/bin/mpv`) strips playlist tracking tokens and prevents redundant player windows by focusing existing Hyprland windows.

---

## 🛠 Dependencies

- **python-textual** (`extra/python-textual`)
- **mpv** (`extra/mpv`)
- **yt-dlp** (`yt-dlp`)
- **chafa** (`extra/chafa` for terminal graphics)
- **wl-clipboard** (`extra/wl-clipboard` for URL yank)
- **micro** (`extra/micro` default terminal text editor for description viewing)

---

## 🎮 Keybindings

| Key | Action |
| --- | --- |
| `h` / `l` or `Left` / `Right` | Switch focus between Main Feed and Right Navigation Pillar |
| `j` / `k` or `Down` / `Up` | Move cursor in list (with distinct active highlight) |
| `Enter` | Play video in MPV / Browse channel / Expand playlist / Activate nav item |
| `Q` / `Shift+Enter` | **Play Next / Queue**: Enqueue highlighted video to active MPV instance via IPC |
| `d` | **Download Video**: Background download video to `~/Downloads` via `yt-dlp` |
| `D` | **Download Audio**: Background download MP3 audio to `~/Downloads` via `yt-dlp` |
| `f` | **Filter Search**: Open modal to filter/sort results (Upload Date, Views, Live, Short, Long) |
| `k` | **View Comments**: View top comments modal for highlighted video |
| `/` | Focus search bar |
| `w` | Sync account from **Webflow** web engine |
| `a` | Sync account from **Zen Browser** |
| `c` | Browse channel / Cycle channel tabs (*Videos* -> *Playlists* -> *Shorts*) |
| `p` | Browse playlist of highlighted item |
| `b` | **Add to Playlist**: Add video to a custom or synchronized YouTube playlist, or create a new playlist |
| `m` | Play audio-only stream in MPV |
| `t` | View full description & links in `micro` (default terminal text editor) |
| `y` | Yank / Copy YouTube URL to clipboard (`wl-copy`) |
| `Esc` | Unfocus search bar / Return to previous search results |
| `r` | Refresh current feed or search |
| `1` – `8` | Jump directly to category (*Home, Subscriptions, History, Playlists, Trending, Tech, Music, Gaming*) |
| `Tab` / `Shift+Tab` | Cycle next / previous category |
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
