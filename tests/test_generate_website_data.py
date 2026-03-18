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

    def test_prefers_mixed_case(self):
        names = ["YOUTH GUIDANCE FOSTER CARE", "Youth Guidance Foster Care", "Youth Guidance Foster Care"]
        assert pick_best_name(names) == "Youth Guidance Foster Care"

    def test_majority_wins(self):
        names = ["Samaritas - Bay", "Samaritas - Bay", "Samaritas - Bay", "SAMARITAS - BAY", "Lutheran Social Services"]
        assert pick_best_name(names) == "Samaritas - Bay"

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
        assert result == "Wellspring Lutheran Services"

    def test_mixed_case_preferred_over_all_caps(self):
        names = ["ENNIS CENTER FOR CHILDREN - FLINT", "Ennis Center for Children - Flint"]
        result = pick_best_name(names)
        assert result == "Ennis Center for Children - Flint"


# ---------------------------------------------------------------------------
# resolve_agency_display_name
# ---------------------------------------------------------------------------

class TestResolveAgencyDisplayName:
    def test_neither_available(self):
        assert resolve_agency_display_name(None, None) == "Unknown Agency"

    def test_facility_only(self):
        assert resolve_agency_display_name("Grant Me Hope", None) == "Grant Me Hope"

    def test_document_only(self):
        assert resolve_agency_display_name(None, "Youth Guidance Foster Care") == "Youth Guidance Foster Care"

    def test_document_more_specific(self):
        """When doc name starts with facility name, prefer doc (more detail)."""
        result = resolve_agency_display_name("Eagle Village", "Eagle Village - Hainley House")
        assert result == "Eagle Village - Hainley House"

    def test_facility_contained_in_doc(self):
        """When facility name is fully contained in doc name, prefer doc."""
        result = resolve_agency_display_name("42nd Circuit Court", "42ND CIRCUIT COURT - FAMILY DIVISION")
        assert "FAMILY DIVISION" in result

    def test_completely_different_prefers_facility(self):
        """When names are unrelated, prefer facility (authoritative)."""
        result = resolve_agency_display_name("Berrien County Trial Court-Family Division", "Berrien County Probate Court")
        assert result == "Berrien County Trial Court-Family Division"

    def test_empty_string_treated_as_none(self):
        """Empty strings should be treated like None."""
        assert resolve_agency_display_name("", "Some Agency") == "Some Agency"
        assert resolve_agency_display_name("Some Facility", "") == "Some Facility"

    def test_same_name_prefers_mixed_case(self):
        """When names are identical (case-insensitive), prefer mixed-case."""
        result = resolve_agency_display_name("EAGLE VILLAGE ASHMUN-SHERK", "Eagle Village Ashmun-Sherk")
        assert result == "Eagle Village Ashmun-Sherk"

    def test_same_name_keeps_facility_if_already_mixed(self):
        """When both are mixed-case, prefer facility (authoritative)."""
        result = resolve_agency_display_name("Eagle Village - Hainley House", "Eagle Village - Hainley House")
        assert result == "Eagle Village - Hainley House"
