# 3Bytes – Enhanced Graphhopper Directions

DEVASC Project Activity 3, Option 1: feature enhancements of the Lab 4.9.2 application
("Integrate a REST API in a Python Application"). The lab now uses the **Graphhopper** API,
which replaced MapQuest, so the repository name still says "mapquest".

The app takes a starting location, a destination and a vehicle (car, bike, foot) and shows
the distance, duration, arrival time and turn-by-turn directions. Only places in
mainland Luzon can be used (see `LUZON_POLYGON` in `app/graphhopper_enhanced.py`). It runs in two ways:

| Version | File | How it looks |
|---|---|---|
| Terminal | `app/graphhopper_enhanced.py` | Coloured text in the VS Code / PowerShell terminal |
| Web | `app/web_app.py` + `app/templates/index.html` | Browser page with a map, served on your own computer |

Both versions use the same functions, so a fix in `app/graphhopper_enhanced.py` fixes both.

## Setup

1. Install Python 3.10 or newer.
2. Install the libraries:
   ```
   pip install -r requirements.txt
   ```
3. Get a free API key at https://www.graphhopper.com/ (Dashboard → API Keys).
4. Give the app your key, in **one** of these ways:
   - Create a file named `.env` (no `.example`) in the top project folder (next to `README.md`) containing
     `GRAPHHOPPER_API_KEY=your_key_here`
   - or, in PowerShell: `$env:GRAPHHOPPER_API_KEY="your_key_here"`

   **Never put your key in `.env.example` or in a `.py` file** – those are pushed to GitHub.
   `.env` is listed in `.gitignore`, so it stays on your computer.

## Run

Terminal version:
```
python app/graphhopper_enhanced.py
```
Commands that work at the prompts: `q` quit (any prompt), `h` trip history,
`u` change units (vehicle prompt), `r` re-type a place (match list), Ctrl+C exit.

Web version:
```
python app/web_app.py
```
Then open http://127.0.0.1:5000 in a browser. Press Ctrl+C in the terminal to stop the server.
The map needs an internet connection; the planner still works without it.

## Features

Enhancements over the lab code:
1. API key from `.env` / environment variable instead of hard-coded
2. Units: miles, kilometres or both
3. Colour-coded terminal output
4. Numbered, aligned directions table
5. Estimated arrival time
6. Trip history (`trip_history.json`, view with `h`)
7. Network errors and timeouts handled without crashing
8. Small documented functions for easy hand-over

Sprint 2 improvements (from QA test cases):
9. **Location confirmation** – top matches listed, user picks one; warning when a match does not contain what was typed
10. **API key checked at start-up** – a wrong key is reported immediately
11. **Stricter input** – invalid vehicles/units are re-asked; `kilometers`, `miles` etc. accepted; `q` works everywhere
12. **Clean exit on Ctrl+C** – no traceback
13. **Readable output** – wrapped instructions, m/ft for short distances, "4 days 5 hrs 18 mins" durations, directions shown 20 at a time
14. **Luzon only** – places outside mainland Luzon (Visayas, Mindanao, ferry islands, other countries) are rejected, since trips are by car, bike or foot
15. **Web UI** – browser version with a route map (Flask + Leaflet/OpenStreetMap)

## Project files

| File | Purpose |
|---|---|
| `app/graphhopper_enhanced.py` | Main app and all shared functions (see the function index in its docstring) |
| `app/web_app.py` | Flask server: `/` page, `/api/geocode`, `/api/route` |
| `app/templates/index.html` | Web page (HTML, CSS, JavaScript in one file) |
| `lab/graphhopper_parse-json_1.py` … `_7.py` | Original lab steps, kept for reference |
| `requirements.txt` | Python libraries to install |
| `.env.example` | Template showing the variable name – copy to `.env` |

## How to continue the project

- New terminal feature: add a function in `app/graphhopper_enhanced.py` and call it from `run()`.
- New web feature: add a route in `app/web_app.py` that reuses those functions, then update `app/templates/index.html`.
- Work on your own branch, open a pull request, and have a teammate review it before merging into `main`.

## Backlog (future enhancements)

- Warn before showing very long trips or routes that use ferries
- Plain-language routing errors (e.g. "No road route – the places may be separated by sea")
- Recover from a damaged `trip_history.json` instead of silently not saving
- Multi-stop trips (waypoints) and route options such as avoiding tolls
- Export directions to a file or share a link to the route
- Extend the service area (e.g. Mindoro or Visayas) with ferry-aware routing
