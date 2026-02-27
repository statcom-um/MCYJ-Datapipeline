#!/usr/bin/env python3
"""Step 1: Fetch agency data from the Michigan API and update facility_information.csv.

- Upserts rows by LicenseNumber from the API.
- Marks LicenseStatus='Unknown' for facilities in CSV but absent from the API.
- Never deletes rows.
"""

import argparse
import os
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion.scripts.pull_agency_info_api import get_all_agency_info

FACILITY_INFO_COLUMNS = [
    "LicenseNumber",
    "Address",
    "agencyId",
    "AgencyName",
    "AgencyType",
    "City",
    "County",
    "LicenseEffectiveDate",
    "LicenseeGroupOrganizationName",
    "LicenseExpirationDate",
    "LicenseStatus",
    "Phone",
    "ZipCode",
]

DEFAULT_FACILITY_INFO_CSV = "ingestion/data/facility_information.csv"


def run(facility_info_csv: str) -> None:
    # Load existing
    if os.path.exists(facility_info_csv):
        existing = pd.read_csv(facility_info_csv, dtype=str).fillna("")
    else:
        existing = pd.DataFrame(columns=FACILITY_INFO_COLUMNS)

    # Fetch from API
    all_agency_info = get_all_agency_info()
    if not all_agency_info:
        raise RuntimeError("Failed to fetch agency information from API")

    agency_list = (
        all_agency_info.get("returnValue", {})
        .get("objectData", {})
        .get("responseResult", [])
    )
    print(f"Fetched {len(agency_list)} agencies from API")

    # Build DataFrame from API data
    api_rows = []
    for agency in agency_list:
        if not isinstance(agency, dict):
            continue
        license_number = (agency.get("LicenseNumber") or "").strip()
        if not license_number:
            continue
        api_rows.append({col: agency.get(col, "") for col in FACILITY_INFO_COLUMNS})

    api_df = pd.DataFrame(api_rows, columns=FACILITY_INFO_COLUMNS).fillna("")
    api_license_numbers = set(api_df["LicenseNumber"].unique())

    # Merge: API rows overwrite existing rows by LicenseNumber
    existing_key = existing.set_index("LicenseNumber")
    api_key = api_df.set_index("LicenseNumber")

    # Update existing with API data, add new from API
    merged = api_key.combine_first(existing_key)
    # Overwrite columns for rows that appear in API (combine_first keeps existing if API is NaN)
    merged.update(api_key)

    merged = merged.reset_index()

    # Mark facilities not in API as Unknown
    unknown_mask = ~merged["LicenseNumber"].isin(api_license_numbers)
    unknown_count = unknown_mask.sum()
    merged.loc[unknown_mask, "LicenseStatus"] = "Unknown"

    # Sort and save
    merged = merged.sort_values("LicenseNumber").reset_index(drop=True)
    # Ensure column order
    merged = merged[[c for c in FACILITY_INFO_COLUMNS if c in merged.columns]]

    os.makedirs(os.path.dirname(facility_info_csv) or ".", exist_ok=True)
    merged.to_csv(facility_info_csv, index=False, quoting=1)  # QUOTE_ALL

    appended = len(api_license_numbers - set(existing["LicenseNumber"].unique())) if len(existing) > 0 else len(api_license_numbers)
    print(
        f"Facility information updated "
        f"(total={len(merged)}, appended={appended}, marked_unknown={unknown_count}): "
        f"{facility_info_csv}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 1: Fetch agency data and update facility_information.csv")
    parser.add_argument(
        "--facility-info-csv",
        default=DEFAULT_FACILITY_INFO_CSV,
        help=f"Path to facility_information.csv (default: {DEFAULT_FACILITY_INFO_CSV})",
    )
    args = parser.parse_args()
    run(args.facility_info_csv)


if __name__ == "__main__":
    main()
