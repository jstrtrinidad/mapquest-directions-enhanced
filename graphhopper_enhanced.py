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
    1. API key is read from the GRAPHHOPPER_API_KEY environment variable or a
       .env file (or asked at start-up) instead of being hard-coded.
    2. Unit choice: miles, kilometres, or both.
    3. Colour-coded output (ANSI colours; automatically off if unsupported).
    4. Directions printed as an aligned table with step numbers.
    5. Estimated arrival time based on the current local time.
    6. Trip history saved to trip_history.json and viewable with "h".
    7. Network errors/timeouts are caught, so the program no longer crashes.
    8. Code split into small, documented functions for easy hand-over.

    Sprint 2 improvements (from QA test cases TC1-TC4):
    9.  Location confirmation: the top matches are listed and the user picks one,
        with a warning when a match does not contain what was typed
        (fixes "xyzabc" -> Indonesia and "San Jose" -> California).
    10. API key is checked once at start-up; an invalid key is reported
        immediately and the user can enter another one.
    11. Stricter input: unknown vehicles/units are re-asked instead of silently
        replaced; full words like "kilometers" are accepted; q works at every
        prompt; h and u are commands, never searched as places.
    12. Ctrl+C (or closing input) exits cleanly with "Goodbye!" - no traceback.
    13. Readable output: long instructions wrap instead of being cut, short
        distances show in m/ft instead of "0.0 km", durations read like
        "4 days 5 hrs 18 mins", and long direction lists are shown 20 at a time.
    14. Luzon only: searches are biased to Luzon and any match outside mainland
        Luzon (Visayas, Mindanao, ferry islands, other countries) is rejected,
        because trips are made by car, bike or foot.

HOW TO RUN
    pip install -r requirements.txt
    Put GRAPHHOPPER_API_KEY=your_key in a .env file (never commit it), or
    $env:GRAPHHOPPER_API_KEY="your_key"   (Windows PowerShell)
    python graphhopper_enhanced.py        (terminal version)
    python web_app.py                     (browser version, see README.md)

HOW TO CONTINUE THE PROJECT
    Each feature lives in its own function (see the index below), so a new
    feature normally means one new function plus one call in run().
    The web version (web_app.py) imports these same functions, so a fix here
    fixes both versions.

FUNCTION INDEX
    supports_color / paint ...... colour helpers
    ask ......................... input() that understands q / quit everywhere
    api_get ..................... safe GET request -> (status, json)
    in_luzon .................... is a point inside the Luzon service area?
    find_locations .............. Geocoding API, returns Luzon matches only
    check_api_key ............... start-up key validation
    get_route ................... Routing API call, returns (status, json)
    format_duration ............. milliseconds -> "3 hrs 28 mins"
    format_distance ............. metres -> text in the chosen unit
    print_trip / print_directions summary + wrapped, paged directions table
    save_trip / show_history .... JSON trip history
    get_api_key / choose_units / choose_vehicle / choose_location ... prompts
    run / main .................. program loop and clean exit
