from __future__ import annotations

import os
import json
import math
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("FLIGHTCHECK_DATABASE", BASE_DIR / "instance" / "flightcheck.db"))
AIRCRAFT_SOURCE = BASE_DIR / "data" / "aircraft-master.txt"
FAA_AIRCRAFT_SOURCE = BASE_DIR / "data" / "faa-aircraft.json"
GLOBAL_AIRPORTS_SOURCE = BASE_DIR / "data" / "global-airports.json"
GLOBAL_NAVAIDS_SOURCE = BASE_DIR / "data" / "global-navaids.json"
US_AIRPORTS = [
    ("KATL", "Hartsfield–Jackson Atlanta International Airport"),
    ("KAUS", "Austin–Bergstrom International Airport"),
    ("KBDL", "Bradley International Airport"),
    ("KBNA", "Nashville International Airport"),
    ("KBOS", "Boston Logan International Airport"),
    ("KBWI", "Baltimore/Washington International Thurgood Marshall Airport"),
    ("KCLE", "Cleveland Hopkins International Airport"),
    ("KCLT", "Charlotte Douglas International Airport"),
    ("KCVG", "Cincinnati/Northern Kentucky International Airport"),
    ("KDCA", "Ronald Reagan Washington National Airport"),
    ("KDEN", "Denver International Airport"),
    ("KDFW", "Dallas Fort Worth International Airport"),
    ("KDTW", "Detroit Metropolitan Wayne County Airport"),
    ("KEWR", "Newark Liberty International Airport"),
    ("KFLL", "Fort Lauderdale–Hollywood International Airport"),
    ("KHNL", "Daniel K. Inouye International Airport"),
    ("KIAD", "Washington Dulles International Airport"),
    ("KIAH", "George Bush Intercontinental Airport"),
    ("KIND", "Indianapolis International Airport"),
    ("KJFK", "John F. Kennedy International Airport"),
    ("KLAS", "Harry Reid International Airport"),
    ("KLAX", "Los Angeles International Airport"),
    ("KLGA", "LaGuardia Airport"),
    ("KMCI", "Kansas City International Airport"),
    ("KMCO", "Orlando International Airport"),
    ("KMDW", "Chicago Midway International Airport"),
    ("KMEM", "Memphis International Airport"),
    ("KMIA", "Miami International Airport"),
    ("KMKE", "Milwaukee Mitchell International Airport"),
    ("KMSP", "Minneapolis–Saint Paul International Airport"),
    ("KMSY", "Louis Armstrong New Orleans International Airport"),
    ("KOAK", "San Francisco Bay Oakland International Airport"),
    ("KORD", "Chicago O'Hare International Airport"),
    ("KPDX", "Portland International Airport"),
    ("KPHL", "Philadelphia International Airport"),
    ("KPHX", "Phoenix Sky Harbor International Airport"),
    ("KPIT", "Pittsburgh International Airport"),
    ("KRDU", "Raleigh–Durham International Airport"),
    ("KSAN", "San Diego International Airport"),
    ("KSAT", "San Antonio International Airport"),
    ("KSEA", "Seattle–Tacoma International Airport"),
    ("KSFO", "San Francisco International Airport"),
    ("KSJC", "Norman Y. Mineta San José International Airport"),
    ("KSLC", "Salt Lake City International Airport"),
    ("KSMF", "Sacramento International Airport"),
    ("KSNA", "John Wayne Airport"),
    ("KSTL", "St. Louis Lambert International Airport"),
    ("KTPA", "Tampa International Airport"),
    ("KALB", "Albany International Airport"),
    ("KHPN", "Westchester County Airport"),
    ("KISP", "Long Island MacArthur Airport"),
    ("KTEB", "Teterboro Airport"),
    ("KTTN", "Trenton–Mercer Airport"),
]

app = Flask(__name__)
app.config.update(
    DATABASE=DATABASE,
    SECRET_KEY=os.environ.get("SECRET_KEY", "flightcheck-local-development"),
    TEMPLATES_AUTO_RELOAD=True,
    SEND_FILE_MAX_AGE_DEFAULT=0,
)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        app.config["DATABASE"].parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            flight_name TEXT NOT NULL,
            experience INTEGER NOT NULL,
            sleep REAL NOT NULL,
            stress TEXT NOT NULL,
            aircraft_status TEXT NOT NULL,
            fuel_margin INTEGER NOT NULL,
            weather TEXT NOT NULL,
            visibility REAL NOT NULL,
            wind INTEGER NOT NULL,
            crosswind INTEGER NOT NULL,
            night INTEGER NOT NULL,
            pressure_level TEXT NOT NULL,
            score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            summary TEXT NOT NULL
        )
        """
    )
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS route_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            departure TEXT NOT NULL,
            destination TEXT NOT NULL,
            checkpoints TEXT NOT NULL,
            true_course REAL NOT NULL,
            distance REAL NOT NULL,
            true_airspeed REAL NOT NULL,
            wind_direction REAL NOT NULL,
            wind_speed REAL NOT NULL,
            visibility REAL NOT NULL,
            ceiling INTEGER NOT NULL,
            temperature REAL NOT NULL,
            weather_notes TEXT NOT NULL,
            heading REAL NOT NULL,
            groundspeed REAL NOT NULL,
            ete_minutes INTEGER NOT NULL,
            fuel_needed REAL NOT NULL,
            assistant_brief TEXT NOT NULL,
            navlog TEXT NOT NULL DEFAULT '[]',
            fuel_burn REAL NOT NULL DEFAULT 0,
            reserve_minutes INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS ai_route_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            departure TEXT NOT NULL,
            destination TEXT NOT NULL,
            aircraft_type TEXT NOT NULL,
            empty_weight REAL NOT NULL,
            payload_weight REAL NOT NULL,
            fuel_gallons REAL NOT NULL,
            max_gross_weight REAL NOT NULL,
            cruise_speed REAL NOT NULL,
            fuel_burn REAL NOT NULL,
            reserve_minutes INTEGER NOT NULL,
            optimization TEXT NOT NULL,
            loaded_weight REAL NOT NULL,
            distance REAL NOT NULL,
            ete_minutes INTEGER NOT NULL,
            estimated_fuel REAL NOT NULL,
            route_json TEXT NOT NULL,
            summary TEXT NOT NULL,
            warnings TEXT NOT NULL,
            agent_source TEXT NOT NULL
        )
        """
    )
    route_columns = {row["name"] for row in get_db().execute("PRAGMA table_info(route_plans)").fetchall()}
    route_migrations = {
        "navlog": "ALTER TABLE route_plans ADD COLUMN navlog TEXT NOT NULL DEFAULT '[]'",
        "fuel_burn": "ALTER TABLE route_plans ADD COLUMN fuel_burn REAL NOT NULL DEFAULT 0",
        "reserve_minutes": "ALTER TABLE route_plans ADD COLUMN reserve_minutes INTEGER NOT NULL DEFAULT 0",
    }
    for column, statement in route_migrations.items():
        if column not in route_columns:
            get_db().execute(statement)
    get_db().commit()


@app.cli.command("init-db")
def init_db_command() -> None:
    init_db()
    print("FlightCheck database initialized.")


def number(name: str, minimum: float, maximum: float, *, integer: bool = False) -> float | int:
    raw = request.form.get(name, "").strip()
    try:
        value = int(raw) if integer else float(raw)
    except ValueError as exc:
        raise ValueError(f"Enter a valid value for {name.replace('_', ' ')}.") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name.replace('_', ' ').title()} must be between {minimum:g} and {maximum:g}.")
    return value


