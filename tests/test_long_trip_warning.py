import graphhopper_enhanced as gh
from conftest import make_path


def test_short_trip_no_warning():
    assert gh.trip_warnings(make_path(), "car") == []


def test_long_trip_warning():
    path = make_path(distance_m=600_000, time_ms=10 * 3_600_000)
    assert "very long trip" in gh.trip_warnings(path, "car")[0]
