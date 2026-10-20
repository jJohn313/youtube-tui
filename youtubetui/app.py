"""
Main Textual Application for YouTube-TUI.
Unites 3-column Yazi layout with YouTube web interface capabilities,
supporting inline Chafa true-color thumbnails, video/channel/playlist searches,
and background smart-MPV streaming.
"""

import asyncio
import sys
from typing import Any, Dict, List, Optional
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, ListView
from youtubetui.api import (
    get_channel_videos, get_curated_feed, get_playlist_videos, search_youtube,
    get_home_feed, get_subscriptions_feed, get_history_feed
)
from youtubetui.auth import clear_session, is_authenticated, is_premium, sync_from_browser
from youtubetui.player import copy_to_clipboard, play_url
from youtubetui.theme import TCSS_THEME
from youtubetui.ui.feed import FeedItemWidget, FeedPane
from youtubetui.ui.header import HeaderBar
from youtubetui.ui.navigation import NavItem, NavigationSidebar
from youtubetui.ui.preview import PreviewPane
from youtubetui.ui.statusbar import StatusBar

class YouTubeTUIApp(App):
    """Aesthetic YouTube TUI client copying Yazi."""

    CSS = TCSS_THEME
    TITLE = "YouTube TUI"

    BINDINGS = [
        Binding("q", "quit_app", "Quit", show=True),
        Binding("/", "focus_search", "Search", show=True),
        Binding("escape", "escape_action", "Back/Normal", show=True),
        Binding("c", "open_channel", "Channel", show=True),
        Binding("p", "open_playlist", "Playlist", show=True),
        Binding("m", "play_audio", "Audio MPV", show=True),
        Binding("y", "yank_url", "Yank URL", show=True),
        Binding("a", "toggle_account_sync", "Account Sync", show=True),
        Binding("r", "refresh_feed", "Refresh", show=True),
        Binding("h", "focus_nav", "Sidebar", show=False),
        Binding("l", "focus_feed", "Feed", show=False),
        Binding("question_mark", "show_help", "Help", show=True),
    ]

    def __init__(self, initial_query: str = ""):
        super().__init__()
        self.initial_query = initial_query
        self.current_query = initial_query
        self.current_filter = "all"
        self.previous_results: List[Dict[str, Any]] = []
        self.previous_title: str = ""

    def compose(self) -> ComposeResult:
        yield HeaderBar(id="header-bar")
        with Horizontal(id="main-columns"):
            yield NavigationSidebar(id="nav-sidebar")
            yield FeedPane(id="feed-pane")
            yield PreviewPane(id="preview-pane")
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        """Initializes the view on startup."""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_mode("NORMAL")

        if self.initial_query:
            search_input = self.query_one("#search-box", Input)
            search_input.value = self.initial_query
            self.run_worker(self.perform_search(self.initial_query), exclusive=True)
        elif is_authenticated():
            self.run_worker(self.load_home_feed(), exclusive=True)
        else:
            self.run_worker(self.load_feed("trending", "Trending Feed"), exclusive=True)

        # Focus feed list by default
        self.query_one("#feed-list-view", ListView).focus()

    def action_quit_app(self) -> None:
        self.exit()

    def action_focus_search(self) -> None:
        """Focuses the top search bar and enters SEARCH mode."""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_mode("SEARCH")
        search_box = self.query_one("#search-box", Input)
        search_box.focus()

    def action_escape_action(self) -> None:
        """Handles Escape: returns from search or pops channel/playlist view."""
        search_box = self.query_one("#search-box", Input)
        if search_box.has_focus:
            search_box.blur()
            self.query_one("#feed-list-view", ListView).focus()
            self.query_one("#status-bar", StatusBar).set_mode("NORMAL")
            return

        # If we previously drilled into a channel or playlist, go back
        if self.previous_results:
            feed_pane = self.query_one("#feed-pane", FeedPane)
            feed_pane.populate(self.previous_results, self.previous_title or "SEARCH RESULTS")
            self.previous_results = []
            self.previous_title = ""
            self.query_one("#header-bar", HeaderBar).update_breadcrumb(f"Search: {self.current_query}")
            self.query_one("#status-bar", StatusBar).set_message("Restored previous search results")

    def action_focus_nav(self) -> None:
        self.query_one("#nav-list", ListView).focus()

    def action_focus_feed(self) -> None:
        self.query_one("#feed-list-view", ListView).focus()

    def get_selected_item(self) -> Optional[Dict[str, Any]]:
        """Returns the currently highlighted item from the center feed."""
        feed_pane = self.query_one("#feed-pane", FeedPane)
        list_view = self.query_one("#feed-list-view", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, FeedItemWidget):
            return list_view.highlighted_child.item_data
        if feed_pane.items and list_view.index is not None and 0 <= list_view.index < len(feed_pane.items):
            return feed_pane.items[list_view.index]
        return None

    def action_open_channel(self) -> None:
        """Navigates to the channel of the currently highlighted item."""
        item = self.get_selected_item()
        if not item:
            return
        ch_id = item.get("channel_id") or item.get("channel")
        if ch_id:
            self.run_worker(self.load_channel(ch_id, item.get("channel", "Channel")))

    def action_open_playlist(self) -> None:
        """Expands the playlist of the currently highlighted item."""
        item = self.get_selected_item()
        if not item:
            return
        if item.get("type") == "playlist":
            pid = item.get("id")
            if pid:
                self.run_worker(self.load_playlist(pid, item.get("title", "Playlist")))
        else:
            self.query_one("#status-bar", StatusBar).set_message("Selected item is not a playlist")

    def action_play_audio(self) -> None:
        """Dispatches audio-only MPV playback."""
        item = self.get_selected_item()
        if not item or item.get("type") != "video":
            self.query_one("#status-bar", StatusBar).set_message("Select a video to play audio")
            return
        ok, msg = play_url(item["url"], audio_only=True)
        self.query_one("#status-bar", StatusBar).set_message(msg)

    def action_yank_url(self) -> None:
        """Copies the URL of the active item to the clipboard."""
        item = self.get_selected_item()
        if not item:
            return
        url = item.get("url", "")
        ok, msg = copy_to_clipboard(url)
        self.query_one("#status-bar", StatusBar).set_message(f"{msg}: {url}")

    def action_refresh_feed(self) -> None:
        """Reloads the current search or feed."""
        if self.current_query:
            self.run_worker(self.perform_search(self.current_query))
        else:
            self.run_worker(self.load_feed("trending", "Trending Feed"))

    def action_toggle_account_sync(self) -> None:
        """Toggles / triggers browser account synchronization."""
        self.run_worker(self.sync_account_from_browser("zen"), exclusive=True)

    async def sync_account_from_browser(self, browser: str = "zen") -> None:
        """Syncs YouTube login session from browser."""
        status_bar = self.query_one("#status-bar", StatusBar)
        header_bar = self.query_one("#header-bar", HeaderBar)
        
        status_bar.set_message(f"Connecting YouTube account from {browser} browser...")
        loop = asyncio.get_running_loop()
        ok, msg = await loop.run_in_executor(None, sync_from_browser, browser)
        
        status_bar.set_message(msg)
        header_bar.update_account_status()
        
        if ok:
            await self.load_home_feed()

    def action_show_help(self) -> None:
        msg = "[/] Search  [Enter] Play/Open  [a] Sync Account  [c] Channel  [p] Playlist  [m] Audio  [y] Yank  [r] Refresh  [q] Quit"
        self.query_one("#status-bar", StatusBar).set_message(msg)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handles submission from the top search bar."""
        query = event.value.strip()
        if query:
            self.current_query = query
            self.query_one("#status-bar", StatusBar).set_mode("NORMAL")
            event.input.blur()
            self.query_one("#feed-list-view", ListView).focus()
            await self.perform_search(query)

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Fires when cursor moves across items in the feed."""
        if event.list_view.id == "feed-list-view":
            feed_pane = self.query_one("#feed-pane", FeedPane)
            preview_pane = self.query_one("#preview-pane", PreviewPane)
            status_bar = self.query_one("#status-bar", StatusBar)
            
            idx = event.list_view.index if event.list_view.index is not None else 0
            total = len(feed_pane.items)
            status_bar.set_counter(idx + 1 if total else 0, total)

            if isinstance(event.item, FeedItemWidget):
                item = event.item.item_data
                status_bar.set_message(item.get("title", ""))
                await preview_pane.update_item(item)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Fires when Enter is pressed on an item."""
        if event.list_view.id == "feed-list-view" and isinstance(event.item, FeedItemWidget):
            item = event.item.item_data
            item_type = item.get("type", "video")

            if item_type == "video":
                # Launch Smart MPV
                status_bar = self.query_one("#status-bar", StatusBar)
                status_bar.set_mode("PLAYING")
                ok, msg = play_url(item.get("url", ""))
                status_bar.set_message(msg)
                await asyncio.sleep(2)
                status_bar.set_mode("NORMAL")

            elif item_type == "channel":
                # Open channel uploads
                cid = item.get("channel_id") or item.get("id")
                await self.load_channel(cid, item.get("title", "Channel"))

            elif item_type == "playlist":
                # Open playlist videos
                pid = item.get("id")
                await self.load_playlist(pid, item.get("title", "Playlist"))

        elif event.list_view.id == "nav-list" and isinstance(event.item, NavItem):
            item_id = event.item.item_id
            if item_id == "feed_home":
                await self.load_home_feed()
            elif item_id == "feed_subs":
                await self.load_subscriptions_feed()
            elif item_id == "feed_history":
                await self.load_history_feed()
            elif item_id == "explore_all":
                self.current_filter = "all"
                if self.current_query:
                    await self.perform_search(self.current_query)
            elif item_id == "explore_videos":
                self.current_filter = "videos"
                if self.current_query:
                    await self.perform_search(self.current_query)
            elif item_id == "explore_channels":
                self.current_filter = "channels"
                if self.current_query:
                    await self.perform_search(self.current_query)
            elif item_id == "explore_playlists":
                self.current_filter = "playlists"
                if self.current_query:
                    await self.perform_search(self.current_query)
            elif item_id == "action_sync_zen":
                await self.sync_account_from_browser("zen")
            elif item_id == "action_sync_firefox":
                await self.sync_account_from_browser("firefox")
            elif item_id == "action_sign_out":
                clear_session()
                self.query_one("#header-bar", HeaderBar).update_account_status()
                self.query_one("#status-bar", StatusBar).set_message("Signed out. Switched to Guest mode.")
                await self.load_feed("trending", "Trending Feed")
            elif item_id.startswith("feed_"):
                cat = item_id.replace("feed_", "")
                await self.load_feed(cat, event.item.raw_label.strip())
            
            self.query_one("#feed-list-view", ListView).focus()

    async def perform_search(self, query: str) -> None:
        """Executes YouTube Innertube search across videos, channels, and playlists."""
        status_bar = self.query_one("#status-bar", StatusBar)
        header_bar = self.query_one("#header-bar", HeaderBar)
        feed_pane = self.query_one("#feed-pane", FeedPane)

        status_bar.set_message(f"Searching for '{query}'...")
        header_bar.update_breadcrumb(f"Search: {query} [{self.current_filter.upper()}]")

        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, search_youtube, query, self.current_filter)

        feed_pane.populate(results, title=f"SEARCH: {query.upper()}")
        status_bar.set_message(f"Loaded {len(results)} items for '{query}'")

        if results:
            preview_pane = self.query_one("#preview-pane", PreviewPane)
            await preview_pane.update_item(results[0])

    async def load_channel(self, channel_id: str, channel_name: str) -> None:
        """Loads a channel's uploaded videos into the center feed."""
        feed_pane = self.query_one("#feed-pane", FeedPane)
        status_bar = self.query_one("#status-bar", StatusBar)
        header_bar = self.query_one("#header-bar", HeaderBar)

        # Stash current search results for Back/Esc
        self.previous_results = list(feed_pane.items)
        self.previous_title = getattr(feed_pane, "current_title", "SEARCH RESULTS")

        status_bar.set_message(f"Loading uploads for {channel_name}...")
        header_bar.update_breadcrumb(f"Channel: {channel_name}")

        loop = asyncio.get_running_loop()
        videos = await loop.run_in_executor(None, get_channel_videos, channel_id)

        feed_pane.populate(videos, title=f"CHANNEL: {channel_name.upper()}")
        status_bar.set_message(f"Loaded {len(videos)} videos from {channel_name}")

        if videos:
            preview_pane = self.query_one("#preview-pane", PreviewPane)
            await preview_pane.update_item(videos[0])

    async def load_playlist(self, playlist_id: str, playlist_name: str) -> None:
        """Loads a playlist's video items into the center feed."""
        feed_pane = self.query_one("#feed-pane", FeedPane)
        status_bar = self.query_one("#status-bar", StatusBar)
        header_bar = self.query_one("#header-bar", HeaderBar)

        # Stash current search results for Back/Esc
        self.previous_results = list(feed_pane.items)
        self.previous_title = getattr(feed_pane, "current_title", "SEARCH RESULTS")

        status_bar.set_message(f"Loading playlist {playlist_name}...")
        header_bar.update_breadcrumb(f"Playlist: {playlist_name}")

        loop = asyncio.get_running_loop()
        videos = await loop.run_in_executor(None, get_playlist_videos, playlist_id)

        feed_pane.populate(videos, title=f"PLAYLIST: {playlist_name.upper()}")
        status_bar.set_message(f"Loaded {len(videos)} items from playlist")

        if videos:
            preview_pane = self.query_one("#preview-pane", PreviewPane)
            await preview_pane.update_item(videos[0])

    async def load_home_feed(self) -> None:
        """Loads personalized YouTube Home recommendations."""
        feed_pane = self.query_one("#feed-pane", FeedPane)
        status_bar = self.query_one("#status-bar", StatusBar)
        header_bar = self.query_one("#header-bar", HeaderBar)

        status_bar.set_message("Loading personalized Home feed...")
        header_bar.update_breadcrumb("Feed: My Home")

        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, get_home_feed)

        feed_pane.populate(items, title="MY HOME FEED")
        status_bar.set_message(f"Loaded {len(items)} personalized recommendations")

        if items:
            preview_pane = self.query_one("#preview-pane", PreviewPane)
            await preview_pane.update_item(items[0])

    async def load_subscriptions_feed(self) -> None:
        """Loads latest uploads from subscribed channels."""
        feed_pane = self.query_one("#feed-pane", FeedPane)
        status_bar = self.query_one("#status-bar", StatusBar)
        header_bar = self.query_one("#header-bar", HeaderBar)

        status_bar.set_message("Loading Subscriptions feed...")
        header_bar.update_breadcrumb("Feed: Subscriptions")

        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, get_subscriptions_feed)

        if not items:
            status_bar.set_message("No subscriptions found. Please sync your YouTube account via 'a'.")
            return

        feed_pane.populate(items, title="SUBSCRIPTIONS FEED")
        status_bar.set_message(f"Loaded {len(items)} recent uploads from your subscriptions")

        if items:
            preview_pane = self.query_one("#preview-pane", PreviewPane)
            await preview_pane.update_item(items[0])

    async def load_history_feed(self) -> None:
        """Loads user watch history."""
        feed_pane = self.query_one("#feed-pane", FeedPane)
        status_bar = self.query_one("#status-bar", StatusBar)
        header_bar = self.query_one("#header-bar", HeaderBar)

        status_bar.set_message("Loading Watch History...")
        header_bar.update_breadcrumb("Feed: Watch History")

        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, get_history_feed)

        if not items:
            status_bar.set_message("No watch history found. Please sync your YouTube account via 'a'.")
            return

        feed_pane.populate(items, title="WATCH HISTORY")
        status_bar.set_message(f"Loaded {len(items)} videos from watch history")

        if items:
            preview_pane = self.query_one("#preview-pane", PreviewPane)
            await preview_pane.update_item(items[0])

    async def load_feed(self, category: str, label: str) -> None:
        """Loads curated feed topics."""
        feed_pane = self.query_one("#feed-pane", FeedPane)
        status_bar = self.query_one("#status-bar", StatusBar)
        header_bar = self.query_one("#header-bar", HeaderBar)

        status_bar.set_message(f"Loading {label}...")
        header_bar.update_breadcrumb(f"Feed: {label}")

        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, get_curated_feed, category)

        feed_pane.populate(items, title=f"FEED: {label.upper()}")
        status_bar.set_message(f"Loaded {len(items)} items in {label}")

        if items:
            preview_pane = self.query_one("#preview-pane", PreviewPane)
            await preview_pane.update_item(items[0])

def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    app = YouTubeTUIApp(initial_query=query)
    app.run()

if __name__ == "__main__":
    main()