def calculate_assessment(data: dict) -> dict:
    score = 0
    findings: list[dict[str, str | int]] = []

    def flag(category: str, title: str, detail: str, points: int) -> None:
        nonlocal score
        score += points
        findings.append({"category": category, "title": title, "detail": detail, "points": points})

    if data["experience"] < 25:
        flag("Pilot", "Limited recent experience", "Consider flying with an instructor or experienced pilot.", 18)
    elif data["experience"] < 75:
        flag("Pilot", "Building experience", "Use conservative personal minimums for today’s conditions.", 8)
    if data["sleep"] < 5:
        flag("Pilot", "Significant fatigue", "Fatigue can impair judgment and reaction time. Postponing is the safest option.", 25)
    elif data["sleep"] < 7:
        flag("Pilot", "Possible fatigue", "Reassess alertness honestly before continuing.", 12)
    if data["stress"] == "high":
        flag("Pilot", "High stress or distraction", "Resolve the distraction or choose another time to fly.", 18)
    elif data["stress"] == "moderate":
        flag("Pilot", "Moderate stress", "Slow down and use written checklists deliberately.", 7)

    if data["aircraft_status"] == "unresolved":
        flag("Aircraft", "Unresolved aircraft issue", "Do not fly until a qualified person resolves the discrepancy.", 35)
    elif data["aircraft_status"] == "monitor":
        flag("Aircraft", "Condition requires attention", "Review maintenance status and aircraft limitations before departure.", 15)
    if data["fuel_margin"] < 45:
        flag("Aircraft", "Narrow fuel margin", "Increase fuel margin and verify legal reserves for this flight.", 18)
    elif data["fuel_margin"] < 60:
        flag("Aircraft", "Conservative fuel check", "Confirm expected burn, reserves, and diversion fuel.", 7)

    if data["weather"] == "marginal":
        flag("Environment", "Marginal or changing weather", "Obtain an official briefing and prepare a clear diversion or no-go trigger.", 22)
    elif data["weather"] == "mixed":
        flag("Environment", "Mixed conditions", "Compare conditions with personal minimums and monitor trends.", 10)
    if data["visibility"] < 3:
        flag("Environment", "Very low visibility", "Conditions may be unsuitable or below legal VFR minimums. Verify regulations and briefing data.", 35)
    elif data["visibility"] < 6:
        flag("Environment", "Reduced visibility", "Use extra margin and verify ceiling, terrain, and route conditions.", 16)
    if data["crosswind"] > 12:
        flag("Environment", "Strong crosswind component", "Compare the component with aircraft limits and your demonstrated personal minimum.", 20)
    elif data["crosswind"] > 7:
        flag("Environment", "Moderate crosswind", "Review runway options and your crosswind proficiency.", 9)
    if data["wind"] > 25:
        flag("Environment", "Strong surface wind", "Expect turbulence and changing runway conditions; verify gusts.", 18)
    elif data["wind"] > 15:
        flag("Environment", "Elevated surface wind", "Check gust spread and airport/runway conditions.", 8)
    if data["night"]:
        flag("Environment", "Night operation", "Account for reduced visual cues, lighting, weather, and alternates.", 8)

    if data["pressure_level"] == "high":
        flag("External pressures", "Strong pressure to complete the flight", "Remove the deadline. Make delaying or canceling an easy, explicit option.", 20)
    elif data["pressure_level"] == "moderate":
        flag("External pressures", "Some schedule pressure", "Tell passengers the plan may change and set a firm no-go trigger.", 8)

    score = min(score, 100)
    if score >= 55:
        level, decision, summary = "High", "Pause & reassess", "Several factors combine to create a high-risk picture."
    elif score >= 25:
        level, decision, summary = "Elevated", "Mitigate before flight", "Important risks need a specific mitigation plan."
    else:
        level, decision, summary = "Lower", "Continue the briefing", "No major warning cluster was identified from these inputs."

    if not findings:
        findings.append({
            "category": "Briefing",
            "title": "No entered factor was flagged",
            "detail": "Continue with official weather, NOTAM, weight-and-balance, performance, and preflight checks.",
            "points": 0,
        })
    return {"score": score, "level": level, "decision": decision, "summary": summary, "findings": findings}


def calculate_wind_plan(course: float, tas: float, wind_from: float, wind_speed: float) -> dict:
    """Educational wind-triangle calculation; all directions are true."""
    angle = math.radians(wind_from - course)
    ratio = max(-1.0, min(1.0, (wind_speed / tas) * math.sin(angle)))
    correction = math.degrees(math.asin(ratio))
    heading = (course + correction) % 360
    groundspeed = tas * math.cos(math.radians(correction)) - wind_speed * math.cos(angle)
    return {
        "correction": round(correction, 1),
        "heading": round(heading, 1),
        "groundspeed": max(1, round(groundspeed, 1)),
    }


def fetch_metars(stations: list[str]) -> list[dict]:
    if app.config.get("TESTING"):
        return []
    ids = ",".join(station for station in stations if station)
    if not ids:
        return []
    query = urllib.parse.urlencode({"ids": ids, "format": "json"})
    request_data = urllib.request.Request(
        f"https://aviationweather.gov/api/data/metar?{query}",
        headers={"User-Agent": "FlightCheck-Student-Project/1.0"},
    )
    try:
        with urllib.request.urlopen(request_data, timeout=5) as response:
            return json.loads(response.read().decode("utf-8")) if response.status == 200 else []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []


def interpolate_corridor(first: dict, second: dict, count: int = 7) -> list[dict]:
    """Return evenly spaced points while taking the short path across the dateline."""
    lon_delta = second["lon"] - first["lon"]
    if lon_delta > 180:
        lon_delta -= 360
    elif lon_delta < -180:
        lon_delta += 360
    return [
        {
            "fraction": index / (count - 1),
            "lat": round(first["lat"] + (second["lat"] - first["lat"]) * index / (count - 1), 4),
            "lon": round(((first["lon"] + lon_delta * index / (count - 1) + 180) % 360) - 180, 4),
        }
        for index in range(count)
    ]


