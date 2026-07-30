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
        self.assertIn(b"Plan with clarity", response.data)
        self.assertIn(b'class="planner-cta"', response.data)
        self.assertIn(b"Route planner", response.data)
        self.assertIn(b"Start briefing", response.data)

    def test_briefing_page_contains_assessment(self):
        response = self.client.get("/briefing")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Build your risk picture", response.data)
        self.assertIn(b'id="assessment-form"', response.data)

    def test_aircraft_library_has_filters_and_profiles(self):
        response = self.client.get("/aircraft")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="filter-manufacturer"', response.data)
        self.assertIn(b"A350-900", response.data)
        self.assertIn(b"A318-100", response.data)
        self.assertIn(b"737 MAX 7", response.data)
        self.assertIn(b"Comac C919-100ER", response.data)
        self.assertIn(b"74</strong>", response.data)
        self.assertIn(b"Widebody", response.data)
        self.assertIn(b"/aircraft/a359-a350-900", response.data)
        detail = self.client.get("/aircraft/a359-a350-900")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Maximum takeoff weight", detail.data)
        self.assertIn(b"Wingspan", detail.data)
        self.assertIn(b"FAA Aircraft Characteristics Database", detail.data)

    def test_airbus_families_do_not_share_the_wrong_photo(self):
        aircraft = {item["name"]: item for item in flightcheck.load_aircraft_catalog()}
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
        self.assertIn(b"Generate both routes", response.data)
        self.assertNotIn(b'name="checkpoints"', response.data)
        self.assertNotIn(b'name="payload_weight"', response.data)

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
            {**candidate, "optimization": "lowest_fuel"},
            {**candidate, "optimization": "fastest"},
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
        self.assertIn(b"GAYEL", response.data)
        self.assertIn(b"5,500 ft MSL", response.data)
        history = self.client.get("/history")
        self.assertIn(b"Saved AI candidates", history.data)
        self.assertIn(b"787-9 Dreamliner", history.data)
        saved = self.client.get("/ai-plan/1")
        self.assertEqual(saved.status_code, 200)
        self.assertIn(b"GAYEL", saved.data)


if __name__ == "__main__":
    unittest.main()
