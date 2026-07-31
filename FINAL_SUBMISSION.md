# FlightCheck Final Project Submission

## 1. Public GitHub repository

https://github.com/chun0325xin-cell/flight-check

## 2. Live application

https://www.pilotbrieflab.com

## 3. What does the application do?

FlightCheck is a student-pilot decision-support web application that combines a guided PAVE preflight risk assessment, personal minimums, saved planning history, aircraft references, and an educational route planner. It helps users recognize accumulating risk and compare route, weather, time, and fuel considerations while clearly reminding them to verify everything with official aviation sources and an instructor.

## 4. Meaningful POST endpoint

`POST /assess` validates the user's preflight briefing, applies the application's PAVE-based risk logic, generates factor-by-factor feedback, and saves the assessment to SQLite. The app also uses substantive POST workflows for route generation (`POST /ai-plan` and `POST /plan`), personal minimums, renaming records, and deleting saved records.

## 5. Persistent data storage

FlightCheck uses SQLite to save preflight assessments, route plans, AI-assisted route candidates, personal minimums, timestamps, and browser-session ownership identifiers. Database creation, migrations, inserts, updates, and queries are implemented in `app.py`; the local database is created automatically at `instance/flightcheck.db`.

## 6. How to run the application

Python 3 is required. From the repository folder, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows, activate the environment with `.venv\Scripts\activate`. Then open http://127.0.0.1:5000. The app works without an OpenAI key; setting `OPENAI_API_KEY` only enables optional AI-generated route candidates.

## 7. Known limitations

FlightCheck is an educational classroom project, not an approved flight-planning or weather-briefing system. Its risk weights and route estimates are not operationally validated, AI output may be incomplete, real airline purchase prices are often confidential, and all weather, NOTAMs, charts, aircraft performance, weight and balance, airspace, and ATC information must be independently verified. SQLite persists locally, but the Vercel serverless `/tmp` database is not permanent across deployments or instances.

## 8. Outside tools and sources

- Flask for the Python web server and routing
- SQLite for local persistent storage
- OpenAI Responses API for optional route-candidate generation
- AviationWeather.gov for METAR/TAF data and aviation identifier checks
- Open-Meteo for pressure-level wind forecasts
- OurAirports for global airport coordinates and elevations
- FAA Aircraft Characteristics Database for aircraft specifications
- Airbus published historical list-price data and The Airline Simulator Wiki list for aircraft catalog references
- Leaflet and OpenStreetMap for interactive maps
- Wikimedia Commons for aircraft photographs
- GitHub for source control and Vercel for public hosting

## Requirement checklist

- [x] Working Python/Flask web application
- [x] Runs locally after installing `requirements.txt`
- [x] Public GitHub repository
- [x] README with purpose and setup instructions
- [x] Public hosting
- [x] Persistent SQLite data storage for local use
- [x] Meaningful POST endpoints
- [x] Known limitations and outside-source citations
