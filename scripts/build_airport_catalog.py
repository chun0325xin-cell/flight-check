"""Build a compact global airport search catalog from OurAirports CSV exports."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def main(airports_csv: str, countries_csv: str, output_json: str) -> None:
    with open(countries_csv, encoding="utf-8", newline="") as source:
        countries = {row["code"]: row["name"] for row in csv.DictReader(source)}

    airports = []
    with open(airports_csv, encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if row["type"] not in {"large_airport", "medium_airport", "small_airport"}:
                continue
            if row["scheduled_service"] != "yes" and row["type"] == "small_airport":
                continue
            code = (row["icao_code"] or row["gps_code"] or row["ident"]).upper()
            if not (3 <= len(code) <= 4 and code.isalnum()):
                continue
            airports.append({
                "code": code,
                "iata": row["iata_code"].upper(),
                "name": row["name"],
                "city": row["municipality"],
                "country": countries.get(row["iso_country"], row["iso_country"]),
                "lat": float(row["latitude_deg"]),
                "lon": float(row["longitude_deg"]),
                "type": row["type"].replace("_", " ").title(),
            })

    airports.sort(key=lambda item: (item["country"], item["city"], item["name"], item["code"]))
    Path(output_json).write_text(
        json.dumps(airports, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Wrote {len(airports):,} airports to {output_json}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
