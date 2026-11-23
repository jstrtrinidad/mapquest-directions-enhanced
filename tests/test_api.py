"""Tests for the API layer: safe requests, the Luzon filter, geocoding, key check and routing.
Every Graphhopper reply here is fake, so no API key or internet is needed."""

import pytest
import requests

import graphhopper_enhanced as gh
from conftest import BAGUIO, MANILA, hit


# --------------------------------------------------------------------------- #
# api_get - never crashes on network problems
# --------------------------------------------------------------------------- #
class FakeReply:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def test_api_get_returns_status_and_json(monkeypatch):
    monkeypatch.setattr(gh.requests, "get", lambda url, timeout: FakeReply(200, {"hits": []}))
    assert gh.api_get("https://example") == (200, {"hits": []})


def test_api_get_timeout_gives_status_zero(monkeypatch):
    def slow(url, timeout):
        raise requests.exceptions.Timeout
    monkeypatch.setattr(gh.requests, "get", slow)
    status, data = gh.api_get("https://example")
    assert status == 0
    assert "Timeout" in data["message"]


def test_api_get_handles_non_json_reply(monkeypatch):
    monkeypatch.setattr(gh.requests, "get", lambda url, timeout: FakeReply(502, ValueError()))
    assert gh.api_get("https://example") == (502, {"message": "Server did not return JSON"})


# --------------------------------------------------------------------------- #
# in_luzon - the service area
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("place, lat, lng", [
    ("Manila", 14.5995, 120.9842),
    ("Baguio", 16.4023, 120.5960),
    ("Tuguegarao", 17.6132, 121.7270),
    ("Naga", 13.6218, 123.1948),
])
def test_in_luzon_accepts_mainland_luzon(place, lat, lng):
    assert gh.in_luzon(lat, lng), place


@pytest.mark.parametrize("place, lat, lng", [
    ("Cebu City", 10.3157, 123.8854),
    ("Davao City", 7.1907, 125.4553),
    ("Calapan, Mindoro", 13.4115, 121.1803),
    ("Puerto Princesa", 9.7392, 118.7353),
    ("Tokyo", 35.6762, 139.6503),
])
def test_in_luzon_rejects_places_outside(place, lat, lng):
    assert not gh.in_luzon(lat, lng), place


# --------------------------------------------------------------------------- #
# find_locations
# --------------------------------------------------------------------------- #
def test_find_locations_keeps_luzon_matches(fake_api):
    fake_api.replies = [(200, {"hits": [hit("Manila", 14.5995, 120.9842, "Metro Manila")]})]
    status, matches, message = gh.find_locations("Manila", "KEY")
    assert status == 200 and message == ""
    assert matches[0]["name"] == "Manila, Metro Manila, Philippines"
    assert matches[0]["exact"] is True
    assert "point=15.5%2C121.0" in fake_api.urls[0]              # Luzon search bias


def test_find_locations_rejects_outside_luzon(fake_api):
    cebu = {"hits": [hit("Cebu City", 10.3157, 123.8854, "Central Visayas")]}
    fake_api.replies = [(200, cebu), (200, cebu)]                 # second try adds ", Philippines"
    status, matches, message = gh.find_locations("Cebu City", "KEY")
    assert matches == []
    assert "outside Luzon" in message
    assert "Philippines" in fake_api.urls[1]


def test_find_locations_not_found(fake_api):
    fake_api.replies = [(200, {"hits": []}), (200, {"hits": []})]
    status, matches, message = gh.find_locations("xyzabc", "KEY")
    assert (status, matches) == (200, [])
    assert message == "No place found for 'xyzabc'"


def test_find_locations_removes_duplicates_and_flags_inexact(fake_api):
    same = hit("Quezon City", 14.676, 121.0437, "Metro Manila")
    fake_api.replies = [(200, {"hits": [same, same]})]
    _, matches, _ = gh.find_locations("QC", "KEY")
    assert len(matches) == 1
    assert matches[0]["exact"] is False                          # "QC" is not in the name


def test_find_locations_passes_api_errors_through(fake_api):
    fake_api.replies = [(401, {"message": "Wrong credentials"})]
    assert gh.find_locations("Manila", "BAD") == (401, [], "Wrong credentials")


# --------------------------------------------------------------------------- #
# check_api_key
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("reply, expected", [
    ((200, {"hits": [hit("Manila", 14.5995, 120.9842)]}), True),
    ((401, {"message": "Wrong credentials"}), False),
    ((0, {"message": "Network problem: ConnectionError"}), None),
])
def test_check_api_key(fake_api, reply, expected):
    fake_api.replies = [reply]
    ok, _ = gh.check_api_key("KEY")
    assert ok is expected


# --------------------------------------------------------------------------- #
# get_route
# --------------------------------------------------------------------------- #
def test_get_route_builds_the_request(fake_api):
    fake_api.replies = [(200, {"paths": []})]
    gh.get_route(MANILA, BAGUIO, "bike", "KEY")
    url = fake_api.urls[0]
    assert url.startswith(gh.ROUTE_URL)
    assert "vehicle=bike" in url
    assert "point=14.5995%2C120.9842&point=16.4023%2C120.596" in url
    assert "points_encoded" not in url


def test_get_route_with_points_for_the_web_map(fake_api):
    fake_api.replies = [(200, {"paths": []})]
    gh.get_route(MANILA, BAGUIO, "car", "KEY", with_points=True)
    assert "points_encoded=false" in fake_api.urls[0]
