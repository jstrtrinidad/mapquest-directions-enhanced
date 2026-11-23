"""Tests for the existing formatting helpers: durations, distances and arrival time."""

from datetime import datetime

import pytest

import graphhopper_enhanced as gh


@pytest.mark.parametrize("number, word, expected", [
    (1, "hr", "1 hr"),
    (3, "hr", "3 hrs"),
    (0, "min", "0 mins"),
])
def test_plural(number, word, expected):
    assert gh.plural(number, word) == expected


@pytest.mark.parametrize("milliseconds, expected", [
    (12_289_673, "3 hrs 24 mins"),                  # Manila -> Baguio by car
    (45_000, "45 secs"),                            # under a minute
    (60_000, "1 min"),
    (3_600_000, "1 hr"),
    (364_680_000, "4 days 5 hrs 18 mins"),
    (0, "0 secs"),
])
def test_format_duration(milliseconds, expected):
    assert gh.format_duration(milliseconds) == expected


@pytest.mark.parametrize("meters, expected", [
    (450, "450 m"),
    (999, "999 m"),
    (1000, "1.0 km"),
    (12_345, "12.3 km"),
])
def test_metric_text(meters, expected):
    assert gh.metric_text(meters) == expected


@pytest.mark.parametrize("meters, expected", [
    (45, "148 ft"),                                 # short steps show feet, not "0.0 mi"
    (1609.344, "1.0 mi"),
    (12_230, "7.6 mi"),
])
def test_imperial_text(meters, expected):
    assert gh.imperial_text(meters) == expected


def test_format_distance_units():
    assert gh.format_distance(12_230, "km") == "12.2 km"
    assert gh.format_distance(12_230, "mi") == "7.6 mi"
    assert gh.format_distance(12_230, "both") == "7.6 mi / 12.2 km"


def test_format_eta_adds_trip_time_to_now(monkeypatch):
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 23, 8, 0)
    monkeypatch.setattr(gh, "datetime", FixedClock)
    assert gh.format_eta(90 * 60 * 1000) == "Mon 23 Nov 2026, 09:30 AM"
