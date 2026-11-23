"""Tests for the Flask web version, using Flask's test client (no server, no real API)."""

import pytest

import graphhopper_enhanced as gh
import web_app
from conftest import BAGUIO, MANILA, make_path


@pytest.fixture
def client():
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


def test_home_page_loads(client):
    reply = client.get("/")
    assert reply.status_code == 200
    assert b"<html" in reply.data.lower()


def test_geocode_needs_a_place_name(client):
    reply = client.get("/api/geocode?q=")
    assert reply.status_code == 400
    assert reply.get_json()["error"] == "Please type a place name."


def test_geocode_returns_matches(client, monkeypatch):
    monkeypatch.setattr(gh, "find_locations",
                        lambda query, key: (200, [dict(MANILA, type="city", exact=True)], ""))
    data = client.get("/api/geocode?q=Manila").get_json()
    assert data["query"] == "Manila"
    assert data["matches"][0]["name"] == MANILA["name"]


def test_geocode_network_failure_is_502(client, monkeypatch):
    monkeypatch.setattr(gh, "find_locations", lambda query, key: (0, [], "Network problem"))
    assert client.get("/api/geocode?q=Manila").status_code == 502


@pytest.mark.parametrize("body, message", [
    ({}, "Choose both a starting location and a destination."),
    ({"from": MANILA, "to": BAGUIO, "vehicle": "truck"}, "Vehicle must be one of: car, bike, foot"),
    ({"from": MANILA, "to": BAGUIO, "units": "parsecs"}, "Units must be mi, km or both."),
])
def test_route_rejects_bad_requests(client, body, message):
    reply = client.post("/api/route", json=body)
    assert reply.status_code == 400
    assert reply.get_json()["error"] == message


def test_route_success(client, monkeypatch):
    path = make_path(260_619, 12_289_673)
    path["points"] = {"coordinates": [[120.98, 14.60], [120.60, 16.40]]}   # [lng, lat]
    monkeypatch.setattr(gh, "get_route", lambda *args, **kwargs: (200, {"paths": [path]}))

    reply = client.post("/api/route", json={"from": MANILA, "to": BAGUIO, "vehicle": "car", "units": "km"})
    data = reply.get_json()
    assert reply.status_code == 200
    assert data["distance"] == "260.6 km"
    assert data["duration"] == "3 hrs 24 mins"
    assert data["line"] == [[14.60, 120.98], [16.40, 120.60]]           # flipped to [lat, lng]
    assert len(data["steps"]) == 2
