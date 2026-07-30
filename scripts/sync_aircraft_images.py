"""Build a unique Wikimedia Commons image mapping for FlightCheck aircraft."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "aircraft-catalog.json"
OUTPUT_PATH = ROOT / "data" / "aircraft-images.json"
API = "https://commons.wikimedia.org/w/api.php"
SKIP_WORDS = {
    "logo", "seat", "cabin", "cockpit", "diagram", "drawing", "sketch",
    "map", "route", "engine", "winglet", "interior", "business class",
}
SEARCH_ALIASES = {
    "dh8a-de-haviland-canada-dash-8-q100": "Dash 8 Q100 aircraft",
    "dh8b-de-haviland-canada-dash-8-q200": "DHC-8-200 aircraft exterior",
    "dh8c-de-haviland-canada-dash-8-q300": "Dash 8 Q300 aircraft",
    "dh8d-de-haviland-canada-dash-8-q400": "Dash 8 Q400 aircraft",
    "aj27-comac-arj-21-700": "Comac ARJ21-700 aircraft",
}


def request_json(params: dict) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "FlightCheck-Student-Project/1.0"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise
            time.sleep(2 ** attempt)
    return {}


def candidates(maker: str, model: str, search_term: str | None = None) -> list[dict]:
    body = request_json({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrlimit": 20,
        "gsrsearch": f'"{search_term or model}" {maker} filetype:bitmap',
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 720,
    })
    pages = body.get("query", {}).get("pages", {})
    return sorted(pages.values(), key=lambda item: item.get("index", 999))


def candidate_matches_model(title: str, model: str) -> bool:
    compact_title = re.sub(r"[^a-z0-9]+", "", title.lower())
    compact_model = re.sub(r"[^a-z0-9]+", "", model.lower())
    for generic in ("dreamliner", "dehavilandcanadadash", "comac", "atr"):
        compact_model = compact_model.replace(generic, "")
    # ULR is a mission/configuration suffix, and Commons filenames often omit
    # it even when the pictured airframe is that underlying model.
    compact_model = compact_model.replace("ulr", "")
    alternatives = {compact_model}
    if compact_model.startswith("a"):
        alternatives.add(compact_model[1:])
    if compact_model.startswith("737max"):
        alternatives.add(compact_model.replace("737max", "737"))
    if compact_model.startswith("dash8"):
        alternatives.add(compact_model.replace("dash8q", "dhc8"))
        alternatives.add(compact_model.replace("dash8q", "dash8"))
    return any(pattern and pattern in compact_title for pattern in alternatives)


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    rebuild = "--rebuild" in sys.argv
    existing = {} if rebuild else (json.loads(OUTPUT_PATH.read_text(encoding="utf-8")) if OUTPUT_PATH.exists() else {})
    used = {item["url"] for item in existing.values() if item.get("url")}
    output = dict(existing)
    for index, aircraft in enumerate(catalog, start=1):
        slug = aircraft["slug"]
        if slug in output and output[slug].get("url"):
            continue
        selected = None
        for page in candidates(aircraft["maker"], aircraft["name"], SEARCH_ALIASES.get(slug)):
            title = page.get("title", "").lower()
            image = (page.get("imageinfo") or [{}])[0]
            url = image.get("thumburl") or image.get("url")
            if (
                not url
                or url in used
                or any(word in title for word in SKIP_WORDS)
                or not candidate_matches_model(title, aircraft["name"])
            ):
                continue
            selected = {"url": url, "source": image.get("descriptionurl"), "title": page.get("title")}
            break
        if selected:
            output[slug] = selected
            used.add(selected["url"])
            OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{index:02d}/{len(catalog)} {aircraft['name']}: {selected['title'] if selected else 'NO MATCH'}")
        # Wikimedia throttles bursty search traffic. A modest pause keeps this
        # reproducible sync respectful and allows all catalog models to finish.
        time.sleep(6.5)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(output)} unique mappings to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