def fetch_route_winds(departure: str, destination: str, cruise_altitude: int) -> dict:
    """Fetch global forecast winds along the route corridor from Open-Meteo."""
    empty = {
        "available": False,
        "source": "Open-Meteo GFS",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "forecast_time": None,
        "pressure_level_hpa": None,
        "approx_altitude_ft": cruise_altitude,
        "samples": [],
    }
    if app.config.get("TESTING"):
        return empty
    airports = global_airports_by_code()
    if departure not in airports or destination not in airports:
        return empty
    pressure_level = min((200, 250, 300, 400, 500, 700, 850), key=lambda level: abs({
        200: 38600, 250: 34000, 300: 30000, 400: 23600, 500: 18200, 700: 9900, 850: 4800
    }[level] - cruise_altitude))
    corridor = interpolate_corridor(airports[departure], airports[destination])
    speed_field = f"wind_speed_{pressure_level}hPa"
    direction_field = f"wind_direction_{pressure_level}hPa"
    query = urllib.parse.urlencode({
        "latitude": ",".join(str(point["lat"]) for point in corridor),
        "longitude": ",".join(str(point["lon"]) for point in corridor),
        "hourly": f"{speed_field},{direction_field}",
        "forecast_days": 2,
        "wind_speed_unit": "kn",
        "timezone": "UTC",
    })
    request_data = urllib.request.Request(
        f"https://api.open-meteo.com/v1/forecast?{query}",
        headers={"User-Agent": "FlightCheck-Student-Project/1.0"},
    )
    try:
        with urllib.request.urlopen(request_data, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
        forecasts = body if isinstance(body, list) else [body]
        samples = []
        now = datetime.now(timezone.utc)
        forecast_time = None
        for point, forecast in zip(corridor, forecasts):
            hourly = forecast.get("hourly", {})
            times = hourly.get("time", [])
            speeds = hourly.get(speed_field, [])
            directions = hourly.get(direction_field, [])
            if not times or not speeds or not directions:
                continue
            parsed_times = [datetime.fromisoformat(value).replace(tzinfo=timezone.utc) for value in times]
            index = min(range(len(parsed_times)), key=lambda item: abs((parsed_times[item] - now).total_seconds()))
            if speeds[index] is None or directions[index] is None:
                continue
            forecast_time = times[index] + "Z"
            samples.append({
                **point,
                "wind_speed_kt": round(float(speeds[index]), 1),
                "wind_from_deg": round(float(directions[index])),
            })
        return {
            **empty,
            "available": bool(samples),
            "forecast_time": forecast_time,
            "pressure_level_hpa": pressure_level,
            "samples": samples,
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, TypeError, IndexError):
        return empty


def initial_bearing(first: dict, second: dict) -> float:
    lat1, lat2 = math.radians(first["lat"]), math.radians(second["lat"])
    dlon = math.radians(second["lon"] - first["lon"])
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def apply_forecast_winds(route_points: list[dict], cruise_speed: float, weather: dict) -> dict:
    """Estimate leg time using the nearest forecast sample; never substitutes for performance planning."""
    samples = weather.get("samples", []) if weather.get("available") else []
    total_minutes = 0.0
    still_air_minutes = 0.0
    components = []
    for first, second in zip(route_points, route_points[1:]):
        distance = haversine_nm(first, second)
        still_air_minutes += distance / cruise_speed * 60
        midpoint = {"lat": (first["lat"] + second["lat"]) / 2, "lon": (first["lon"] + second["lon"]) / 2}
        sample = min(samples, key=lambda item: haversine_nm(midpoint, item)) if samples else None
        if sample:
            calculation = calculate_wind_plan(
                initial_bearing(first, second), cruise_speed,
                sample["wind_from_deg"], sample["wind_speed_kt"],
            )
            groundspeed = calculation["groundspeed"]
            component = groundspeed - cruise_speed
            components.append(component)
            first["forecast_wind"] = (
                f"{sample['wind_from_deg']:03.0f}° at {sample['wind_speed_kt']:.0f} kt"
            )
        else:
            groundspeed = cruise_speed
        total_minutes += distance / max(groundspeed, 1) * 60
    return {
        "ete_minutes": math.ceil(total_minutes),
        "still_air_minutes": math.ceil(still_air_minutes),
        "average_wind_component_kt": round(sum(components) / len(components), 1) if components else None,
    }


def parse_waypoint_ids(departure: str, checkpoints: str, destination: str) -> list[str]:
    middle = [
        item.strip().upper()
        for item in checkpoints.replace("\n", ",").replace(" ", ",").split(",")
        if item.strip()
    ]
    return [departure, *middle, destination]


def parse_navlog(waypoint_ids: list[str]) -> list[dict]:
    submitted_ids = [value.strip().upper() for value in request.form.getlist("leg_waypoint")]
    altitudes = request.form.getlist("leg_altitude")
    facilities = request.form.getlist("leg_facility")
    frequencies = request.form.getlist("leg_frequency")
    notes = request.form.getlist("leg_notes")
    submitted: dict[str, dict] = {}
    for index, identifier in enumerate(submitted_ids):
        raw_altitude = altitudes[index].strip() if index < len(altitudes) else ""
        if raw_altitude:
            try:
                altitude = int(raw_altitude)
            except ValueError as exc:
                raise ValueError(f"Enter a valid planned altitude for {identifier}.") from exc
            if not 0 <= altitude <= 60000:
                raise ValueError(f"Planned altitude for {identifier} must be between 0 and 60,000 feet.")
        else:
            altitude = None
        frequency = frequencies[index].strip()[:12] if index < len(frequencies) else ""
        if frequency and not all(character.isdigit() or character == "." for character in frequency):
            raise ValueError(f"Enter a valid radio frequency for {identifier}.")
        submitted[identifier] = {
            "altitude": altitude,
            "facility": facilities[index].strip()[:80] if index < len(facilities) else "",
            "frequency": frequency,
            "notes": notes[index].strip()[:200] if index < len(notes) else "",
        }
    return [
        {"order": order, "waypoint": identifier, **submitted.get(identifier, {
            "altitude": None, "facility": "", "frequency": "", "notes": ""
        })}
        for order, identifier in enumerate(waypoint_ids, start=1)
    ]


def fetch_aviation_json(endpoint: str, identifiers: list[str]) -> list[dict]:
    if app.config.get("TESTING") or not identifiers:
        return []
    query = urllib.parse.urlencode({"ids": ",".join(identifiers), "format": "json"})
    request_data = urllib.request.Request(
        f"https://aviationweather.gov/api/data/{endpoint}?{query}",
        headers={"User-Agent": "FlightCheck-Student-Project/1.0"},
    )
    try:
        with urllib.request.urlopen(request_data, timeout=6) as response:
            if response.status != 200:
                return []
            body = json.loads(response.read().decode("utf-8"))
            return body if isinstance(body, list) else []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []


def resolve_route_points(identifiers: list[str]) -> tuple[list[dict], list[str]]:
    records: dict[str, dict] = {}
    for endpoint, point_type in (("stationinfo", "Airport / station"), ("navaid", "Navaid"), ("fix", "Fix")):
        for item in fetch_aviation_json(endpoint, identifiers):
            identifier = str(item.get("icaoId") or item.get("id") or "").upper()
            if identifier and item.get("lat") is not None and item.get("lon") is not None:
                records.setdefault(
                    identifier,
                    {
                        "id": identifier,
                        "name": item.get("site") or item.get("name") or identifier,
                        "lat": float(item["lat"]),
                        "lon": float(item["lon"]),
                        "type": point_type,
                    },
                )
    points: list[dict] = []
    unresolved: list[str] = []
    for order, identifier in enumerate(identifiers, start=1):
        item = records.get(identifier)
        if item:
            points.append({**item, "order": order})
        else:
            unresolved.append(identifier)
    return points, unresolved


def fallback_route_brief(plan: dict) -> str:
    concerns: list[str] = []
    if plan["visibility"] < 5:
        concerns.append("visibility is below a conservative five-mile planning margin")
    if plan["ceiling"] < 3000:
        concerns.append("the reported or forecast ceiling deserves additional VFR margin review")
    if plan["wind_speed"] >= 20:
        concerns.append("strong winds may increase turbulence and landing workload")
    if plan["groundspeed"] < plan["true_airspeed"] * 0.75:
        concerns.append("the headwind materially increases time and fuel exposure")
    if plan["temperature"] <= 2:
        concerns.append("the temperature warrants an icing-risk review wherever visible moisture may exist")
    if concerns:
        focus = "; ".join(concerns)
        return f"Planning focus: {focus}. Verify the complete route with an official briefing, aircraft performance data, NOTAMs, fuel reserves, alternates, and a CFI before flight."
    return (
        "The entered values do not show an obvious weather-margin warning, but that is not a go decision. "
        "Verify METARs, TAFs, NOTAMs, winds aloft, fuel reserves, alternates, terrain, airspace, and aircraft performance with official sources."
    )


def ai_route_brief(plan: dict, metars: list[dict]) -> tuple[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return fallback_route_brief(plan), "FlightCheck rules"
    system_text = (
        "You are an educational preflight planning coach for student pilots. Never make a go/no-go decision, "
        "call a route safe, or substitute for an official briefing or CFI. Identify missing information, explain "
        "wind/weather implications, and give a short verification checklist. Use only the supplied data."
    )
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-5.6"),
        "reasoning": {"effort": "low"},
        "input": [
            {"role": "developer", "content": system_text},
            {"role": "user", "content": json.dumps({"route_plan": plan, "metars": metars})},
        ],
    }
    api_request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(api_request, timeout=25) as response:
            body = json.loads(response.read().decode("utf-8"))
        text_parts = [
            part.get("text", "")
            for item in body.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        ]
        if any(text_parts):
            return "\n".join(text_parts).strip(), f"OpenAI {payload['model']}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        pass
    return fallback_route_brief(plan), "FlightCheck rules (AI unavailable)"


def response_output_text(body: dict) -> str:
    return "\n".join(
        part.get("text", "")
        for item in body.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ).strip()


@lru_cache(maxsize=1)
def load_global_airports() -> list[dict]:
    return json.loads(GLOBAL_AIRPORTS_SOURCE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def global_airport_codes() -> set[str]:
    return {airport["code"] for airport in load_global_airports()}


@lru_cache(maxsize=1)
def global_airports_by_code() -> dict[str, dict]:
    return {airport["code"]: airport for airport in load_global_airports()}


@lru_cache(maxsize=1)
def load_global_navaids() -> list[dict]:
    return json.loads(GLOBAL_NAVAIDS_SOURCE.read_text(encoding="utf-8"))


def local_fallback_routes(data: dict) -> list[dict]:
    departure = global_airports_by_code()[data["departure"]]
    destination = global_airports_by_code()[data["destination"]]
    aircraft_class = next(
        (item["class_group"] for item in load_aircraft_catalog() if item["name"] == data["aircraft_type"]),
        "narrowbody",
    )
    cruise_altitude = {"widebody": 37000, "narrowbody": 35000, "regional": 25000}[aircraft_class]

    def interpolated_point(fraction: float) -> dict:
        lon_delta = destination["lon"] - departure["lon"]
        if lon_delta > 180:
            lon_delta -= 360
        elif lon_delta < -180:
            lon_delta += 360
        lon = ((departure["lon"] + lon_delta * fraction + 180) % 360) - 180
        return {
            "lat": departure["lat"] + (destination["lat"] - departure["lat"]) * fraction,
            "lon": lon,
        }

    def altitude_for(fraction: float) -> tuple[int, str]:
        if fraction <= 0.22:
            return min(12000, cruise_altitude), "Climb segment — verify SID, terrain, restrictions, and clearance."
        if fraction >= 0.78:
            return min(12000, cruise_altitude), "Descent segment — verify STAR, crossing restrictions, and clearance."
        return cruise_altitude, "Cruise segment — verify airway, direction-of-flight altitude, and clearance."

    def build(optimization: str, fractions: tuple[float, ...]) -> dict:
        selected = []
        used = set()
        for fraction in fractions:
            target = interpolated_point(fraction)
            candidates = sorted(load_global_navaids(), key=lambda item: haversine_nm(target, item))
            navaid = next((item for item in candidates if item["id"] not in used), candidates[0])
            used.add(navaid["id"])
            altitude, action = altitude_for(fraction)
            selected.append({
                "id": navaid["id"], "altitude_ft": altitude, "action": action,
                "name": navaid["name"], "type": navaid["type"],
                "lat": navaid["lat"], "lon": navaid["lon"],
            })
        endpoint_points = [
            {
                "id": departure["code"], "altitude_ft": None,
                "elevation_ft": departure.get("elevation_ft"),
                "action": "Departure — verify field elevation, SID, runway, altimeter setting, and clearance.",
                "name": departure["name"], "type": "Airport",
                "lat": departure["lat"], "lon": departure["lon"],
            },
            {
                "id": destination["code"], "altitude_ft": None,
                "elevation_ft": destination.get("elevation_ft"),
                "action": "Arrival — verify field elevation, STAR, approach, runway, altimeter setting, and clearance.",
                "name": destination["name"], "type": "Airport",
                "lat": destination["lat"], "lon": destination["lon"],
            },
        ]
        points = [endpoint_points[0], *selected, endpoint_points[1]]
        return {
            "optimization": optimization,
            "summary": (
                "A structured educational fallback using nearby real-world navaids and a climb/cruise/descent "
                "profile. It does not establish an airway, procedure, clearance, or flyable route."
            ),
            "rationale": (
                "This fallback uses a different geometric navaid pattern and altitude profile for comparison. "
                + (
                    "Current Open-Meteo model winds were supplied to the later time-and-fuel estimate, but the "
                    "navaid sequence itself remains geometric and must not be treated as an operational route."
                    if data.get("route_winds_aloft", {}).get("available")
                    else "No route-wide forecast winds were available, so it does not claim a wind or fuel advantage."
                )
            ),
            "waypoints": points,
            "_route_points": points,
            "warnings": [
                "OpenAI route generation was unavailable; intermediate navaids were selected geometrically, not from current airways or ATC routing."
            ],
        }

    return [
        build("lowest_fuel", (0.22, 0.50, 0.78)),
        build("fastest", (0.16, 0.36, 0.64, 0.84)),
    ]


def generate_ai_route_candidate(data: dict) -> tuple[dict, str]:
    """Generate a candidate only; every returned identifier is validated before display."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "summary": (
                "OpenAI is not connected yet, so FlightCheck created a direct-route placeholder. "
                "Connect the API to generate intermediate waypoint candidates and altitude targets."
            ),
            "waypoints": [
                {"id": data["departure"], "altitude_ft": None, "action": "Departure altitude: verify airport elevation and clearance."},
                {"id": data["destination"], "altitude_ft": None, "action": "Arrival altitude: verify procedure, pattern, and clearance."},
            ],
            "warnings": ["AI route generation is offline; no intermediate waypoints or cruise altitude were invented."],
        }, "FlightCheck fallback — OpenAI not connected"

    prompt = (
        "Create one educational candidate route for a student pilot. Return JSON only with keys summary, "
        "waypoints, and warnings. waypoints must contain 2-8 objects with id, altitude_ft, and action. "
        "Use real airport, navaid, or fix identifiers appropriate to the countries crossed, starting at departure "
        "and ending at destination. "
        "Choose a simple candidate that matches the requested optimization: fastest means minimum practical "
        "distance; lowest_fuel means minimum estimated fuel using supplied cruise speed and fuel burn. "
        "Altitude values are planning targets in feet MSL, not clearances. Never invent radio frequencies, "
        "claim the route is safe/legal/optimal, or replace current charts, NOTAMs, weather, POH performance, "
        "weight and balance, ATC, or a CFI. The input may include automatically retrieved METAR and TAF "
        "records; use only those supplied records and clearly flag missing or stale weather. Flag missing "
        "performance/weather/airspace/terrain information."
    )
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-5.6"),
        "reasoning": {"effort": "low"},
        "input": [
            {"role": "developer", "content": prompt},
            {"role": "user", "content": json.dumps(data)},
        ],
    }
    api_request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(api_request, timeout=35) as response:
            text = response_output_text(json.loads(response.read().decode("utf-8")))
        candidate = json.loads(text)
        if isinstance(candidate, dict) and isinstance(candidate.get("waypoints"), list):
            return candidate, f"OpenAI {payload['model']}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError):
        pass
    fallback, _source = generate_ai_route_candidate_without_api(data)
    return fallback, "FlightCheck fallback — AI response unavailable"


def generate_ai_route_candidate_without_api(data: dict) -> tuple[dict, str]:
    return {
        "summary": "The AI response was unavailable, so FlightCheck retained only the endpoints for verification.",
        "waypoints": [
            {"id": data["departure"], "altitude_ft": None, "action": "Verify departure elevation and clearance."},
            {"id": data["destination"], "altitude_ft": None, "action": "Verify arrival procedure and clearance."},
        ],
        "warnings": ["No intermediate route or altitude was generated. Try again after checking the API connection."],
    }, "FlightCheck fallback"


def generate_ai_route_comparison(data: dict) -> tuple[list[dict], str]:
    """Generate both comparison routes in one API request to fit hosted request limits."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return local_fallback_routes(data), "FlightCheck navaid fallback — OpenAI not connected"

    prompt = (
        "Create two educational candidate routes for a student pilot in one response. Return JSON only with "
        "a routes array containing exactly two objects. Each object must have optimization, summary, rationale, "
        "waypoints, and warnings. One optimization must be lowest_fuel and the other fastest. The waypoint "
        "sequences must be different. Each waypoints array must "
        "contain 2-8 objects with id, altitude_ft, and action, begin at the supplied departure, and end at the "
        "supplied destination. Use real airport, navaid, or fix identifiers appropriate to the countries crossed. "
        "Make the routes meaningfully different. In rationale, explain why the lowest_fuel option may reduce "
        "fuel and why the fastest option may reduce time, discussing distance, waypoint count, altitude profile, "
        "and only the wind/weather evidence actually supplied. Use supplied METAR/TAF records only and flag "
        "missing, stale, or route-wide winds-aloft data. Never invent wind direction or claim a fuel benefit from "
        "wind without supporting data. Altitudes are planning targets, not clearances. Never invent radio frequencies or claim "
        "a route is safe, legal, cleared, or globally optimal. Require verification of charts, NOTAMs, weather, "
        "terrain, airspace, approved performance, loading, fuel, ATC instructions, and instructor review."
    )
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-5.6"),
        "reasoning": {"effort": "low"},
        "input": [
            {"role": "developer", "content": prompt},
            {"role": "user", "content": json.dumps(data)},
        ],
    }
    api_request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(api_request, timeout=25) as response:
            result = json.loads(response_output_text(json.loads(response.read().decode("utf-8"))))
        routes = result.get("routes", [])
        by_optimization = {
            item.get("optimization"): item
            for item in routes if isinstance(item, dict) and isinstance(item.get("waypoints"), list)
        }
        if {"lowest_fuel", "fastest"} <= by_optimization.keys():
            return [by_optimization["lowest_fuel"], by_optimization["fastest"]], f"OpenAI {payload['model']}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError):
        pass
    return local_fallback_routes(data), "FlightCheck navaid fallback — AI response unavailable"


def haversine_nm(first: dict, second: dict) -> float:
    lat1, lat2 = math.radians(first["lat"]), math.radians(second["lat"])
    dlat = lat2 - lat1
    dlon = math.radians(second["lon"] - first["lon"])
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3440.065 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def present_ai_route(row: sqlite3.Row | dict) -> dict:
    plan = dict(row)
    try:
        plan["route_points"] = json.loads(plan.pop("route_json"))
        plan["warnings"] = json.loads(plan["warnings"])
    except (json.JSONDecodeError, TypeError):
        plan["route_points"], plan["warnings"] = [], ["Saved route data could not be read."]
    plan["rationale"] = plan.get("rationale") or plan.get("summary", "")
    return plan


def load_aircraft_catalog() -> list[dict]:
    manufacturers = {"Airbus", "Boeing", "Bombardier", "Embraer", "ATR", "De Havilland Canada", "Comac"}
    photo_by_group = {
        "Airbus-wide": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/EGLF_-_Airbus_A350-941_-_F-WZNW.jpg/330px-EGLF_-_Airbus_A350-941_-_F-WZNW.jpg",
        "Airbus-other": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Airbus_A320-214%2C_Airbus_Industrie_JP7617615.jpg/330px-Airbus_A320-214%2C_Airbus_Industrie_JP7617615.jpg",
        "Boeing-wide": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Boeing_787_N1015B_ANA_Airlines_%2827611880663%29_%28cropped%29.jpg/330px-Boeing_787_N1015B_ANA_Airlines_%2827611880663%29_%28cropped%29.jpg",
        "Boeing-other": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/Alaska_737_Max_9.jpg/330px-Alaska_737_Max_9.jpg",
        "Bombardier": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/EC-JTU_%288544702097%29.jpg/330px-EC-JTU_%288544702097%29.jpg",
        "Embraer": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Wider%C3%B8e%2C_LN-WEA%2C_Embraer_E190-E2_%40_HEL.jpg/330px-Wider%C3%B8e%2C_LN-WEA%2C_Embraer_E190-E2_%40_HEL.jpg",
        "ATR": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/F-WWEZ_%28948%29_ATR.72-212A%28500%29_FlyFireFly_TLS_30AUG11_%286097869500%29_%28cropped%29.jpg/330px-F-WWEZ_%28948%29_ATR.72-212A%28500%29_FlyFireFly_TLS_30AUG11_%286097869500%29_%28cropped%29.jpg",
        "De Havilland Canada": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Hamburg_Airport_Wider%C3%B8e_Bombardier_DHC-8-402Q_LN-WDR_%28DSC08713%29.jpg/330px-Hamburg_Airport_Wider%C3%B8e_Bombardier_DHC-8-402Q_LN-WDR_%28DSC08713%29.jpg",
        "Comac": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/B-919A%40PEK_%2820221226151722%29.jpg/330px-B-919A%40PEK_%2820221226151722%29.jpg",
    }
    photo_by_family = {
        ("Airbus", "A220"): "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Airbus_A220-300.jpg/330px-Airbus_A220-300.jpg",
        ("Airbus", "A320"): "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Airbus_A320-214%2C_Airbus_Industrie_JP7617615.jpg/330px-Airbus_A320-214%2C_Airbus_Industrie_JP7617615.jpg",
        ("Airbus", "A320neo"): "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/IndiGo_Airbus_A320neo_F-WWDG_%28to_VT-ITI%29_%2828915135713%29.jpg/330px-IndiGo_Airbus_A320neo_F-WWDG_%28to_VT-ITI%29_%2828915135713%29.jpg",
        ("Airbus", "A330"): "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Delta_Air_Lines_Airbus_A330-300_N830NW_departing_Boston_July_2026_1.jpg/330px-Delta_Air_Lines_Airbus_A330-300_N830NW_departing_Boston_July_2026_1.jpg",
        ("Airbus", "A330neo"): "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Airbus_A330neo_F-WTTN_37.jpg/330px-Airbus_A330neo_F-WTTN_37.jpg",
        ("Airbus", "A340"): "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Frankfurt_Airport_Lufthansa_Airbus_A340-313_D-AIGY_%28DSC02566%29.jpg/330px-Frankfurt_Airport_Lufthansa_Airbus_A340-313_D-AIGY_%28DSC02566%29.jpg",
        ("Airbus", "A350"): "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/EGLF_-_Airbus_A350-941_-_F-WZNW.jpg/330px-EGLF_-_Airbus_A350-941_-_F-WZNW.jpg",
        ("Airbus", "A380"): "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/A6-EDY_A380_Emirates_31_jan_2013_jfk_%288442269364%29_%28cropped%29.jpg/330px-A6-EDY_A380_Emirates_31_jan_2013_jfk_%288442269364%29_%28cropped%29.jpg",
        ("Boeing", "717"): "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Delta_Air_Lines%2C_N991AT%2C_Boeing_717-23S_%2849593115578%29.jpg/330px-Delta_Air_Lines%2C_N991AT%2C_Boeing_717-23S_%2849593115578%29.jpg",
        ("Boeing", "737"): "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Classic_Colors_Southwest_Airlines_N648SW_Boeing_737-3H4_SJC.jpg/330px-Classic_Colors_Southwest_Airlines_N648SW_Boeing_737-3H4_SJC.jpg",
        ("Boeing", "737 MAX"): "https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/Alaska_737_Max_9.jpg/330px-Alaska_737_Max_9.jpg",
        ("Boeing", "747"): "https://upload.wikimedia.org/wikipedia/commons/thumb/4/48/Frankfurt_Airport_Lufthansa_Boeing_747-430_D-ABVY_%28DSC09727%29.jpg/330px-Frankfurt_Airport_Lufthansa_Boeing_747-430_D-ABVY_%28DSC09727%29.jpg",
        ("Boeing", "757"): "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Delta_757-200_N713TW_on_final_approach_to_Boston_Dec_2024_2.jpg/330px-Delta_757-200_N713TW_on_final_approach_to_Boston_Dec_2024_2.jpg",
    }
    image_mappings_path = BASE_DIR / "data" / "aircraft-images.json"
    image_mappings = json.loads(image_mappings_path.read_text(encoding="utf-8")) if image_mappings_path.exists() else {}
    faa_aliases = {"E140": "E135", "E175": "E75L"}
    supplemental_specs = {
        "b3xm-737-max-10": {
            "faa_model": "Boeing 737-10", "engine_type": "Jet", "engines": 2,
            "wingspan_ft": 117.8, "length_ft": 143.7, "height_ft": 40.3,
            "mtow_lb": 197900, "wake_category": "Medium",
            "spec_source": "https://www.boeing.com/commercial/737max",
        },
        "crjx-crj-1000": {
            "faa_model": "Bombardier CRJ1000", "engine_type": "Jet", "engines": 2,
            "wingspan_ft": 85.9, "length_ft": 128.4, "height_ft": 24.5,
            "mtow_lb": 91800, "landing_weight_lb": 81500, "wake_category": "Medium",
            "spec_source": "https://customer.aero.bombardier.com/webd/BAG/CustSite/BRAD/RACSDocument.nsf/51aae8b2b3bfdf6685256c300045ff31/ec63f8639ff3ab9d85257c1500635bd8/%24FILE/ATT82VLY.pdf/CRJ1000APMR8.pdf",
        },
        "aj27-comac-arj-21-700": {
            "faa_model": "COMAC ARJ21-700 / C909", "engine_type": "Jet", "engines": 2,
            "wingspan_ft": 89.5, "length_ft": 109.8, "height_ft": 27.5,
            "mtow_lb": 95901, "wake_category": "Medium",
            "spec_source": "https://www.comac.cc/fujian/c909acap_en.pdf",
        },
        "c919-comac-c919-100std": {
            "faa_model": "COMAC C919-100STD", "engine_type": "Jet", "engines": 2,
            "wingspan_ft": 117.5, "length_ft": 127.6, "height_ft": 39.2,
            "mtow_lb": 165567, "landing_weight_lb": 149474, "wake_category": "Medium",
            "spec_source": "https://www.comac.cc/fujian/c919acap_en.pdf",
        },
        "c919-comac-c919-100er": {
            "faa_model": "COMAC C919-100ER", "engine_type": "Jet", "engines": 2,
            "wingspan_ft": 117.5, "length_ft": 127.6, "height_ft": 39.2,
            "mtow_lb": 173944, "landing_weight_lb": 149474, "wake_category": "Medium",
            "spec_source": "https://www.comac.cc/fujian/c919acap_en.pdf",
        },
    }
    first_flight_by_family = {
        ("Airbus", "A220"): ("September 16, 2013", "A220 / CSeries program"),
        ("Airbus", "A320"): ("February 22, 1987", "A320 family program"),
        ("Airbus", "A320neo"): ("September 25, 2014", "A320neo family program"),
        ("Airbus", "A330"): ("November 2, 1992", "A330 family program"),
        ("Airbus", "A330neo"): ("October 19, 2017", "A330neo family program"),
        ("Airbus", "A340"): ("October 25, 1991", "A340 family program"),
        ("Airbus", "A350"): ("June 14, 2013", "A350 family program"),
        ("Airbus", "A380"): ("April 27, 2005", "A380 program"),
        ("Boeing", "717"): ("September 2, 1998", "717 program"),
        ("Boeing", "737"): ("February 9, 1997", "737 Next Generation program"),
        ("Boeing", "737 MAX"): ("January 29, 2016", "737 MAX family program"),
        ("Boeing", "747"): ("February 9, 1969", "747 family program"),
        ("Boeing", "757"): ("February 19, 1982", "757 program"),
        ("Boeing", "767"): ("September 26, 1981", "767 program"),
        ("Boeing", "777"): ("June 12, 1994", "777 family program"),
        ("Boeing", "777X"): ("January 25, 2020", "777X program"),
        ("Boeing", "787 Dreamliner"): ("December 15, 2009", "787 program"),
        ("Bombardier", "CRJ"): ("May 10, 1991", "CRJ family program"),
        ("Embraer", "ERJ"): ("August 11, 1995", "ERJ family program"),
        ("Embraer", "E-Jet"): ("February 19, 2002", "E-Jet family program"),
        ("Embraer", "E-Jet E2"): ("May 23, 2016", "E-Jet E2 family program"),
        ("ATR", "ATR 42/72"): ("August 16, 1984", "ATR family program"),
        ("De Havilland Canada", "Dash 8"): ("June 20, 1983", "Dash 8 family program"),
        ("Comac", "ARJ-21"): ("November 28, 2008", "ARJ21 program"),
        ("Comac", "C919"): ("May 5, 2017", "C919 program"),
    }
    first_flight_by_slug = {
        "b3xm-737-max-10": ("June 18, 2021", "737-10 model"),
        "crjx-crj-1000": ("September 3, 2008", "CRJ1000 model"),
        "e140-erj-140": ("June 27, 2000", "ERJ-140 model"),
        "e175-e175": ("June 14, 2003", "E175 model"),
        "e175-e175lr": ("June 14, 2003", "E175 model"),
        "aj27-comac-arj-21-700": ("November 28, 2008", "ARJ21 model"),
        "c919-comac-c919-100std": ("May 5, 2017", "C919 program"),
        "c919-comac-c919-100er": ("May 5, 2017", "C919 program"),
    }
    def commons_file(filename: str) -> dict:
        encoded = urllib.parse.quote(filename.replace(" ", "_"), safe="()_,-.")
        return {
            "url": f"https://commons.wikimedia.org/wiki/Special:Redirect/file/{encoded}?width=960",
            "source": f"https://commons.wikimedia.org/wiki/File:{encoded}",
        }

    model_photo_overrides = {
        "a319-a319-100": commons_file("EasyJet Europe Airbus A319 OE-LQQ Milan Malpensa 2024 (01).jpg"),
        "a321-a321-200": {
            "url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Nouvelair_A321_TS-IQB.jpg?width=960",
            "source": "https://commons.wikimedia.org/wiki/File:Nouvelair_A321_TS-IQB.jpg",
        },
        "a19n-a319neo": commons_file("Airbus A319-151N, Airbus Industrie JP9105933.jpg"),
        "a20n-a320neo": {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/IndiGo_Airbus_A320neo_F-WWDG_%28to_VT-ITI%29_%2828915135713%29.jpg/330px-IndiGo_Airbus_A320neo_F-WWDG_%28to_VT-ITI%29_%2828915135713%29.jpg",
            "source": "https://commons.wikimedia.org/wiki/File:IndiGo_Airbus_A320neo_F-WWDG_(to_VT-ITI)_(28915135713).jpg",
        },
        "a332-a330-200": {
            "url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Aeroflot_Airbus_A330-200_de-icing_Pereslavtsev.jpg?width=960",
            "source": "https://commons.wikimedia.org/wiki/File:Aeroflot_Airbus_A330-200_de-icing_Pereslavtsev.jpg",
        },
        "a333-a330-300": commons_file("Philippine Airlines Airbus A330-300 (RP-C8765) landing at Davao International Airport.jpg"),
        "a338-a330-800": commons_file("KUWAIT AIRWAYS AIRBUS A330-800 9K-APG (52891864111).jpg"),
        "a35k-a350-1000ulr": {
            "url": "https://aerospaceglobalnews.com/wp-content/uploads/2026/06/A350-1000ULR-MSN707-Qantas-First-flight-push-back-and-take-off_AI-PHO-0383-05-06-Large.jpeg",
            "source": "https://aerospaceglobalnews.com/news/airbus-a350-1000ulr-engineering-qantas-project-sunrise/",
        },
        "b712-717-200": {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/National_Jet_Systems_Boeing_717-200.jpg/1280px-National_Jet_Systems_Boeing_717-200.jpg",
            "source": "https://commons.wikimedia.org/wiki/File:National_Jet_Systems_Boeing_717-200.jpg",
        },
        "b37m-737-max-7": commons_file("N7208U B737 MAX 7, Southwest, Grant County 08-29-24 (55178942589).jpg"),
        "b39m-737-max-9": commons_file("Alaska 737 Max 9.jpg"),
        "b3xm-737-max-10": commons_file("737 MAX 10 Roll Out (Nov 2019) - 003.jpg"),
        "b744-747-400": commons_file("Air New Zealand 747-400 sideview.jpg"),
        "b744-747-400d": commons_file("JAL Japan Airlines Boeing 747-400D; JA8904, March 2004.jpg"),
        "b748-747-8": commons_file("Air China Boeing 747-8 port side smokey (33086724460).jpg"),
        "b77l-777-200lr": commons_file("Emirates Boeing 777-200LR A6-EWD IAD.jpg"),
        "b779-777-9": commons_file("Boeing 777X at Dubai Airshow 2021 2.jpg"),
        "e170-e170": commons_file("07-NOV-2022 - AF1439 HAJ-CDG (E170 - F-HBXC) (01).jpg"),
        "e195-e195": commons_file("I-ADJM AIRCRAFT Embraer E195LR 1B.jpg"),
        "dh8a-de-haviland-canada-dash-8-q100": commons_file("Jazz Air Dash 8 Q100 C-GTBP.jpg"),
        "dh8b-de-haviland-canada-dash-8-q200": commons_file("De Havilland Canada DHC-8-200 (UNI Air).jpg"),
        "dh8c-de-haviland-canada-dash-8-q300": commons_file("QantasLink Dash-8 Q300.jpg"),
        "aj27-comac-arj-21-700": commons_file("Comac ARJ21-700.jpg"),
    }
    # Commons search can occasionally return a nearby family member. Never show
    # those known mismatches as if they were the requested aircraft variant.
    rejected_synced_photos = {"a321-a321-200", "a20n-a320neo"}
    lines = AIRCRAFT_SOURCE.read_text(encoding="utf-8").splitlines()
    faa_data = json.loads(FAA_AIRCRAFT_SOURCE.read_text(encoding="utf-8"))
    start = next(index for index, line in enumerate(lines) if line.startswith("Manufacturer\t")) + 1
    current_maker = current_family = ""
    catalog: list[dict] = []
    for line in lines[start:]:
        if line == "How to Use This List":
            break
        if not line.strip():
            continue
        parts = line.split("\t")
        if parts[0] in manufacturers:
            current_maker, current_family, variant = parts[0], parts[1], parts[2]
            values = parts[3:]
        elif len(parts) >= 8:
            current_family, variant = parts[0], parts[1]
            values = parts[2:]
        else:
            variant = parts[0]
            values = parts[1:]
        if len(values) < 4:
            continue
        icao, range_text, seats, price = values[:4]
        try:
            range_km = int(range_text.replace(",", ""))
        except ValueError:
            continue
        wide = (current_maker == "Airbus" and current_family in {"A330", "A330neo", "A340", "A350", "A380"}) or (
            current_maker == "Boeing" and current_family in {"747", "767", "777", "777X", "787 Dreamliner"}
        )
        regional = current_maker in {"Bombardier", "Embraer", "ATR", "De Havilland Canada"} or (
            current_maker == "Comac" and current_family == "ARJ-21"
        )
        aircraft_class = "widebody" if wide else "regional" if regional else "narrowbody"
        range_group = "short" if range_km < 2778 else "medium" if range_km < 7408 else "long"
        photo_key = f"{current_maker}-{'wide' if wide else 'other'}" if current_maker in {"Airbus", "Boeing"} else current_maker
        faa = faa_data.get(faa_aliases.get(icao.upper(), icao.upper()), {})
        wingspan = faa.get("Wingspan_ft_with_winglets_sharklets") or faa.get("Wingspan_ft_without_winglets_sharklets")
        slug = re.sub(r"[^a-z0-9]+", "-", f"{icao}-{variant}".lower()).strip("-")
        override_photo = model_photo_overrides.get(slug)
        synced_photo = None if slug in rejected_synced_photos else image_mappings.get(slug)
        selected_image = (
            override_photo
            or synced_photo
            or {
                "url": photo_by_family.get((current_maker, current_family)) or photo_by_group[photo_key],
                "source": f"https://commons.wikimedia.org/wiki/Category:{current_maker.replace(' ', '_')}_{current_family.replace(' ', '_')}",
            }
        )
        supplemental = supplemental_specs.get(slug, {})
        first_flight, first_flight_scope = first_flight_by_slug.get(
            slug, first_flight_by_family.get((current_maker, current_family), ("Not verified", "program"))
        )
        catalog.append({
            "slug": slug,
            "name": variant,
            "maker": current_maker,
            "family": current_family,
            "selector_family": {
                ("Airbus", "A320"): "A320 series",
                ("Airbus", "A320neo"): "A320 series",
                ("Airbus", "A330"): "A330 series",
                ("Airbus", "A330neo"): "A330 series",
            }.get((current_maker, current_family), current_family),
            "icao": icao,
            "range_km": f"{range_km:,}",
            "range_nm": f"{round(range_km / 1.852):,}",
            "range_group": range_group,
            "seats": seats,
            "price": price,
            "class_group": aircraft_class,
            "class_name": {"widebody": "Widebody", "narrowbody": "Narrowbody", "regional": "Regional"}[aircraft_class],
            "image": selected_image["url"],
            "image_source": selected_image["source"],
            "faa_model": supplemental.get("faa_model") or faa.get("Model_FAA"),
            "engine_type": supplemental.get("engine_type") or faa.get("Physical_Class_Engine"),
            "engines": supplemental.get("engines") or faa.get("Num_Engines"),
            "wingspan_ft": supplemental.get("wingspan_ft") or wingspan,
            "length_ft": supplemental.get("length_ft") or faa.get("Length_ft"),
            "height_ft": supplemental.get("height_ft") or faa.get("Tail_Height_at_OEW_ft"),
            "mtow_lb": supplemental.get("mtow_lb") or faa.get("MTOW_lb"),
            "landing_weight_lb": supplemental.get("landing_weight_lb") or faa.get("MALW_lb"),
            "wake_category": supplemental.get("wake_category") or faa.get("ICAO_WTC"),
            "approach_speed_knot": supplemental.get("approach_speed_knot") or faa.get("Approach_Speed_knot"),
            "first_flight": first_flight,
            "first_flight_scope": first_flight_scope,
            "spec_source": supplemental.get("spec_source"),
        })
    return catalog


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/briefing")
def briefing():
    return render_template("briefing.html")


@app.get("/aircraft")
def aircraft():
    aircraft_catalog = load_aircraft_catalog()
    return render_template("aircraft.html", aircraft=aircraft_catalog)


@app.get("/api/airports")
def airport_search():
    query = request.args.get("q", "").strip().casefold()
    if not query:
        return {"airports": []}

    def score(airport: dict) -> tuple[int, str]:
        code = airport["code"].casefold()
        iata = airport["iata"].casefold()
        name = airport["name"].casefold()
        city = airport["city"].casefold()
        country = airport["country"].casefold()
        if query == code or query == iata:
            rank = 0
        elif code.startswith(query) or iata.startswith(query):
            rank = 1
        elif name.startswith(query) or city.startswith(query) or country.startswith(query):
            rank = 2
        else:
            rank = 3
        return rank, airport["name"]

    matches = [
        airport for airport in load_global_airports()
        if query in " ".join((
            airport["code"], airport["iata"], airport["name"],
            airport["city"], airport["country"],
        )).casefold()
    ]
    matches.sort(key=score)
    return {"airports": matches[:12]}


@app.get("/aircraft/<slug>")
def aircraft_detail(slug: str):
    item = next((entry for entry in load_aircraft_catalog() if entry["slug"] == slug), None)
    if item is None:
        abort(404)
    return render_template("aircraft_detail.html", aircraft=item)


@app.post("/assess")
def assess():
    try:
        flight_name = request.form.get("flight_name", "").strip()[:80] or "Untitled flight"
        data = {
            "experience": number("experience", 0, 5000, integer=True),
            "sleep": number("sleep", 0, 24),
            "stress": request.form.get("stress"),
            "aircraft_status": request.form.get("aircraft_status"),
            "fuel_margin": number("fuel_margin", 0, 600, integer=True),
            "weather": request.form.get("weather"),
            "visibility": number("visibility", 0, 100),
            "wind": number("wind", 0, 150, integer=True),
            "crosswind": number("crosswind", 0, 100, integer=True),
            "night": request.form.get("night") == "yes",
            "pressure_level": request.form.get("pressure_level"),
        }
        allowed = {
            "stress": {"low", "moderate", "high"},
            "aircraft_status": {"clear", "monitor", "unresolved"},
            "weather": {"stable", "mixed", "marginal"},
            "pressure_level": {"low", "moderate", "high"},
        }
        if any(data[key] not in values for key, values in allowed.items()):
            raise ValueError("Choose an option for every assessment field.")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("briefing") + "#assessment")

    result = calculate_assessment(data)
    summary = " ".join(f"{item['category']}: {item['title']}." for item in result["findings"])
    cursor = get_db().execute(
        """
        INSERT INTO assessments (
            created_at, flight_name, experience, sleep, stress, aircraft_status,
            fuel_margin, weather, visibility, wind, crosswind, night,
            pressure_level, score, risk_level, summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(), flight_name, data["experience"], data["sleep"],
            data["stress"], data["aircraft_status"], data["fuel_margin"], data["weather"],
            data["visibility"], data["wind"], data["crosswind"], int(data["night"]),
            data["pressure_level"], result["score"], result["level"], summary,
        ),
    )
    get_db().commit()
    return render_template("result.html", result=result, data=data, assessment_id=cursor.lastrowid, flight_name=flight_name)


@app.get("/history")
def history():
    init_db()
    assessments = get_db().execute("SELECT * FROM assessments ORDER BY id DESC LIMIT 50").fetchall()
    route_plans = get_db().execute("SELECT * FROM route_plans ORDER BY id DESC LIMIT 50").fetchall()
    ai_route_plans = get_db().execute("SELECT * FROM ai_route_plans ORDER BY id DESC LIMIT 50").fetchall()
    return render_template(
        "history.html", assessments=assessments, route_plans=route_plans, ai_route_plans=ai_route_plans
    )


@app.post("/history/<int:assessment_id>/delete")
def delete_assessment(assessment_id: int):
    cursor = get_db().execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))
    get_db().commit()
    if cursor.rowcount == 0:
        abort(404)
    flash("Assessment removed from history.", "success")
    return redirect(url_for("history"))


@app.post("/history/routes/<int:plan_id>/delete")
def delete_route_plan(plan_id: int):
    cursor = get_db().execute("DELETE FROM route_plans WHERE id = ?", (plan_id,))
    get_db().commit()
    if cursor.rowcount == 0:
        abort(404)
    flash("Route plan removed from history.", "success")
    return redirect(url_for("history"))


@app.post("/history/ai-routes/<int:plan_id>/delete")
def delete_ai_route_plan(plan_id: int):
    cursor = get_db().execute("DELETE FROM ai_route_plans WHERE id = ?", (plan_id,))
    get_db().commit()
    if cursor.rowcount == 0:
        abort(404)
    flash("AI route candidate removed from history.", "success")
    return redirect(url_for("history"))


@app.get("/about")
def about():
    return render_template("about.html")


@app.get("/flight-tips")
def flight_tips():
    return render_template("flight_tips.html")


@app.get("/programs")
def pilot_programs():
    return render_template("programs.html")


@app.route("/plan", methods=["GET", "POST"])
def route_planner():
    if request.method == "GET":
        return redirect(url_for("ai_route_planner"))
    try:
        departure = request.form.get("departure", "").strip().upper()[:4]
        destination = request.form.get("destination", "").strip().upper()[:4]
        if not (3 <= len(departure) <= 4 and departure.isalnum() and 3 <= len(destination) <= 4 and destination.isalnum()):
            raise ValueError("Enter valid three- or four-character airport identifiers.")
        plan = {
            "departure": departure,
            "destination": destination,
            "checkpoints": request.form.get("checkpoints", "").strip()[:300],
            "true_course": number("true_course", 0, 359),
            "distance": number("distance", 1, 3000),
            "true_airspeed": number("true_airspeed", 30, 500),
            "wind_direction": number("wind_direction", 0, 359),
            "wind_speed": number("wind_speed", 0, 200),
            "visibility": number("route_visibility", 0, 100),
            "ceiling": number("ceiling", 0, 60000, integer=True),
            "temperature": number("temperature", -80, 60),
            "fuel_burn": number("fuel_burn", 1, 100),
            "reserve_minutes": number("reserve_minutes", 0, 300, integer=True),
            "weather_notes": request.form.get("weather_notes", "").strip()[:1000],
        }
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("route_planner"))

    wind = calculate_wind_plan(
        plan["true_course"], plan["true_airspeed"], plan["wind_direction"], plan["wind_speed"]
    )
    plan.update(wind)
    plan["ete_minutes"] = math.ceil((plan["distance"] / plan["groundspeed"]) * 60)
    plan["fuel_needed"] = round(((plan["ete_minutes"] + plan["reserve_minutes"]) / 60) * plan["fuel_burn"], 1)
    waypoint_ids = parse_waypoint_ids(departure, plan["checkpoints"], destination)
    try:
        navlog = parse_navlog(waypoint_ids)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("route_planner"))
    plan["navlog"] = navlog
    route_points, unresolved_waypoints = resolve_route_points(waypoint_ids)
    navlog_by_id = {row["waypoint"]: row for row in navlog}
    route_points = [{**point, **navlog_by_id.get(point["id"], {})} for point in route_points]
    metars = fetch_metars([departure, destination])
    assistant_brief, assistant_source = ai_route_brief(plan, metars)
    cursor = get_db().execute(
        """
        INSERT INTO route_plans (
            created_at, departure, destination, checkpoints, true_course, distance,
            true_airspeed, wind_direction, wind_speed, visibility, ceiling, temperature,
            weather_notes, heading, groundspeed, ete_minutes, fuel_needed, assistant_brief,
            navlog, fuel_burn, reserve_minutes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(), departure, destination, plan["checkpoints"],
            plan["true_course"], plan["distance"], plan["true_airspeed"], plan["wind_direction"],
            plan["wind_speed"], plan["visibility"], plan["ceiling"], plan["temperature"],
            plan["weather_notes"], plan["heading"], plan["groundspeed"], plan["ete_minutes"],
            plan["fuel_needed"], assistant_brief, json.dumps(navlog), plan["fuel_burn"],
            plan["reserve_minutes"],
        ),
    )
    get_db().commit()
    return render_template(
        "plan_result.html",
        plan=plan,
        metars=metars,
        assistant_brief=assistant_brief,
        assistant_source=assistant_source,
        plan_id=cursor.lastrowid,
        route_points=route_points,
        unresolved_waypoints=unresolved_waypoints,
        navlog=navlog,
    )


