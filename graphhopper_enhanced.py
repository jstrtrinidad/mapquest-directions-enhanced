"""
3Bytes - Enhanced Graphhopper Directions Application
====================================================
Project Activity 3, Option 1: feature enhancements of the Lab 4.9.2 code.

WHAT THIS PROGRAM DOES
    Asks the user for a vehicle profile, a starting location and a destination,
    then uses the Graphhopper Geocoding API (place name -> latitude/longitude) and
    the Graphhopper Routing API (two points -> route) to print a trip summary and
    turn-by-turn directions.

ENHANCEMENTS OVER THE LAB 4.9.2 CODE
    1. API key is read from the GRAPHHOPPER_API_KEY environment variable
       (or asked at start-up) instead of being hard-coded in the source.
    2. Unit choice: miles, kilometres, or both.
    3. Colour-coded output (ANSI colours; automatically off if unsupported).
    4. Directions printed as an aligned table with step numbers.
    5. Estimated arrival time based on the current local time.
    6. Trip history saved to trip_history.json and viewable with "h".
    7. Network errors/timeouts are caught, so the program no longer crashes.
    8. Code split into small, documented functions for easy hand-over.

HOW TO RUN
    pip install requests
    set GRAPHHOPPER_API_KEY=your_key      (Windows)   /   export ... (Linux/macOS)
    python graphhopper_enhanced.py
    Type q or quit at any prompt to exit; type h at the vehicle prompt for history.

HOW TO CONTINUE THE PROJECT
    See BACKLOG.md. Each feature lives in its own function (see the index below),
    so a new feature normally means one new function plus one call in main().

FUNCTION INDEX
    supports_color / paint ... colour helpers
    get_api_key .............. load the API key
    geocoding ................ Geocoding API call, returns a dict
    get_route ................ Routing API call, returns (status, json)
    format_duration .......... milliseconds -> hh:mm:ss
    format_distance .......... metres -> text in the chosen unit
    print_trip ............... prints summary + directions table
    save_trip / show_history . JSON trip history
    choose_vehicle / choose_units ... user prompts
    main ..................... program loop
"""

import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta

import requests

GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"
PROFILES = ["car", "bike", "foot"]          # vehicle profiles free on Graphhopper
HISTORY_FILE = "trip_history.json"
TIMEOUT = 15                                 # seconds before a request gives up
KM_PER_MILE = 1.609344
QUIT_WORDS = ("q", "quit")


# --------------------------------------------------------------------------- #
# Colour helpers
# --------------------------------------------------------------------------- #
def supports_color():
    """True when the terminal can show ANSI colours (and NO_COLOR is not set)."""
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


COLORS = {"red": "31", "green": "32", "yellow": "33", "blue": "34",
          "magenta": "35", "cyan": "36", "bold": "1"}


def paint(text, color):
    """Wrap text in an ANSI colour code, or return it unchanged if unsupported."""
    if supports_color() and color in COLORS:
        return "\033[{}m{}\033[0m".format(COLORS[color], text)
    return text


# --------------------------------------------------------------------------- #
# API access
# --------------------------------------------------------------------------- #
def get_api_key():
    """Return the API key from GRAPHHOPPER_API_KEY, or ask the user for it."""
    key = os.environ.get("GRAPHHOPPER_API_KEY", "").strip()
    while not key:
        key = input("Enter your Graphhopper API key: ").strip()
    return key


def geocoding(location, key):
    """
    Look up a place name with the Geocoding API.

    Returns a dict:
        ok       True if a location was found
        status   HTTP status code (0 if the request itself failed)
        lat, lng coordinates (None when not ok)
        name     readable name, e.g. "Baltimore, Maryland, United States"
        message  error text when not ok
    """
    while location.strip() == "":                       # empty input -> ask again
        location = input("Enter the location again: ")

    url = GEOCODE_URL + urllib.parse.urlencode({"q": location, "limit": "1", "key": key})
    result = {"ok": False, "status": 0, "lat": None, "lng": None,
              "name": location, "message": ""}
    try:
        reply = requests.get(url, timeout=TIMEOUT)
    except requests.exceptions.RequestException as err:
        result["message"] = "Network problem: {}".format(err.__class__.__name__)
        return result

    result["status"] = reply.status_code
    try:
        data = reply.json()
    except ValueError:
        result["message"] = "Server did not return JSON"
        return result

    if reply.status_code == 200 and len(data.get("hits", [])) != 0:
        hit = data["hits"][0]
        result["ok"] = True
        result["lat"] = hit["point"]["lat"]
        result["lng"] = hit["point"]["lng"]
        # state / country are missing for some places (e.g. Beijing has no state)
        parts = [hit.get("name", location), hit.get("state", ""), hit.get("country", "")]
        result["name"] = ", ".join(p for p in parts if p)
        print(paint("Found: {} (type: {})".format(result["name"], hit.get("osm_value", "?")), "green"))
    elif reply.status_code == 200:
        result["message"] = "No match found for '{}'".format(location)
    else:
        result["message"] = data.get("message", "Unknown error")
    return result


