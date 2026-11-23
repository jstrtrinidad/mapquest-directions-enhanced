"""Tests for the terminal prompts (input is faked) and the existing trip history."""

import json

import pytest

import graphhopper_enhanced as gh
from conftest import BAGUIO, MANILA, make_path


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("word", ["q", "Q", "quit", " exit "])
def test_ask_quits_on_quit_words(typed, word):
    typed(word)
    with pytest.raises(gh.QuitApp):
        gh.ask("> ")


def test_ask_strips_spaces(typed):
    typed("  Manila  ")
    assert gh.ask("> ") == "Manila"


@pytest.mark.parametrize("answer, expected", [
    ("", "both"), ("k", "km"), ("kilometers", "km"), ("Miles", "mi"), ("b", "both"),
])
def test_choose_units(typed, answer, expected):
    typed(answer)
    assert gh.choose_units() == expected


def test_choose_units_reasks_on_bad_input(typed, capsys):
    typed("lightyears", "km")
    assert gh.choose_units() == "km"
    assert "'lightyears' is not a unit" in capsys.readouterr().out


@pytest.mark.parametrize("answer, expected", [
    ("", "car"), ("walk", "foot"), ("bicycle", "bike"), ("h", "history"), ("u", "units"),
])
def test_choose_vehicle(typed, answer, expected):
    typed(answer)
    assert gh.choose_vehicle() == expected


def test_choose_vehicle_reasks_on_unknown_vehicle(typed, capsys):
    typed("truck", "car")
    assert gh.choose_vehicle() == "car"
    assert "'truck' is not a vehicle profile" in capsys.readouterr().out


def test_main_exits_cleanly_on_q(typed, capsys, monkeypatch):
    monkeypatch.setenv("GRAPHHOPPER_API_KEY", "")
    typed("q")
    gh.main()                                       # must not raise
    assert "Goodbye!" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Trip history
# --------------------------------------------------------------------------- #
def test_save_trip_creates_history(history_file):
    gh.save_trip(MANILA, BAGUIO, "car", make_path(260_619, 12_289_673))
    saved = json.loads(history_file.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["from"] == MANILA["name"]
    assert saved[0]["to"] == BAGUIO["name"]
    assert saved[0]["distance_m"] == 260_619
    assert saved[0]["duration_ms"] == 12_289_673


def test_save_trip_appends(history_file):
    gh.save_trip(MANILA, BAGUIO, "car", make_path())
    gh.save_trip(BAGUIO, MANILA, "bike", make_path())
    saved = json.loads(history_file.read_text(encoding="utf-8"))
    assert [trip["vehicle"] for trip in saved] == ["car", "bike"]


def test_show_history_when_empty(capsys):
    gh.show_history()
    assert "No trips saved yet." in capsys.readouterr().out


def test_show_history_lists_trips(capsys):
    gh.save_trip(MANILA, BAGUIO, "car", make_path(260_619, 12_289_673))
    gh.show_history()
    out = capsys.readouterr().out
    assert "Manila, Metro Manila, Philippines -> Baguio" in out
    assert "260.6 km" in out
    assert "3 hrs 24 mins" in out