@app.route("/ai-plan", methods=["GET", "POST"])
def ai_route_planner():
    if request.method == "GET":
        return render_template("ai_planner.html", aircraft=load_aircraft_catalog())
    try:
        departure = request.form.get("departure", "").strip().upper()[:4]
        destination = request.form.get("destination", "").strip().upper()[:4]
        if not (3 <= len(departure) <= 4 and departure.isalnum() and 3 <= len(destination) <= 4 and destination.isalnum()):
            raise ValueError("Enter valid three- or four-character airport identifiers.")
        if departure not in global_airport_codes() or destination not in global_airport_codes():
            raise ValueError("Choose both airports from the provided list.")
        if departure == destination:
            raise ValueError("Departure and arrival airports must be different.")
        route_mode = request.form.get("route_mode", "both").strip()
        if route_mode not in {"lowest_fuel", "fastest", "both"}:
            raise ValueError("Choose lowest fuel, fastest, or compare both.")
        selected_maker = request.form.get("aircraft_manufacturer", "").strip()
        selected_family = request.form.get("aircraft_family", "").strip()
        selected_type = request.form.get("aircraft_type", "").strip()
        selected_aircraft = next((item for item in load_aircraft_catalog() if
            (item["maker"], item["selector_family"], item["name"]) ==
            (selected_maker, selected_family, selected_type)), None)
        if selected_aircraft is None:
            raise ValueError("Choose a manufacturer, aircraft family, and specific model from the list.")
        payload_weight = 0.0
        cruise_speed, fuel_burn = {
            "widebody": (485, 1800), "narrowbody": (445, 750), "regional": (315, 300)
        }[selected_aircraft["class_group"]]
        max_gross_weight = float(selected_aircraft["mtow_lb"] or max(payload_weight * 2, 2500))
        if payload_weight > max_gross_weight:
            raise ValueError("The entered load is greater than this aircraft's published maximum takeoff weight.")
        data = {
            "departure": departure,
            "destination": destination,
            "aircraft_manufacturer": selected_maker,
            "aircraft_family": selected_family,
            "aircraft_type": selected_type,
            "route_mode": route_mode,
            "empty_weight": 0, "payload_weight": payload_weight, "fuel_gallons": 0,
            "max_gross_weight": max_gross_weight, "cruise_speed": cruise_speed,
            "fuel_burn": fuel_burn, "reserve_minutes": 45, "loaded_weight": payload_weight,
            "current_weather_observations": fetch_metars([departure, destination]),
            "current_terminal_forecasts": fetch_aviation_json("taf", [departure, destination]),
            "departure_airport": global_airports_by_code()[departure],
            "destination_airport": global_airports_by_code()[destination],
        }
        cruise_altitude = {"widebody": 35000, "narrowbody": 33000, "regional": 24000}[selected_aircraft["class_group"]]
        data["route_winds_aloft"] = fetch_route_winds(departure, destination, cruise_altitude)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("ai_route_planner"))

    candidates, agent_source = generate_ai_route_comparison(data)
    route_signatures = [
        tuple(str(point.get("id", "")).upper() for point in candidate.get("waypoints", []))
        for candidate in candidates
    ]
    if len(route_signatures) == 2 and route_signatures[0] == route_signatures[1]:
        candidates[1] = local_fallback_routes(data)[1]
        agent_source += " · alternate route differentiated locally"
    candidates_by_optimization = {
        candidate.get("optimization"): candidate for candidate in candidates
        if isinstance(candidate, dict)
    }
    selected_optimizations = (
        ("lowest_fuel", "fastest") if route_mode == "both" else (route_mode,)
    )
    plans = []
    for optimization in selected_optimizations:
        candidate = candidates_by_optimization.get(optimization)
        if candidate is None:
            candidate = next(
                route for route in local_fallback_routes(data)
                if route["optimization"] == optimization
            )
            agent_source += f" · {optimization} fallback"
        route_input = {**data, "optimization": optimization}
        submitted = candidate.get("waypoints", [])
        identifiers = [str(item.get("id", "")).strip().upper() for item in submitted
                       if isinstance(item, dict) and str(item.get("id", "")).strip()][:8]
        if not identifiers or identifiers[0] != departure:
            identifiers.insert(0, departure)
        if identifiers[-1] != destination:
            identifiers.append(destination)
        identifiers = list(dict.fromkeys(identifiers))
        if candidate.get("_route_points"):
            route_points = [
                {
                    "id": point["id"], "name": point["name"], "type": point["type"],
                    "lat": point["lat"], "lon": point["lon"], "order": order,
                }
                for order, point in enumerate(candidate["_route_points"], start=1)
            ]
            unresolved = []
        else:
            route_points, unresolved = resolve_route_points(identifiers)
            route_points = [dict(point) for point in route_points]
        submitted_by_id = {str(item.get("id", "")).upper(): item for item in submitted if isinstance(item, dict)}
        for point in route_points:
            suggestion = submitted_by_id.get(point["id"], {})
            try:
                altitude = int(suggestion.get("altitude_ft"))
            except (TypeError, ValueError):
                altitude = None
            point["altitude"] = altitude if altitude is not None and 0 <= altitude <= 60000 else None
            point["action"] = str(suggestion.get("action", "Research and verify this waypoint."))[:240]
            airport_record = global_airports_by_code().get(point["id"])
            point["elevation_ft"] = airport_record.get("elevation_ft") if airport_record else None
        if len(route_points) < 2:
            flash("The airport identifiers could not be verified. Check the codes and try again.", "error")
            return redirect(url_for("ai_route_planner"))
        distance = round(sum(haversine_nm(a, b) for a, b in zip(route_points, route_points[1:])), 1)
        wind_result = apply_forecast_winds(route_points, data["cruise_speed"], data["route_winds_aloft"])
        ete_minutes = wind_result["ete_minutes"]
        estimated_fuel = round(((ete_minutes + data["reserve_minutes"]) / 60) * data["fuel_burn"], 1)
        warnings = [str(item)[:300] for item in candidate.get("warnings", []) if str(item).strip()]
        if unresolved:
            warnings.append("Removed unverified AI waypoint identifiers: " + ", ".join(unresolved) + ".")
        warnings.append("Speed and fuel burn are aircraft-category comparison estimates; verify approved performance, winds, loading, reserves, weather, NOTAMs, terrain, airspace, and ATC routing.")
        if data["route_winds_aloft"]["available"]:
            wind_component = wind_result["average_wind_component_kt"]
            wind_word = "tailwind" if wind_component is not None and wind_component >= 0 else "headwind"
            warnings.append(
                f"Open-Meteo {data['route_winds_aloft']['pressure_level_hpa']} hPa forecast "
                f"({data['route_winds_aloft']['forecast_time']}) was sampled along the corridor; "
                f"estimated average {wind_word} component {abs(wind_component or 0):.1f} kt. "
                "Forecast winds are model guidance, not an official aviation briefing."
            )
        else:
            warnings.append("Route-wide forecast winds were unavailable, so time and fuel use still-air estimates.")
        summary = str(candidate.get("summary", "Candidate route generated for review."))[:1200]
        rationale = str(candidate.get(
            "rationale",
            "Compare distance, altitude profile, weather evidence, time, and estimated fuel before choosing."
        ))[:1200]
        cursor = get_db().execute(
            """INSERT INTO ai_route_plans (
                created_at, departure, destination, aircraft_type, empty_weight, payload_weight,
                fuel_gallons, max_gross_weight, cruise_speed, fuel_burn, reserve_minutes,
                optimization, loaded_weight, distance, ete_minutes, estimated_fuel,
                route_json, summary, warnings, agent_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now(timezone.utc).isoformat(), departure, destination, data["aircraft_type"],
             data["empty_weight"], data["payload_weight"], data["fuel_gallons"],
             data["max_gross_weight"], data["cruise_speed"], data["fuel_burn"],
             data["reserve_minutes"], optimization, data["loaded_weight"], distance,
             ete_minutes, estimated_fuel, json.dumps(route_points), summary,
             json.dumps(warnings), agent_source))
        plans.append({**route_input, "id": cursor.lastrowid, "distance": distance,
                      "ete_minutes": ete_minutes, "estimated_fuel": estimated_fuel,
                      "route_points": route_points, "summary": summary, "rationale": rationale,
                      "warnings": warnings, "agent_source": agent_source,
                      "wind_component": wind_result["average_wind_component_kt"],
                      "wind_forecast": data["route_winds_aloft"]})
    get_db().commit()
    return render_template("ai_plan_result.html", plans=plans, plan=plans[0])


@app.get("/ai-plan/<int:plan_id>")
def saved_ai_route_plan(plan_id: int):
    init_db()
    row = get_db().execute("SELECT * FROM ai_route_plans WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        abort(404)
    return render_template("ai_plan_result.html", plan=present_ai_route(row))


@app.get("/plan/<int:plan_id>")
def saved_route_plan(plan_id: int):
    init_db()
    row = get_db().execute("SELECT * FROM route_plans WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        abort(404)
    try:
        navlog = json.loads(row["navlog"] or "[]")
        if not isinstance(navlog, list):
            navlog = []
    except json.JSONDecodeError:
        navlog = []
    plan = dict(row)
    plan["navlog"] = navlog
    plan["fuel_burn"] = row["fuel_burn"] or 0
    plan["reserve_minutes"] = row["reserve_minutes"] or 0
    wind = calculate_wind_plan(
        plan["true_course"], plan["true_airspeed"], plan["wind_direction"], plan["wind_speed"]
    )
    plan["correction"] = wind["correction"]
    waypoint_ids = parse_waypoint_ids(plan["departure"], plan["checkpoints"], plan["destination"])
    route_points, unresolved_waypoints = resolve_route_points(waypoint_ids)
    navlog_by_id = {item.get("waypoint"): item for item in navlog if isinstance(item, dict)}
    route_points = [{**point, **navlog_by_id.get(point["id"], {})} for point in route_points]
    return render_template(
        "plan_result.html",
        plan=plan,
        metars=[],
        assistant_brief=row["assistant_brief"],
        assistant_source="Saved planning brief",
        plan_id=plan_id,
        route_points=route_points,
        unresolved_waypoints=unresolved_waypoints,
        navlog=navlog,
    )


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