def get_route(orig, dest, vehicle, key):
    """Call the Routing API. Returns (status_code, json_dict); status 0 = network failure."""
    query = urllib.parse.urlencode({"key": key, "vehicle": vehicle})
    points = "&point={}%2C{}&point={}%2C{}".format(orig["lat"], orig["lng"], dest["lat"], dest["lng"])
    try:
        reply = requests.get(ROUTE_URL + query + points, timeout=TIMEOUT)
        return reply.status_code, reply.json()
    except (requests.exceptions.RequestException, ValueError) as err:
        return 0, {"message": "Network problem: {}".format(err.__class__.__name__)}


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def format_duration(milliseconds):
    """Convert milliseconds to 'hh:mm:ss'."""
    total = int(milliseconds // 1000)
    return "{:02d}:{:02d}:{:02d}".format(total // 3600, total // 60 % 60, total % 60)


def format_distance(meters, units):
    """Format metres as miles, km or both depending on units ('mi', 'km', 'both')."""
    km = meters / 1000
    miles = km / KM_PER_MILE
    if units == "mi":
        return "{:.1f} mi".format(miles)
    if units == "km":
        return "{:.1f} km".format(km)
    return "{:.1f} mi / {:.1f} km".format(miles, km)


def print_trip(orig, dest, vehicle, units, path):
    """Print the trip summary, ETA and the directions table for one route."""
    line = "=" * 70
    print(paint(line, "cyan"))
    print(paint("Directions from {} to {} by {}".format(orig["name"], dest["name"], vehicle), "bold"))
    print(paint(line, "cyan"))
    print("Distance Traveled : " + paint(format_distance(path["distance"], units), "yellow"))
    print("Trip Duration     : " + paint(format_duration(path["time"]), "yellow"))
    eta = datetime.now() + timedelta(milliseconds=path["time"])
    print("Estimated arrival : " + paint(eta.strftime("%a %d %b %Y, %I:%M %p"), "yellow"))
    print(paint(line, "cyan"))
    print(paint("{:>3}  {:<48} {}".format("#", "Instruction", "Distance"), "magenta"))
    print("-" * 70)
    for number, step in enumerate(path["instructions"], start=1):
        print("{:>3}  {:<48} {}".format(number, step["text"][:48], format_distance(step["distance"], units)))
    print(paint(line, "cyan"))


# --------------------------------------------------------------------------- #
# Trip history
# --------------------------------------------------------------------------- #
def save_trip(orig, dest, vehicle, path):
    """Append the trip to HISTORY_FILE (a JSON list). Failure to save is not fatal."""
    entry = {"when": datetime.now().isoformat(timespec="seconds"),
             "from": orig["name"], "to": dest["name"], "vehicle": vehicle,
             "distance_m": round(path["distance"]), "duration_ms": path["time"]}
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, encoding="utf-8") as handle:
                history = json.load(handle)
        history.append(entry)
        with open(HISTORY_FILE, "w", encoding="utf-8") as handle:
            json.dump(history, handle, indent=2, ensure_ascii=False)
    except (OSError, ValueError):
        print(paint("(Could not save trip history.)", "yellow"))


def show_history():
    """Print saved trips, newest last."""
    try:
        with open(HISTORY_FILE, encoding="utf-8") as handle:
            history = json.load(handle)
    except (OSError, ValueError):
        history = []
    if not history:
        print("No trips saved yet.")
        return
    for item in history:
        print("{}  {} -> {} by {}  {:.1f} km  {}".format(
            item["when"], item["from"], item["to"], item["vehicle"],
            item["distance_m"] / 1000, format_duration(item["duration_ms"])))


# --------------------------------------------------------------------------- #
# User prompts
# --------------------------------------------------------------------------- #
def choose_vehicle():
    """Ask for a vehicle profile. Returns profile, 'history', or None to quit."""
    print(paint("\n" + "+" * 45 + "\nVehicle profiles available on Graphhopper:\n" + "+" * 45, "blue"))
    print(", ".join(PROFILES))
    print(paint("+" * 45, "blue"))
    answer = input("Enter a vehicle profile (h = history, q = quit): ").strip().lower()
    if answer in QUIT_WORDS:
        return None
    if answer in ("h", "history"):
        return "history"
    if answer in PROFILES:
        return answer
    print("No valid vehicle profile was entered. Using the car profile.")
    return "car"


def choose_units():
    """Ask once for the distance unit. Returns 'mi', 'km' or 'both'."""
    answer = input("Distance units - (m)iles, (k)ilometres or (b)oth [b]: ").strip().lower()
    return {"m": "mi", "mi": "mi", "k": "km", "km": "km"}.get(answer, "both")


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #
def main():
    """Program loop: choose vehicle, geocode both places, route, display, repeat."""
    key = get_api_key()
    units = choose_units()
    while True:
        vehicle = choose_vehicle()
        if vehicle is None:
            break
        if vehicle == "history":
            show_history()
            continue

        loc1 = input("Starting Location: ")
        if loc1.strip().lower() in QUIT_WORDS:
            break
        orig = geocoding(loc1, key)

        loc2 = input("Destination: ")
        if loc2.strip().lower() in QUIT_WORDS:
            break
        dest = geocoding(loc2, key)

        for place in (orig, dest):                       # report geocoding failures
            if not place["ok"]:
                print(paint("Geocode error {}: {}".format(place["status"], place["message"]), "red"))
        if not (orig["ok"] and dest["ok"]):
            continue

        status, data = get_route(orig, dest, vehicle, key)
        if status == 200:
            print_trip(orig, dest, vehicle, units, data["paths"][0])
            save_trip(orig, dest, vehicle, data["paths"][0])
        else:
            print(paint("Routing error {}: {}".format(status, data.get("message", "Unknown")), "red"))
            print(paint("*" * 49, "red"))
    print("Goodbye!")


if __name__ == "__main__":
    main()
