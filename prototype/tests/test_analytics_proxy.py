"""Deterministic test for the PostHog proxy's address mapping (no network)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics_proxy import target_url  # noqa: E402


def test_events_go_to_the_api_host():
    assert target_url("i/v0/e/", "compression=gzip-js") == "https://us.i.posthog.com/i/v0/e/?compression=gzip-js"
    assert target_url("flags/") == "https://us.i.posthog.com/flags/"


def test_javascript_files_come_from_the_asset_host():
    assert target_url("static/array.js") == "https://us-assets.i.posthog.com/static/array.js"
    assert target_url("array/phc_x/config.js") == "https://us-assets.i.posthog.com/array/phc_x/config.js"
