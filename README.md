# FlightCheck

FlightCheck by PilotBrief Lab is a student-pilot preflight risk and planning workspace. It guides a user through the **PAVE** framework—Pilot, Aircraft, enVironment, and External pressures—then explains concerns, compares conditions with saved personal minimums, and stores the review privately for that browser session.

- **Live application:** [pilotbrieflab.com](https://www.pilotbrieflab.com)
- **Public source code:** [github.com/chun0325xin-cell/flight-check](https://github.com/chun0325xin-cell/flight-check)

> **Safety note:** FlightCheck is a classroom project, not an official flight-planning tool. It does not replace an instructor, a weather briefing, FAA regulations, aircraft documents, or pilot-in-command judgment.

## Features

- Guided four-step PAVE assessment
- Educational route planner with wind-correction, groundspeed, ETE, and fuel estimates
- Interactive route map with numbered airport, navaid, and fix markers
- Spherical great-circle corridor generation for polar and dateline-crossing routes
- Waypoint-by-waypoint navigation log for planned altitude, radio facility, frequency, and notes
- Weather-factor workspace with optional live METAR observations
- Built-in planning assistant with optional OpenAI Responses API enhancement
- Training Route Planner with searchable global airports and automatic lowest-fuel and fastest route comparison
- Server-side validation of AI-suggested waypoint identifiers before map display, with proposed altitude at each validated point
- Explainable risk indicator with factor-by-factor feedback
- Session-isolated SQLite storage for assessments, routes, and personal minimums
- View, rename, compare, trend, and delete controls for saved assessments
- Separate training-aircraft and commercial-aircraft reference sections
- Responsive, accessible interface for desktop and mobile
- Clear safety boundaries throughout the experience

## Run locally

1. Clone the repository and enter the project folder.
2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows, activate with `.venv\Scripts\activate`.

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start Flask (either command works):

   ```bash
   python app.py
   # or
   flask --app app run --debug
   ```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

The SQLite database is created automatically at `instance/flightcheck.db`.

## Course point requirements

FlightCheck completes all three optional point requirements:

1. **Public hosting:** The application is deployed at [pilotbrieflab.com](https://www.pilotbrieflab.com) through Vercel.
2. **Persistent data store:** SQLite stores assessments, route exercises, and personal minimums. Database setup and safe additive migrations are in `init_db()`.
3. **Meaningful POST usage:** `POST /assess` validates the submitted briefing, runs the PAVE-based evaluation logic, saves the result, and renders tailored feedback. `POST /history/<id>/delete` also changes persistent state.

`POST /plan` provides another substantive workflow: it validates a proposed route, solves an educational wind triangle, estimates time and fuel, retrieves recent METAR observations when available, generates a planning-assistant brief, and saves the route plan.

`POST /ai-plan` provides an AI-assisted workflow: it checks an approximate loaded weight, requests a candidate route, validates every returned waypoint against aviation data, estimates route distance/time/fuel, and saves the candidate in `ai_route_plans`. Saved candidates reopen at `/ai-plan/<id>`.

## Optional AI planning assistant

The app works without an API key and shows a clearly labeled direct-route fallback. To enable AI-generated intermediate waypoint and altitude candidates with the OpenAI Responses API, set an API key before starting Flask:

```bash
export OPENAI_API_KEY="your-key"
```

The app defaults to the current `gpt-5.6` alias. You may override it with `OPENAI_MODEL`. Never commit API keys to Git.

## Project structure

```text
app.py                 Flask routes, scoring logic, and SQLite access
templates/             Jinja page templates
static/css/style.css   Responsive visual design
static/js/app.js       Multi-step form behavior and interactions
requirements.txt       Python dependency list
tests/                 Automated Flask tests
```

## Known limitations

- Risk weights are educational design choices, not medically or operationally validated aviation standards.
- FlightCheck retrieves recent METAR/TAF information from AviationWeather.gov and samples Open-Meteo model winds along the route corridor, but it does not provide a complete or official weather briefing.
- Route calculations use user-entered true course and wind; they do not account for magnetic variation, climb/descent, changing winds, terrain, airspace, or aircraft-specific performance.
- “Lowest fuel” and “fastest” use aircraft-category estimates plus available forecast wind components; they are not guarantees of a globally optimal, legal, or safe route.
- AI waypoint and altitude suggestions can be wrong or incomplete. Identifiers are checked before mapping, but pilots must independently verify charts, terrain, airspace, weather, NOTAMs, performance, weight-and-balance/CG, fuel requirements, and ATC instructions.
- Records are associated with a signed private browser-session UUID rather than an account. Clearing session cookies breaks that association.
- SQLite is durable for local use. A serverless Vercel `/tmp` database is ephemeral; durable public multi-instance storage requires an external managed database.
- The app cannot determine whether a flight is legal or safe.

## Data sources and tools

- [OurAirports](https://ourairports.com/data/) public-domain global airport coordinates and field elevations
- [AviationWeather.gov](https://aviationweather.gov/data/api/) aviation weather and identifier validation
- [Open-Meteo](https://open-meteo.com/en/docs) global pressure-level wind forecasts
- [FAA Aircraft Characteristics Database](https://www.faa.gov/airports/engineering/aircraft_char_database) aircraft specifications
- [Airbus 2018 published list prices](https://www.airbus.com/sites/g/files/jlcbta136/files/2021-07/new-airbus-list-prices-2018.pdf) historical commercial-aircraft price references
- [The Airline Simulator Wiki aircraft list](https://the-airline-simulator.fandom.com/wiki/Category:Aircraft) initial commercial-aircraft model list supplied for the project
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses) optional route-candidate generation
- [Leaflet](https://leafletjs.com/) interactive route maps
- [Natural Earth](https://www.naturalearthdata.com/) public-domain country boundaries for the locally served vector basemap
- [Wikimedia Commons](https://commons.wikimedia.org/) aircraft photography
- [Flask](https://flask.palletsprojects.com/) Python web framework
- [Vercel](https://vercel.com/) public hosting

## Possible future improvements

- Optional authenticated accounts and encrypted cross-device synchronization
- Official aviation-data integrations with clear source attribution
- Accounts and private cloud synchronization
- CFI review of the educational scoring weights and mitigation prompts
