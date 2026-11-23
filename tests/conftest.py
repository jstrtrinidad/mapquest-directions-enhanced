"""
Shared test setup for the 3Bytes Route Planner.

- Puts app/ on the import path so tests can `import graphhopper_enhanced`.
- Blocks real internet access: every Graphhopper call must be faked, so the
  tests run without an API key (locally and on GitHub Actions).
- Gives each test its own empty trip_history.json in a temporary folder.
"""

import os
import sys

import pytest

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP_DIR)

import graphhopper_enhanced as gh  # noqa: E402  (needs the path above)


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """Fail loudly if any test tries to reach the real Graphhopper API."""
    def refuse(*args, **kwargs):
        raise AssertionError("A test tried to use the real internet - fake the API call instead")
    monkeypatch.setattr(gh.requests, "get", refuse)


@pytest.fixture(autouse=True)
def history_file(tmp_path, monkeypatch):
    """Point HISTORY_FILE at a temporary file so tests never touch the real history."""
    path = tmp_path / "trip_history.json"
    monkeypatch.setattr(gh, "HISTORY_FILE", str(path))
    return path


@pytest.fixture
def fake_api(monkeypatch):
    """
    Replace api_get with canned replies.
    Usage: fake_api.replies = [(200, {...}), (401, {...})]; the URLs asked for
    end up in fake_api.urls.
    """
    class FakeApi:
        def __init__(self):
            self.replies = []
            self.urls = []

        def __call__(self, url):
            self.urls.append(url)
            if not self.replies:
                raise AssertionError("api_get called more times than the test expected")
            return self.replies.pop(0)

    fake = FakeApi()
    monkeypatch.setattr(gh, "api_get", fake)
    return fake


@pytest.fixture
def typed(monkeypatch):
    """Feed answers to input(): typed("car", "q") makes the next input() calls return them."""
    def feed(*answers):
        queue = list(answers)

        def fake_input(prompt=""):
            if not queue:
                raise EOFError
            return queue.pop(0)
        monkeypatch.setattr("builtins.input", fake_input)
    return feed


def hit(name, lat, lng, state="", country="Philippines", kind="city"):
    """One Geocoding API hit, shaped like Graphhopper's reply."""
    return {"name": name, "state": state, "country": country,
            "point": {"lat": lat, "lng": lng}, "osm_value": kind}


def make_path(distance_m=12000, time_ms=1_200_000, steps=None):
    """One Routing API path, shaped like Graphhopper's reply."""
    if steps is None:
        steps = [{"text": "Continue onto EDSA", "distance": distance_m},
                 {"text": "Arrive at destination", "distance": 0}]
    return {"distance": distance_m, "time": time_ms, "instructions": steps}


MANILA = {"name": "Manila, Metro Manila, Philippines", "lat": 14.5995, "lng": 120.9842}
BAGUIO = {"name": "Baguio, Cordillera Administrative Region, Philippines",
          "lat": 16.4023, "lng": 120.5960}
