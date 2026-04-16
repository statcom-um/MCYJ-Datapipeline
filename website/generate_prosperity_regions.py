#!/usr/bin/env python3
"""
Generate prosperity_regions.geojson from Census Bureau county boundaries
and the michigan_prosperity_regions.csv mapping file.

Each output GeoJSON feature is a Michigan county polygon tagged with its
prosperity region number and name so that the website map overlay can
colour counties by region.
"""

import csv
import json
import os
import sys
from pathlib import Path

import requests

# Census Bureau TIGERweb REST API – county boundaries for Michigan (FIPS 26)
TIGERWEB_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/tigerWMS_Current/MapServer/82/query"
)
TIGERWEB_PARAMS = {
    "where": "STATE='26'",
    "outFields": "NAME,STATE,COUNTY",
    "f": "geojson",
    "outSR": "4326",
}

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR / "michigan_prosperity_regions.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "public" / "data"


def load_region_mapping(csv_path: str) -> dict:
    """Return {county_name_lower: (region_number, region_name)} from CSV."""
    mapping = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row["county"].strip()
            region_number = int(row["region_number"])
            region_name = row["region_name"].strip()
            mapping[county.lower()] = (region_number, region_name)
    return mapping


def simplify_coordinates(coords, precision=4):
    """Round coordinates to *precision* decimal places to shrink file size."""
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], precision), round(coords[1], precision)]
    return [simplify_coordinates(c, precision) for c in coords]


def fetch_county_geojson() -> dict:
    """Download Michigan county boundaries from the Census Bureau."""
    print("Downloading Michigan county boundaries from Census Bureau...")
    resp = requests.get(TIGERWEB_URL, params=TIGERWEB_PARAMS, timeout=60)
    resp.raise_for_status()
    geojson = resp.json()
    print(f"  Received {len(geojson.get('features', []))} county features")
    return geojson


def build_prosperity_geojson(county_geojson: dict, region_map: dict) -> dict:
    """Tag each county feature with prosperity region info and simplify."""
    features = []
    unmatched = []
    for feature in county_geojson.get("features", []):
        raw_name = (feature.get("properties") or {}).get("NAME", "")
        # Census returns "Eaton County"; CSV has just "Eaton"
        name = raw_name.strip()
        key = name.lower().removesuffix(" county")

        if key not in region_map:
            unmatched.append(name)
            continue

        region_number, region_name = region_map[key]
        # Simplify coordinates to reduce file size
        geometry = feature["geometry"].copy()
        geometry["coordinates"] = simplify_coordinates(geometry["coordinates"])

        features.append({
            "type": "Feature",
            "properties": {
                "county": name,
                "region_number": region_number,
                "region_name": region_name,
            },
            "geometry": geometry,
        })

    if unmatched:
        print(f"  Warning: {len(unmatched)} counties not matched to a region: {unmatched}")

    return {"type": "FeatureCollection", "features": features}


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
        help="Path to michigan_prosperity_regions.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write prosperity_regions.geojson",
    )
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"Error: CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    region_map = load_region_mapping(args.csv)
    print(f"Loaded {len(region_map)} county→region mappings")

    county_geojson = fetch_county_geojson()
    prosperity = build_prosperity_geojson(county_geojson, region_map)
    print(f"  Built {len(prosperity['features'])} region-tagged features")

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "prosperity_regions.geojson")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(prosperity, f)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"Wrote {out_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
