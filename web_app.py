"""
3Bytes - Graphhopper Directions, web version
============================================
A small Flask web server that puts a browser UI on top of the same functions
used by the terminal app (graphhopper_enhanced.py). Nothing about the API logic
is duplicated: geocoding, routing and formatting all come from that module.

HOW TO RUN
    pip install -r requirements.txt
    Set GRAPHHOPPER_API_KEY (in .env or the terminal), then:
    python web_app.py
    Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop.

HOW IT WORKS
    GET  /              -> the page (templates/index.html)
    GET  /api/geocode   -> ?q=Manila  returns the top matches so the user can confirm one
    POST /api/route     -> JSON {from, to, vehicle, units} returns summary, steps
                           and the route line for the map
    The API key stays on the server; the browser never sees it.
"""

import os
import sys

from flask import Flask, jsonify, render_template, request

import graphhopper_enhanced as gh       # also loads .env if python-dotenv is installed

app = Flask(__name__)
API_KEY = os.environ.get("GRAPHHOPPER_API_KEY", "").strip()


def error(message, status):
    """Return a JSON error. Status 0 (network failure) becomes 502 Bad Gateway."""
    return jsonify({"error": message}), (status if 400 <= status < 600 else 502)


@app.get("/")
def index():
    """Serve the single-page UI."""
    return render_template("index.html")


@app.get("/api/geocode")
def geocode():
    """Return up to 5 matches for a place name so the user can pick the right one."""
    query = request.args.get("q", "").strip()
    if not query:
        return error("Please type a place name.", 400)
    status, matches, message = gh.find_locations(query, API_KEY)
    if status != 200:
        return error("Geocoding failed: {}".format(message), status)
    return jsonify({"query": query, "matches": matches, "message": message})


@app.post("/api/route")
def route():
    """Get directions between two confirmed locations."""
    body = request.get_json(silent=True) or {}
    orig, dest = body.get("from"), body.get("to")
    vehicle = body.get("vehicle", "car")
    units = body.get("units", "both")

    if not (isinstance(orig, dict) and isinstance(dest, dict)):
        return error("Choose both a starting location and a destination.", 400)
    if vehicle not in gh.PROFILES:
        return error("Vehicle must be one of: " + ", ".join(gh.PROFILES), 400)
    if units not in ("mi", "km", "both"):
        return error("Units must be mi, km or both.", 400)

    status, data = gh.get_route(orig, dest, vehicle, API_KEY, with_points=True)
    if status != 200:
        return error("Routing failed: {}".format(data.get("message", "Unknown error")), status)

    path = data["paths"][0]
    gh.save_trip(orig, dest, vehicle, path)      # shared history with the terminal app
    return jsonify({
        "from": orig.get("name", ""),
        "to": dest.get("name", ""),
        "vehicle": vehicle,
        "distance": gh.format_distance(path["distance"], units),
        "duration": gh.format_duration(path["time"]),
        "eta": gh.format_eta(path["time"]),
        "steps": [{"text": step["text"], "distance": gh.format_distance(step["distance"], units)}
                  for step in path["instructions"]],
        # Graphhopper gives [lng, lat]; Leaflet wants [lat, lng]
        "line": [[lat, lng] for lng, lat, *_ in path.get("points", {}).get("coordinates", [])],
    })


def start():
    """Check the API key before starting the server, so a bad key is reported right away."""
    if not API_KEY:
        sys.exit("GRAPHHOPPER_API_KEY is not set. Add it to .env or set it in the terminal.")
    print("Checking API key...")
    ok, message = gh.check_api_key(API_KEY)
    if ok is False:
        sys.exit("Invalid API key: {}".format(message))
    if ok is None:
        print("Warning: could not reach Graphhopper ({}).".format(message))
    print("Open http://127.0.0.1:5000 in your browser (Ctrl+C to stop).")
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        print("\nGoodbye!")
