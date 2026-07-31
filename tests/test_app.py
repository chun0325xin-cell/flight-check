import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as flightcheck


class FlightCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        flightcheck.app.config.update(
            TESTING=True,
            DATABASE=Path(self.temp_dir.name) / "test.db",
            SECRET_KEY="test",
        )
        with flightcheck.app.app_context():
            flightcheck.init_db()
        self.client = flightcheck.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def assessment_payload(self, **overrides):
        payload = {
            "flight_name": "Local pattern",
            "experience": "60",
            "sleep": "8",
            "stress": "low",
            "aircraft_status": "clear",
            "fuel_margin": "75",
            "weather": "stable",
            "visibility": "10",
            "wind": "8",
            "crosswind": "4",
            "night": "no",
            "pressure_level": "low",
        }
        payload.update(overrides)
        return payload

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data.count(b"pilotbrief-logo.png"), 2)
        self.assertIn(b"Plan with clarity", response.data)
        self.assertIn(b"by PilotBrief Lab", response.data)
        self.assertIn(b"A student-pilot preflight risk and planning workspace.", response.data)
        self.assertIn(b"/personal-minimums", response.data)
        self.assertIn(b"/training-aircraft", response.data)
        self.assertIn(b"/commercial-aircraft", response.data)
        self.assertNotIn(b"FLIGHTCHECK AVIATION NETWORK", response.data)
        self.assertIn(b'class="planner-cta"', response.data)
        self.assertIn(b"Route planner", response.data)
        self.assertIn(b"Start briefing", response.data)
        self.assertIn(
            b'class="button landing-primary" href="/ai-plan"', response.data
        )
        self.assertIn(b"images/pilotbrief-logo.png", response.data)
        self.assertIn(b'class="header-logo"', response.data)
        self.assertIn(b"favicon.ico", response.data)
        self.assertIn(b"apple-touch-icon.png", response.data)
        self.assertIn(
            b'class="button landing-secondary" href="/flight-tips"', response.data
        )

    def test_briefing_page_contains_assessment(self):
        response = self.client.get("/briefing")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Build your risk picture", response.data)
        self.assertIn(b'id="assessment-form"', response.data)

    def test_flight_tips_page_is_linked_and_loads(self):
        home = self.client.get("/")
        self.assertIn(b'href="/flight-tips"', home.data)
        response = self.client.get("/flight-tips")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Small habits", response.data)
        self.assertIn(b"IMSAFE", response.data)
        self.assertIn(b"Learning aid only", response.data)

    def test_pilot_program_directory_links_to_official_sources(self):
        home = self.client.get("/")
        self.assertIn(b'class="button landing-secondary landing-programs-button"', home.data)
        response = self.client.get("/programs")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cathay Pacific", response.data)
        self.assertIn(b"Singapore Airlines", response.data)
        self.assertIn(b"United Airlines", response.data)
        self.assertIn(b"British Airways", response.data)
        self.assertIn(b"Air France", response.data)
        self.assertIn(b"Emirates", response.data)
        self.assertIn(b"Qatar Airways", response.data)
        self.assertIn(b"Ryanair", response.data)
        self.assertIn(b"Wizz Air", response.data)
        self.assertIn(b"TUI Airways", response.data)
        self.assertIn(b"Independent directory", response.data)
        self.assertIn(b'id="program-region"', response.data)
        self.assertIn(b'id="program-funding"', response.data)

    def test_aircraft_library_has_filters_and_profiles(self):
        response = self.client.get("/aircraft")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="filter-manufacturer"', response.data)
        self.assertIn(b"A350-900", response.data)
        self.assertIn(b"A318-100", response.data)
        self.assertIn(b"737 MAX 7", response.data)
        self.assertIn(b"Comac C919-100ER", response.data)
        self.assertIn(b"82</strong>", response.data)
        self.assertIn(b"Widebody", response.data)
        self.assertIn(b"Training / GA", response.data)
        for aircraft_name in (
            b"Cessna 152", b"Cessna 172 Skyhawk", b"Piper Warrior III",
            b"Piper Archer DX", b"Diamond DA20-C1", b"Diamond DA40 NG",
            b"Cirrus SR20", b"Beechcraft Bonanza G36",
        ):
            self.assertIn(aircraft_name, response.data)
        self.assertIn(b"/aircraft/a359-a350-900", response.data)
        detail = self.client.get("/aircraft/a359-a350-900")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Maximum takeoff weight", detail.data)
        self.assertIn(b"Wingspan", detail.data)
        self.assertIn(b"First flight", detail.data)
        self.assertIn(b"FAA Aircraft Characteristics Database", detail.data)

        c919 = self.client.get("/aircraft/c919-comac-c919-100er")
        self.assertEqual(c919.status_code, 200)
        self.assertIn(b"May 5, 2017", c919.data)
        self.assertIn(b"173,944", c919.data)
        self.assertIn(b"117.5", c919.data)
        self.assertIn(b"Manufacturer planning data", c919.data)

        cessna = self.client.get("/aircraft/c172-cessna-172-skyhawk")
        self.assertEqual(cessna.status_code, 200)
        self.assertIn(b"June 12, 1955", cessna.data)
        self.assertIn(b"2,550", cessna.data)
        self.assertIn(b"Training / GA", cessna.data)

        training = self.client.get("/training-aircraft")
        self.assertEqual(training.status_code, 200)
        self.assertIn(b"Cessna 152", training.data)
        self.assertNotIn(b"A350-900", training.data)
        simulator = self.client.get("/commercial-aircraft")
        self.assertEqual(simulator.status_code, 200)
        self.assertIn(b"COMMERCIAL AIRCRAFT", simulator.data)
        self.assertIn(b"$110.6 million", simulator.data)
        self.assertNotIn(b"Cessna 152", simulator.data)

    def test_airbus_families_do_not_share_the_wrong_photo(self):
        aircraft = {item["name"]: item for item in flightcheck.load_aircraft_catalog()}
        self.assertEqual(aircraft["A320-200"]["selector_family"], "A320 series")
        self.assertEqual(aircraft["A320neo"]["selector_family"], "A320 series")
        self.assertEqual(aircraft["A330-300"]["selector_family"], "A330 series")
        self.assertEqual(aircraft["A330-900"]["selector_family"], "A330 series")
        compared = ["A220-100", "A220-300", "A320-200", "A320neo", "A330-200", "A340-300", "A350-900"]
        photos = [aircraft[name]["image"] for name in compared]
        self.assertEqual(len(photos), len(set(photos)))
        self.assertIn("A320neo", aircraft["A320neo"]["image"])
        self.assertNotIn("A321-253", aircraft["A320neo"]["image"])
        self.assertIn("A321", aircraft["A321-200"]["image"])
        self.assertNotIn("A320-214", aircraft["A321-200"]["image"])
        self.assertIn("A330-200", aircraft["A330-200"]["image"])

    def test_every_aircraft_uses_a_unique_photo(self):
        aircraft = flightcheck.load_aircraft_catalog()
        photos = [item["image"] for item in aircraft]
        self.assertEqual(
            len(photos),
            len(set(photos)),
            "Every aircraft profile must have its own photo URL.",
        )
        by_name = {item["name"]: item for item in aircraft}
        self.assertIn("A350-1000ULR-MSN707-Qantas", by_name["A350-1000ULR"]["image"])
        self.assertIn("National_Jet_Systems_Boeing_717-200", by_name["717-200"]["image"])
        side_view_files = {
            "A319-100": "EasyJet_Europe_Airbus_A319",
            "737 MAX 7": "N7208U_B737_MAX_7",
            "737 MAX 9": "Alaska_737_Max_9",
            "737 MAX 10": "737_MAX_10_Roll_Out",
            "747-400": "747-400_sideview",
            "747-400D": "747-400D",
            "747-8": "747-8_port_side",
            "777-200LR": "777-200LR",
            "777-9": "Boeing_777X_at_Dubai_Airshow",
            "E170": "E170_-_F-HBXC",
            "E195": "Embraer_E195LR",
        }
        for name, filename_marker in side_view_files.items():
            self.assertIn(filename_marker, by_name[name]["image"])

    def test_assessment_post_persists_result(self):
        response = self.client.post("/assess", data=self.assessment_payload())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Continue the briefing", response.data)
        history = self.client.get("/history")
        self.assertIn(b"Local pattern", history.data)

    def test_high_risk_inputs_explain_result(self):
        response = self.client.post(
            "/assess",
            data=self.assessment_payload(
                sleep="3",
                stress="high",
                aircraft_status="unresolved",
                weather="marginal",
                visibility="2",
                crosswind="18",
                pressure_level="high",
            ),
        )
        self.assertIn(b"Pause &amp; reassess", response.data)
        self.assertIn(b"Unresolved aircraft issue", response.data)

    def test_invalid_number_redirects_with_feedback(self):
        response = self.client.post(
            "/assess",
            data=self.assessment_payload(visibility="-1"),
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Visibility must be between", response.data)

    def test_wind_triangle_has_reasonable_no_wind_result(self):
        result = flightcheck.calculate_wind_plan(90, 110, 0, 0)
        self.assertEqual(result["heading"], 90)
        self.assertEqual(result["groundspeed"], 110)
        self.assertEqual(result["correction"], 0)

    def test_waypoint_parser_preserves_flight_order(self):
        identifiers = flightcheck.parse_waypoint_ids("KJFK", "GAYEL, IGN CAM", "KALB")
        self.assertEqual(identifiers, ["KJFK", "GAYEL", "IGN", "CAM", "KALB"])

    def test_route_plan_post_calculates_and_saves(self):
        response = self.client.post(
            "/plan",
            data={
                "departure": "KJFK",
                "destination": "KALB",
                "checkpoints": "GAYEL",
                "true_course": "010",
                "distance": "120",
                "true_airspeed": "105",
                "wind_direction": "300",
                "wind_speed": "18",
                "route_visibility": "10",
                "ceiling": "5000",
                "temperature": "15",
                "fuel_burn": "8.5",
                "reserve_minutes": "60",
                "weather_notes": "VFR planning exercise",
                "leg_waypoint": ["KJFK", "GAYEL", "KALB"],
                "leg_altitude": ["1500", "5500", "2500"],
                "leg_facility": ["Kennedy Ground", "New York Approach", "Albany Tower"],
                "leg_frequency": ["121.90", "118.40", "119.50"],
                "leg_notes": ["Departure", "Monitor and verify", "Arrival"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"KJFK", response.data)
        self.assertIn(b"Estimated groundspeed", response.data)
        self.assertIn(b"Route visualization", response.data)
        self.assertIn(b"Waypoint-by-waypoint checklist", response.data)
        self.assertIn(b"New York Approach", response.data)
        with flightcheck.app.app_context():
            count = flightcheck.get_db().execute("SELECT COUNT(*) FROM route_plans").fetchone()[0]
        self.assertEqual(count, 1)
        history = self.client.get("/history")
        self.assertIn(b"KJFK", history.data)
        self.assertIn(b"Saved route plans", history.data)
        self.assertIn(b"View plan", history.data)
        saved_plan = self.client.get("/plan/1")
        self.assertEqual(saved_plan.status_code, 200)
        self.assertIn(b"KJFK", saved_plan.data)
        self.assertIn(b"Saved planning brief", saved_plan.data)

    def test_old_route_page_opens_simplified_ai_planner(self):
        response = self.client.get("/plan", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Compare both", response.data)
        self.assertIn(b'value="lowest_fuel"', response.data)
        self.assertIn(b'value="fastest"', response.data)
        self.assertIn(b'value="both"', response.data)
        self.assertNotIn(b'name="checkpoints"', response.data)
        self.assertNotIn(b'name="payload_weight"', response.data)
        self.assertIn(b"Search 5,900+ airports worldwide", response.data)
        self.assertIn(b'class="airport-suggestions"', response.data)
        self.assertIn(b'name="departure"', response.data)
        self.assertIn(b'name="destination"', response.data)

    def test_global_airport_search(self):
        response = self.client.get("/api/airports?q=heathrow")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["airports"][0]["code"], "EGLL")
        self.assertEqual(payload["airports"][0]["iata"], "LHR")

    def test_global_airports_include_field_elevations(self):
        airports = flightcheck.global_airports_by_code()
        self.assertEqual(airports["KJFK"]["elevation_ft"], 13)
        self.assertEqual(airports["EGLL"]["elevation_ft"], 83)
        self.assertEqual(airports["KDEN"]["elevation_ft"], 5431)

    def test_fallback_routes_include_real_navaids_and_altitudes(self):
        routes = flightcheck.local_fallback_routes({
            "departure": "KJFK",
            "destination": "EGLL",
            "aircraft_type": "787-9 Dreamliner",
        })
        self.assertEqual([route["optimization"] for route in routes], ["lowest_fuel", "fastest"])
        for route in routes:
            self.assertGreaterEqual(len(route["waypoints"]), 5)
            self.assertTrue(any(point["altitude_ft"] for point in route["waypoints"][1:-1]))
            self.assertTrue(all(point.get("lat") is not None for point in route["_route_points"]))

    def test_wind_forecast_changes_route_time(self):
        points = [
            {"id": "A", "lat": 40.0, "lon": -75.0},
            {"id": "B", "lat": 40.0, "lon": -70.0},
        ]
        weather = {
            "available": True,
            "samples": [{"lat": 40.0, "lon": -72.5, "wind_speed_kt": 50, "wind_from_deg": 270}],
        }
        result = flightcheck.apply_forecast_winds(points, 400, weather)
        self.assertLess(result["ete_minutes"], result["still_air_minutes"])
        self.assertGreater(result["average_wind_component_kt"], 0)
        self.assertIn("270", points[0]["forecast_wind"])

    def test_route_map_uses_great_circle_segments(self):
        script = (flightcheck.BASE_DIR / "static" / "js" / "route-map.js").read_text(encoding="utf-8")
        self.assertIn("greatCircleLeg", script)
        self.assertIn("GEODESIC ROUTE", script)
        self.assertIn("flight-waypoint-label", script)

    def test_ai_route_designer_validates_calculates_and_saves(self):
        points = [
            {"id": "KJFK", "name": "John F Kennedy", "lat": 40.6413, "lon": -73.7781, "type": "Airport / station", "order": 1},
            {"id": "GAYEL", "name": "GAYEL", "lat": 41.1, "lon": -73.5, "type": "Fix", "order": 2},
            {"id": "KALB", "name": "Albany", "lat": 42.7483, "lon": -73.8017, "type": "Airport / station", "order": 3},
        ]
        candidate = {
            "summary": "Candidate optimized for a short educational comparison.",
            "waypoints": [
                {"id": "KJFK", "altitude_ft": None, "action": "Departure"},
                {"id": "GAYEL", "altitude_ft": 5500, "action": "Cruise target"},
                {"id": "KALB", "altitude_ft": None, "action": "Arrival"},
            ],
            "warnings": ["Verify all route information."],
        }
        comparison = [
            {**candidate, "optimization": "lowest_fuel", "rationale": "Lower fuel explanation."},
            {**candidate, "optimization": "fastest", "rationale": "Faster route explanation.",
             "waypoints": [
                 {"id": "KJFK", "altitude_ft": None, "action": "Departure"},
                 {"id": "CAM", "altitude_ft": 4500, "action": "Cruise target"},
                 {"id": "KALB", "altitude_ft": None, "action": "Arrival"},
             ]},
        ]
        with patch("app.generate_ai_route_comparison", return_value=(comparison, "Test AI")), patch(
            "app.resolve_route_points", return_value=(points, [])
        ):
            response = self.client.post(
                "/ai-plan",
                data={
                    "departure": "KJFK",
                    "destination": "KALB",
                    "aircraft_manufacturer": "Boeing",
                    "aircraft_family": "787 Dreamliner",
                    "aircraft_type": "787-9 Dreamliner",
                    "payload_weight": "18500",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Lowest fuel", response.data)
        self.assertIn(b"Fastest route", response.data)
        self.assertIn(b"WHY THIS ROUTE", response.data)
        self.assertIn(b"Lower fuel explanation.", response.data)
        self.assertIn(b"GAYEL", response.data)
        self.assertIn(b"5,500 ft MSL", response.data)
        self.assertIn(b"Field elevation 13 ft MSL", response.data)
        self.assertIn(b"Airport elevation source", response.data)
        history = self.client.get("/history")
        self.assertIn(b"Saved route candidates", history.data)
        self.assertIn(b"787-9 Dreamliner", history.data)
        saved = self.client.get("/ai-plan/1")
        self.assertEqual(saved.status_code, 200)
        self.assertIn(b"GAYEL", saved.data)

    def test_ai_route_designer_can_generate_fastest_only(self):
        fastest = {
            "optimization": "fastest",
            "summary": "Fastest candidate.",
            "rationale": "Shortest estimated airborne time.",
            "waypoints": [
                {"id": "KJFK", "altitude_ft": None, "action": "Departure"},
                {"id": "CAM", "altitude_ft": 25000, "action": "Cruise"},
                {"id": "KALB", "altitude_ft": None, "action": "Arrival"},
            ],
            "warnings": [],
        }
        lowest_fuel = {
            **fastest,
            "optimization": "lowest_fuel",
            "summary": "Fuel candidate.",
            "waypoints": [
                {"id": "KJFK", "altitude_ft": None, "action": "Departure"},
                {"id": "GAYEL", "altitude_ft": 23000, "action": "Cruise"},
                {"id": "KALB", "altitude_ft": None, "action": "Arrival"},
            ],
        }
        points = [
            {"id": "KJFK", "name": "John F Kennedy", "lat": 40.6413, "lon": -73.7781, "type": "Airport", "order": 1},
            {"id": "KALB", "name": "Albany", "lat": 42.7483, "lon": -73.8017, "type": "Airport", "order": 2},
        ]
        with patch(
            "app.generate_ai_route_comparison", return_value=([lowest_fuel, fastest], "Test AI")
        ), patch("app.resolve_route_points", return_value=(points, [])):
            response = self.client.post("/ai-plan", data={
                "departure": "KJFK",
                "destination": "KALB",
                "aircraft_manufacturer": "Boeing",
                "aircraft_family": "787 Dreamliner",
                "aircraft_type": "787-9 Dreamliner",
                "route_mode": "fastest",
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Fastest route", response.data)
        self.assertIn(b"Fastest candidate.", response.data)
        self.assertNotIn(b"Fuel candidate.", response.data)
        with flightcheck.app.app_context():
            saved = flightcheck.get_db().execute(
                "SELECT optimization FROM ai_route_plans"
            ).fetchall()
        self.assertEqual([row["optimization"] for row in saved], ["fastest"])

    def test_personal_minimums_persist_and_are_compared(self):
        response = self.client.post("/personal-minimums", data={
            "day_ceiling": "3000", "night_ceiling": "5000",
            "minimum_visibility": "7", "surface_wind": "15",
            "maximum_crosswind": "8", "gust_spread_limit": "6",
            "fuel_reserve": "60", "minimum_sleep": "7",
            "night_permitted": "no", "minimums_notes": "Instructor reviewed.",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Instructor reviewed.", response.data)
        payload = self.assessment_payload(
            ceiling="2000", visibility="5", wind="20", crosswind="10",
            fuel_margin="45", sleep="6", night="yes",
        )
        result = self.client.post("/assess", data=payload)
        self.assertIn(b"Saved-limit comparison", result.data)
        self.assertIn(b"Visibility is below your personal minimum", result.data)
        self.assertIn(b"do not permit night flight", result.data)
        with flightcheck.app.app_context():
            count = flightcheck.get_db().execute("SELECT COUNT(*) FROM personal_minimums").fetchone()[0]
        self.assertEqual(count, 1)

    def test_records_are_isolated_by_browser_session(self):
        self.client.post("/assess", data=self.assessment_payload(flight_name="Private owner record"))
        other_client = flightcheck.app.test_client()
        response = other_client.get("/history")
        self.assertNotIn(b"Private owner record", response.data)
        owner_history = self.client.get("/history")
        self.assertIn(b"Private owner record", owner_history.data)

    def test_assessments_can_be_renamed_viewed_and_compared(self):
        self.client.post("/assess", data=self.assessment_payload(flight_name="First"))
        self.client.post("/assess", data=self.assessment_payload(
            flight_name="Second", stress="high", weather="mixed"
        ))
        renamed = self.client.post(
            "/history/1/rename", data={"flight_name": "Renamed first"}, follow_redirects=True
        )
        self.assertIn(b"Renamed first", renamed.data)
        viewed = self.client.get("/history/1")
        self.assertEqual(viewed.status_code, 200)
        compared = self.client.get("/history/compare?assessment=1&assessment=2")
        self.assertEqual(compared.status_code, 200)
        self.assertIn(b"Two briefings, side by side", compared.data)
        self.assertIn(b"Renamed first", compared.data)

    def test_safe_migration_columns_exist(self):
        with flightcheck.app.app_context():
            flightcheck.init_db()
            assessment_columns = {
                row["name"] for row in flightcheck.get_db().execute(
                    "PRAGMA table_info(assessments)"
                ).fetchall()
            }
        self.assertTrue({"session_id", "details_json", "category_scores"} <= assessment_columns)


if __name__ == "__main__":
    unittest.main()
