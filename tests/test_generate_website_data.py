"""Tests for agency name selection and reconciliation in website data generation."""

import sys
from pathlib import Path

import pytest

# Add website/ to path so the module can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "website"))

from generate_website_data import pick_best_name, resolve_agency_display_name


# ---------------------------------------------------------------------------
# pick_best_name
# ---------------------------------------------------------------------------

class TestPickBestName:
    def test_empty_list(self):
        assert pick_best_name([]) is None

    def test_single_name(self):
        assert pick_best_name(["Good Agency"]) == "Good Agency"

    def test_majority_wins(self):
        names = ["Samaritas - Bay", "Samaritas - Bay", "Samaritas - Bay", "SAMARITAS - BAY", "Lutheran Social Services"]
        result = pick_best_name(names)
        # Majority group is "samaritas - bay" (4 entries), longest is picked
        assert result.lower() == "samaritas - bay"

    def test_longest_in_group(self):
        names = [
            "Catholic Charities of Shiawassee and",
            "Catholic Charities of Shiawassee and G",
            "Catholic Charities of Shiawassee and Genesee Co",
            "CATHOLIC CHARITIES OF SHIAWASSEE",
        ]
        result = pick_best_name(names)
        assert result == "Catholic Charities of Shiawassee and Genesee Co"

    def test_strips_trailing_connectors(self):
        """Trailing connectors from old data should be cleaned before grouping."""
        names = ["CHARLEVOIX COUNTY PROBATE &", "CHARLEVOIX COUNTY PROBATE &"]
        result = pick_best_name(names)
        assert "&" not in result
        assert "CHARLEVOIX COUNTY PROBATE" in result

    def test_strips_trailing_dash(self):
        names = ["WELLSPRING LUTHERAN SERVICES -", "Wellspring Lutheran Services"]
        result = pick_best_name(names)
        assert result.lower() == "wellspring lutheran services"


# ---------------------------------------------------------------------------
# resolve_agency_display_name
# ---------------------------------------------------------------------------

class TestResolveAgencyDisplayName:
    def test_neither_available(self):
        assert resolve_agency_display_name(None, None) == "UNKNOWN AGENCY"

    def test_facility_only(self):
        assert resolve_agency_display_name("Grant Me Hope", None) == "GRANT ME HOPE"

    def test_document_only(self):
        assert resolve_agency_display_name(None, "Youth Guidance Foster Care") == "YOUTH GUIDANCE FOSTER CARE"

    def test_document_more_specific(self):
        """When doc name starts with facility name, prefer doc (more detail)."""
        result = resolve_agency_display_name("Eagle Village", "Eagle Village - Hainley House")
        assert result == "EAGLE VILLAGE - HAINLEY HOUSE"

    def test_facility_contained_in_doc(self):
        """When facility name is fully contained in doc name, prefer doc."""
        result = resolve_agency_display_name("42nd Circuit Court", "42ND CIRCUIT COURT - FAMILY DIVISION")
        assert result == "42ND CIRCUIT COURT - FAMILY DIVISION"

    def test_completely_different_prefers_facility(self):
        """When names are unrelated, prefer facility (authoritative)."""
        result = resolve_agency_display_name("Berrien County Trial Court-Family Division", "Berrien County Probate Court")
        assert result == "BERRIEN COUNTY TRIAL COURT - FAMILY DIVISION"

    def test_empty_string_treated_as_none(self):
        """Empty strings should be treated like None."""
        assert resolve_agency_display_name("", "Some Agency") == "SOME AGENCY"
        assert resolve_agency_display_name("Some Facility", "") == "SOME FACILITY"

    def test_same_name_different_case(self):
        """When names are identical (case-insensitive), result is ALL CAPS."""
        result = resolve_agency_display_name("EAGLE VILLAGE ASHMUN-SHERK", "Eagle Village Ashmun-Sherk")
        assert result == "EAGLE VILLAGE ASHMUN - SHERK"

    def test_all_results_are_uppercased(self):
        """All results from resolve_agency_display_name should be ALL CAPS."""
        assert resolve_agency_display_name("eagle village", None).isupper()
        assert resolve_agency_display_name(None, "eagle village").isupper()
        assert resolve_agency_display_name("eagle village", "eagle village").isupper()
        assert resolve_agency_display_name("eagle", "eagle village - house").isupper()
        assert resolve_agency_display_name("totally different", "some agency").isupper()
