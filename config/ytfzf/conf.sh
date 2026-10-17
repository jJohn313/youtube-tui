# Use smart mpv wrapper as the media player
video_player="/home/john/.local/bin/mpv"

# Use direct YouTube scraper (bypasses unreliable/dead Invidious instances)
scrape="yt"

# Enable thumbnails by default
show_thumbnails=1

# Thumbnail viewer (chafa works across terminals including kitty)
thumbnail_viewer="chafa"

# Ensure highest video and audio quality with VP9 preference for instant, smooth streaming
ytdl_pref="bestvideo[vcodec^=vp9]+bestaudio/bestvideo+bestaudio/best"