"""

import json
import os
import sys
import textwrap
import urllib.parse
from datetime import datetime, timedelta

import requests

try:                                    # optional: read the key from a .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEOCODE_URL = "https://graphhopper.com/api/1/geocode?"
ROUTE_URL = "https://graphhopper.com/api/1/route?"
PROFILES = ["car", "bike", "foot"]          # vehicle profiles free on Graphhopper
HISTORY_FILE = "trip_history.json"
TIMEOUT = 15                                 # seconds before a request gives up
KM_PER_MILE = 1.609344
FEET_PER_METER = 3.28084
MATCH_LIMIT = 5                              # how many place matches to offer
FETCH_LIMIT = 10                             # matches requested before the Luzon filter
LUZON_CENTER = "15.5,121.0"                  # search bias so Luzon results come first

# Service area: mainland Luzon (NCR, CAR, Ilocos, Cagayan Valley, Central Luzon,
# Calabarzon, Bicol mainland) - places reachable by car, bike or foot.
# Islands that need a ferry (Mindoro, Marinduque, Masbate, Catanduanes, Polillo,
# Batanes...) and the Visayas, Mindanao and other countries are outside.
# Corner points (latitude, longitude) traced clockwise, slightly offshore.
LUZON_POLYGON = [
    (18.70, 120.45), (18.75, 121.00), (18.55, 121.70), (18.70, 122.35), (17.80, 122.60),
    (16.40, 122.35), (15.75, 121.75), (14.75, 121.75), (14.25, 122.30), (14.30, 123.05),
    (13.95, 123.98), (13.25, 124.00), (12.85, 124.20), (12.50, 124.15), (12.60, 123.80),
    (12.95, 123.55), (13.45, 122.95), (13.80, 122.75), (13.15, 122.55), (13.75, 122.05),
    (13.80, 121.60), (13.60, 121.45), (13.70, 121.05), (13.70, 120.85), (13.75, 120.55),
    (14.10, 120.55), (14.35, 120.40), (14.80, 120.15), (15.30, 119.85), (16.45, 119.75),
    (16.35, 120.25), (17.00, 120.35), (17.60, 120.30), (18.20, 120.45),
]
PAGE_SIZE = 20                               # directions shown per page
TEXT_WIDTH = 46                              # width of the instruction column

QUIT_WORDS = ("q", "quit", "exit")
HISTORY_WORDS = ("h", "history")
UNIT_WORDS = ("u", "units")

VEHICLE_ALIASES = {
    "car": "car", "c": "car", "drive": "car",
    "bike": "bike", "bicycle": "bike", "b": "bike",
    "foot": "foot", "walk": "foot", "walking": "foot", "f": "foot",
}
UNIT_ALIASES = {
    "m": "mi", "mi": "mi", "mile": "mi", "miles": "mi",
    "k": "km", "km": "km", "kilometer": "km", "kilometers": "km",
    "kilometre": "km", "kilometres": "km",
    "b": "both", "both": "both", "": "both",
}
UNIT_NAMES = {"mi": "miles", "km": "kilometres", "both": "miles and kilometres"}


class QuitApp(Exception):
    """Raised when the user types q / quit at any prompt."""


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


def ask(prompt):
    """input() that strips spaces and raises QuitApp when the user types q / quit."""
    answer = input(prompt).strip()
    if answer.lower() in QUIT_WORDS:
        raise QuitApp
    return answer


# --------------------------------------------------------------------------- #
# API access
# --------------------------------------------------------------------------- #
def api_get(url):
    """GET a Graphhopper URL. Returns (status_code, json_dict); status 0 = network failure."""
    try:
        reply = requests.get(url, timeout=TIMEOUT)
    except requests.exceptions.RequestException as err:
        return 0, {"message": "Network problem: {}".format(err.__class__.__name__)}
    try:
        return reply.status_code, reply.json()
    except ValueError:
        return reply.status_code, {"message": "Server did not return JSON"}


def describe_hit(hit, fallback):
    """Build 'Name, State, Country' from a geocoding hit, skipping blanks and repeats."""
    parts = []
    for part in (hit.get("name", fallback), hit.get("state", ""), hit.get("country", "")):
        if part and part not in parts:          # avoids "Hrvatska, Hrvatska"
            parts.append(part)
    return ", ".join(parts)


def in_luzon(lat, lng):
    """True when the point lies inside LUZON_POLYGON (ray-casting point-in-polygon test)."""
    inside = False
    count = len(LUZON_POLYGON)
    for i in range(count):
        lat1, lng1 = LUZON_POLYGON[i]
        lat2, lng2 = LUZON_POLYGON[(i + 1) % count]
        if (lng1 > lng) != (lng2 > lng):        # this edge crosses the point's longitude
            edge_lat = lat1 + (lng - lng1) * (lat2 - lat1) / (lng2 - lng1)
            if lat < edge_lat:
                inside = not inside
    return inside


def find_locations(location, key, limit=MATCH_LIMIT):
    """
    Look up a place name with the Geocoding API and keep only places in Luzon.
    If nothing in Luzon is found, it searches once more with ", Philippines" added.

    Returns (status, matches, message):
        status   HTTP status code (0 if the request itself failed)
        matches  list of dicts: name, lat, lng, type, exact (at most `limit`)
                 exact = True when the typed text appears in the match name
        message  error, "outside Luzon" or "not found" text when matches is empty
    """
    queries = [location]
    if "philippines" not in location.lower():
        queries.append(location + ", Philippines")

    outside = []                                # names found outside the service area
    for query in queries:
        url = GEOCODE_URL + urllib.parse.urlencode(
            {"q": query, "limit": str(FETCH_LIMIT), "point": LUZON_CENTER, "key": key})
        status, data = api_get(url)
        if status != 200:
            return status, [], data.get("message", "Unknown error")

        matches, seen = [], set()
        for hit in data.get("hits", []):
            name = describe_hit(hit, location)
            if name in seen:                    # same place listed twice
                continue
            seen.add(name)
            lat, lng = hit["point"]["lat"], hit["point"]["lng"]
            if not in_luzon(lat, lng):
                if name not in outside:
                    outside.append(name)
                continue
            matches.append({
                "name": name, "lat": lat, "lng": lng,
                "type": hit.get("osm_value", "?"),
                "exact": location.lower() in name.lower(),
            })
        if matches:
            return status, matches[:limit], ""

    if outside:
        return 200, [], "'{}' is outside Luzon (found: {}). Only places in Luzon can be used".format(
            location, outside[0])
    return 200, [], "No place found for '{}'".format(location)


def check_api_key(key):
    """
    Make one small test request to see whether the key works.
    Returns (ok, message): ok is True, False (key rejected) or None (could not check).
    """
    status, _, message = find_locations("Manila", key, limit=1)
    if status in (401, 403):
        return False, message
    if status == 0 or status >= 500:
        return None, message
    return True, ""


def get_route(orig, dest, vehicle, key, with_points=False):
    """
    Call the Routing API for two chosen locations (dicts with lat/lng).
    with_points=True also returns the route line as plain coordinates (used by the web map).
    Returns (status_code, json_dict); status 0 = network failure.
    """
    params = {"key": key, "vehicle": vehicle}
    if with_points:
        params["points_encoded"] = "false"
    points = "&point={}%2C{}&point={}%2C{}".format(orig["lat"], orig["lng"], dest["lat"], dest["lng"])
    return api_get(ROUTE_URL + urllib.parse.urlencode(params) + points)


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def plural(number, word):
    """plural(1, 'hr') -> '1 hr', plural(3, 'hr') -> '3 hrs'."""
    return "{} {}{}".format(number, word, "" if number == 1 else "s")


def format_duration(milliseconds):
    """Convert milliseconds to readable text, e.g. '3 hrs 28 mins' or '4 days 5 hrs 18 mins'."""
    total = int(round(milliseconds / 1000))
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    parts = []
    if days:
        parts.append(plural(days, "day"))
    if hours:
        parts.append(plural(hours, "hr"))
    if minutes:
        parts.append(plural(minutes, "min"))
    if not parts:                               # trips shorter than a minute
        parts.append(plural(seconds, "sec"))
    return " ".join(parts)


def metric_text(meters):
    """Under 1 km -> metres ('450 m'), otherwise kilometres ('12.3 km')."""
    if meters < 1000:
        return "{:.0f} m".format(meters)
    return "{:.1f} km".format(meters / 1000)


def imperial_text(meters):
    """Under 0.1 mile -> feet ('148 ft'), otherwise miles ('7.6 mi')."""
    miles = meters / 1000 / KM_PER_MILE
    if miles < 0.1:
        return "{:.0f} ft".format(meters * FEET_PER_METER)
    return "{:.1f} mi".format(miles)


def format_distance(meters, units):
    """Format metres as miles, km or both depending on units ('mi', 'km', 'both')."""
    if units == "mi":
        return imperial_text(meters)
    if units == "km":
        return metric_text(meters)
    return "{} / {}".format(imperial_text(meters), metric_text(meters))


def format_eta(milliseconds):
    """Arrival time if the trip starts now, e.g. 'Mon 26 Oct 2026, 12:13 AM'."""
    eta = datetime.now() + timedelta(milliseconds=milliseconds)
    return eta.strftime("%a %d %b %Y, %I:%M %p")


def print_directions(instructions, units):
    """Print the numbered directions table, wrapping long text and pausing every PAGE_SIZE steps."""
    total = len(instructions)
    print(paint("{:>3}  {:<{w}}  {}".format("#", "Instruction", "Distance", w=TEXT_WIDTH), "magenta"))
    print("-" * 72)
    for number, step in enumerate(instructions, start=1):
        lines = textwrap.wrap(step["text"], TEXT_WIDTH) or [""]
        print("{:>3}  {:<{w}}  {}".format(number, lines[0], format_distance(step["distance"], units),
                                          w=TEXT_WIDTH))
        for extra in lines[1:]:                 # continuation lines, no cut-off words
            print("     " + extra)
        if number % PAGE_SIZE == 0 and number < total:
            more = ask(paint("-- Showing {} of {} steps. Enter = next {}, s = skip to the end: ".format(
                number, total, min(PAGE_SIZE, total - number)), "blue")).lower()
            if more in ("s", "skip"):
                print("... {} more steps hidden.".format(total - number))
                break


def print_trip(orig, dest, vehicle, units, path):
    """Print the trip summary, ETA and the directions table for one route."""
    line = "=" * 72
    print(paint(line, "cyan"))
    print(paint("Directions from {} to {} by {}".format(orig["name"], dest["name"], vehicle), "bold"))
    print(paint(line, "cyan"))
    print("Distance Traveled : " + paint(format_distance(path["distance"], units), "yellow"))
    print("Trip Duration     : " + paint(format_duration(path["time"]), "yellow"))
    print("Estimated arrival : " + paint(format_eta(path["time"]), "yellow"))
    print("Number of steps   : " + str(len(path["instructions"])))
    print(paint(line, "cyan"))
    print_directions(path["instructions"], units)
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
# User prompts (all of them accept q / quit through ask())
# --------------------------------------------------------------------------- #
def get_api_key():
    """Load the key (env or .env), check it once, and re-ask until a working key is given."""
    key = os.environ.get("GRAPHHOPPER_API_KEY", "").strip()
    while True:
        while not key:
            key = ask("Enter your Graphhopper API key (q = quit): ")
        print("Checking API key...")
        ok, message = check_api_key(key)
        if ok:
            print(paint("API key OK.", "green"))
            return key
        if ok is None:
            print(paint("Could not reach Graphhopper ({}). Check your internet connection; "
                        "continuing anyway.".format(message), "yellow"))
            return key
        print(paint("Invalid API key: {}".format(message), "red"))
        key = ""                                # ask for a new one


def choose_units():
    """Ask for the distance unit until a valid answer is given. Returns 'mi', 'km' or 'both'."""
    while True:
        answer = ask("Distance units - (m)iles, (k)ilometres or (b)oth [b]: ").lower()
        if answer in UNIT_ALIASES:
            units = UNIT_ALIASES[answer]
            print("Showing distances in {}.".format(UNIT_NAMES[units]))
            return units
        print(paint("'{}' is not a unit. Type m, k or b (or miles / kilometers / both).".format(answer), "red"))


def choose_vehicle():
    """Ask for a vehicle profile. Returns a profile, 'history' or 'units'; re-asks on bad input."""
    print(paint("\n" + "+" * 45 + "\nVehicle profiles available on Graphhopper:\n" + "+" * 45, "blue"))
    print(", ".join(PROFILES))
    print(paint("+" * 45, "blue"))
    while True:
        answer = ask("Enter a vehicle profile [car] (h = history, u = units, q = quit): ").lower()
        if answer in HISTORY_WORDS:
            return "history"
        if answer in UNIT_WORDS:
            return "units"
        if answer == "":
            return "car"
        if answer in VEHICLE_ALIASES:
            return VEHICLE_ALIASES[answer]
        print(paint("'{}' is not a vehicle profile. Choose car, bike or foot.".format(answer), "red"))


def choose_location(label, key):
    """
    Ask for a place, list the matches and let the user pick one.
    Returns the chosen match dict. Typing r re-types the place; h shows history.
    """
    while True:
        text = ask("{} in Luzon (q = quit): ".format(label))
        if text == "":
            print(paint("Please type a place name.", "red"))
            continue
        if text.lower() in HISTORY_WORDS:
            show_history()
            continue

        status, matches, message = find_locations(text, key)
        if not matches:
            if status == 200:                   # not found, or outside Luzon
                print(paint(message + ". Try another place.", "red"))
            else:
                print(paint("Geocode error {}: {}".format(status, message), "red"))
            continue

        print("Matches for '{}':".format(text))
        for number, match in enumerate(matches, start=1):
            note = "" if match["exact"] else paint("  <- not an exact match", "yellow")
            print("  {}. {} ({}){}".format(number, match["name"], match["type"], note))
        if not any(match["exact"] for match in matches):
            print(paint("Warning: none of these contain '{}'. Check the spelling.".format(text), "yellow"))

        while True:
            pick = ask("Choose 1-{} (r = re-type the place): ".format(len(matches))).lower()
            if pick in ("r", "retype"):
                break
            if pick.isdigit() and 1 <= int(pick) <= len(matches):
                chosen = matches[int(pick) - 1]
                print(paint("Selected: " + chosen["name"], "green"))
                return chosen
            print(paint("Please type a number from 1 to {}, or r.".format(len(matches)), "red"))


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #
def run():
    """Program loop: choose vehicle, choose both places, route, display, repeat."""
    key = get_api_key()
    units = choose_units()
    while True:
        vehicle = choose_vehicle()
        if vehicle == "history":
            show_history()
            continue
        if vehicle == "units":
            units = choose_units()
            continue

        orig = choose_location("Starting Location", key)
        dest = choose_location("Destination", key)

        status, data = get_route(orig, dest, vehicle, key)
        if status == 200:
            print_trip(orig, dest, vehicle, units, data["paths"][0])
            save_trip(orig, dest, vehicle, data["paths"][0])
        else:
            print(paint("Routing error {}: {}".format(status, data.get("message", "Unknown")), "red"))
            print(paint("*" * 49, "red"))


def main():
    """Start the program and always exit cleanly (q, Ctrl+C or end of input)."""
    try:
        run()
    except (QuitApp, KeyboardInterrupt, EOFError):
        pass
    print("\nGoodbye!")


if __name__ == "__main__":
    main()
