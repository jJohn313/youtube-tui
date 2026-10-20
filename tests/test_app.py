"""
Automated unit and integration tests for YouTube-TUI.
Tests the full lifecycle using Textual's headless test pilot.
"""

import asyncio
import sys
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from youtubetui.app import YouTubeTUIApp
from youtubetui.ui.feed import FeedPane
from youtubetui.ui.preview import PreviewPane
from youtubetui.ui.statusbar import StatusBar

async def test_app_startup_and_curated_feed():
    app = YouTubeTUIApp()
    async with app.run_test() as pilot:
        # Check initial widgets mounted
        assert app.query_one("#header-bar") is not None
        assert app.query_one("#nav-sidebar") is not None
        feed_pane = app.query_one("#feed-pane", FeedPane)
        preview_pane = app.query_one("#preview-pane", PreviewPane)
        status_bar = app.query_one("#status-bar", StatusBar)
        
        assert feed_pane is not None
        assert preview_pane is not None
        assert status_bar is not None
        
        # Wait for feed items to populate
        for _ in range(40):
            if len(feed_pane.items) > 0:
                break
            await pilot.pause(0.2)
        assert len(feed_pane.items) > 0
        await pilot.exit(None)

async def test_app_search_and_navigation():
    app = YouTubeTUIApp(initial_query="veritasium")
    async with app.run_test() as pilot:
        feed_pane = app.query_one("#feed-pane", FeedPane)
        for _ in range(40):
            if len(feed_pane.items) > 0:
                break
            await pilot.pause(0.2)
        assert len(feed_pane.items) > 0
        
        # Verify item types include video and channel
        item_types = {item["type"] for item in feed_pane.items}
        assert "video" in item_types

        # Test load_channel call
        await app.load_channel("UCHnyfMqiRRG1u-2MsSQLbXA", "Veritasium")
        assert getattr(feed_pane, "current_title") == "CHANNEL: VERITASIUM"

        # Navigate down
        await pilot.press("down")
        await pilot.pause(0.2)
        
        # Test ESC to restore previous results
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert len(feed_pane.items) > 0

        await pilot.exit(None)

async def test_auth_and_subscriptions():
    app = YouTubeTUIApp()
    async with app.run_test() as pilot:
        feed_pane = app.query_one("#feed-pane", FeedPane)
        for _ in range(40):
            if len(feed_pane.items) > 0:
                break
            await pilot.pause(0.2)
        assert len(feed_pane.items) > 0

        # Test loading subscriptions
        await app.load_subscriptions_feed()
        assert getattr(feed_pane, "current_title") == "SUBSCRIPTIONS FEED"
        assert len(feed_pane.items) > 0

        await pilot.exit(None)

if __name__ == "__main__":
    asyncio.run(test_app_startup_and_curated_feed())
    asyncio.run(test_app_search_and_navigation())
    asyncio.run(test_auth_and_subscriptions())
    print("✔ All headless integration tests passed!")
    asyncio.run(test_app_search_and_navigation())
    print("✔ All headless integration tests passed!")
