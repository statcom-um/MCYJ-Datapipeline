"""Tests for agency name extraction from document text."""

import re
import sys
from pathlib import Path

import pytest

# Add ingestion/scripts to path so the module can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingestion" / "scripts"))

from extract_document_info import (
    _clean_agency_name,
    _extract_cover_letter_name,
    _join_continuation_line,
    extract_agency_name,
    extract_license_number,
)


# ---------------------------------------------------------------------------
# extract_license_number
# ---------------------------------------------------------------------------

class TestExtractLicenseNumber:
    def test_license_hash_colon(self):
        text = "RE: License #: CB250296641\nSome text"
        assert extract_license_number(text) == "CB250296641"

    def test_license_number_colon(self):
        text = "License Number: CA110200973\nMore text"
        assert extract_license_number(text) == "CA110200973"

    def test_re_license(self):
        text = "Re: License #: CB130201519\nDear person"
        assert extract_license_number(text) == "CB130201519"

    def test_no_license(self):
        assert extract_license_number("No license here") is None


# ---------------------------------------------------------------------------
# _join_continuation_line
# ---------------------------------------------------------------------------

class TestJoinContinuationLine:
    def _make_match(self, text, pattern=r'Agency Name:\s*([^\n]+)'):
        return re.search(pattern, text, re.IGNORECASE)

    def test_no_connector(self):
        text = "Agency Name: SAMARITAS - BAY\nAgency Address: 123 St"
        match = self._make_match(text)
        assert _join_continuation_line(text, match) == "SAMARITAS - BAY"

    def test_trailing_dash(self):
        text = "Agency Name: CATHOLIC CHARITIES WEST MICHIGAN -\nBENTON HARBOR\nAgency Address: 123"
        match = self._make_match(text)
        result = _join_continuation_line(text, match)
        assert result == "CATHOLIC CHARITIES WEST MICHIGAN - BENTON HARBOR"

    def test_trailing_ampersand(self):
        text = "Agency Name: CHARLEVOIX COUNTY PROBATE &\nFAMILY COURT\nFacility Address: 301"
        match = self._make_match(text)
        result = _join_continuation_line(text, match)
        assert result == "CHARLEVOIX COUNTY PROBATE & FAMILY COURT"

    def test_trailing_comma(self):
        text = "Licensee Name: Morning Star Adoption Resource Services,\nInc.\nLicensee Address: 123"
        match = self._make_match(text, r'Licensee Name:\s*([^\n]+)')
        result = _join_continuation_line(text, match)
        assert result == "Morning Star Adoption Resource Services, Inc."

    def test_no_continuation_into_field_label(self):
        """Should NOT join if next line is a field label like 'Agency Address:'."""
        text = "Agency Name: SOME AGENCY -\nAgency Address: 123 Main St"
        match = self._make_match(text)
        # The continuation is a field label so it should not be appended
        result = _join_continuation_line(text, match)
        assert result == "SOME AGENCY -"


# ---------------------------------------------------------------------------
# _clean_agency_name
# ---------------------------------------------------------------------------

class TestCleanAgencyName:
    def test_trailing_dash(self):
        assert _clean_agency_name("SOME AGENCY -") == "SOME AGENCY"

    def test_trailing_ampersand(self):
        assert _clean_agency_name("COUNTY PROBATE &") == "COUNTY PROBATE"

    def test_trailing_comma(self):
        assert _clean_agency_name("Agency Name,") == "Agency Name"

    def test_trailing_field_label(self):
        assert _clean_agency_name("Some Agency Facility Address: 123") == "Some Agency"

    def test_whitespace_normalisation(self):
        assert _clean_agency_name("  Multiple   Spaces  ") == "Multiple Spaces"

    def test_already_clean(self):
        assert _clean_agency_name("Good Name") == "Good Name"


# ---------------------------------------------------------------------------
# extract_agency_name  (integration-style)
# ---------------------------------------------------------------------------

class TestExtractAgencyName:
    def test_agency_name_field(self):
        text = "Some header\nAgency Name: SAMARITAS - BAY\nAgency Address: 123"
        assert extract_agency_name(text) == "SAMARITAS - BAY"

    def test_name_of_facility(self):
        text = "Header\nName of Facility: Traverse Place\nFacility Address: 512 S."
        assert extract_agency_name(text) == "Traverse Place"

    def test_continuation_line_dash(self):
        text = (
            "Header text\n"
            "Agency Name: CATHOLIC CHARITIES WEST MICHIGAN -\n"
            "BENTON HARBOR\n"
            "Agency Address: 185 E. MAIN\n"
        )
        assert extract_agency_name(text) == "CATHOLIC CHARITIES WEST MICHIGAN - BENTON HARBOR"

    def test_continuation_line_ampersand(self):
        text = (
            "Header\n"
            "Name of Agency: CHARLEVOIX COUNTY PROBATE &\n"
            "FAMILY COURT\n"
            "Facility Address: 301 STATE ST\n"
        )
        assert extract_agency_name(text) == "CHARLEVOIX COUNTY PROBATE & FAMILY COURT"

    def test_header_region_limit(self):
        """Matches deep in the document should be ignored."""
        # Put a valid pattern beyond the 5000-char header region
        padding = "x" * 6000
        text = padding + "\nAgency Name: WRONG AGENCY\n"
        assert extract_agency_name(text) is None

    def test_cover_letter_fallback_after_re(self):
        """If no structured fields exist, fall back to cover-letter name after RE:."""
        text = (
            "STATE OF MICHIGAN\n"
            "May 4, 2022\n"
            "John Smith\n"
            "Some Agency Name\n"
            "123 Main Street\n"
            "Detroit, MI 48201\n"
            "RE: License #: CB123456789\n"
            "Some Agency Name\n"
            "123 Main Street\n"
            "Detroit, MI 48201\n"
            "Dear Mr. Smith:\n"
        )
        result = extract_agency_name(text)
        assert result is not None
        assert "Some Agency Name" in result

    def test_cover_letter_fallback_before_re(self):
        """Fall back to cover-letter name before RE: if after-RE starts with Dear."""
        text = (
            "STATE OF MICHIGAN\n"
            "DEPARTMENT OF HEALTH AND HUMAN SERVICES\n"
            "GOVERNOR DIRECTOR\n"
            "May 4, 2022\n"
            "John Smith\n"
            "Berrien County Probate Court\n"
            "811 Port Street\n"
            "Saint Joseph, MI 49085\n"
            "RE: License #: CA110200973\n"
            "Dear Mr. Smith:\n"
        )
        result = extract_agency_name(text)
        assert result is not None
        assert "Berrien County Probate Court" in result


# ---------------------------------------------------------------------------
# _extract_cover_letter_name
# ---------------------------------------------------------------------------

class TestExtractCoverLetterName:
    def test_name_after_re_license(self):
        text = (
            "RE: License #: CB130201519\n"
            "Youth Guidance Foster Care\n"
            "70 Calhoun Street\n"
        )
        assert _extract_cover_letter_name(text) == "Youth Guidance Foster Care"

    def test_dear_after_re_skipped(self):
        """If 'Dear …' follows the license line, try the before-RE pattern."""
        text = (
            "May 4, 2022\n"
            "John Smith\n"
            "Youth Services Center\n"
            "123 Main St\n"
            "Detroit, MI 48201\n"
            "Re: License #: CB123456789\n"
            "Dear Mr. Smith:\n"
        )
        result = _extract_cover_letter_name(text)
        assert result == "Youth Services Center"

    def test_skips_person_name(self):
        """Should skip person names and find the agency name."""
        text = (
            "STATE OF MICHIGAN\n"
            "GOVERNOR DIRECTOR\n"
            "June 12, 2023\n"
            "John Smith\n"
            "BERRIEN COUNTY PROBATE COURT\n"
            "811 PORT ST,\n"
            "SAINT JOSEPH, MI, 49085\n"
            "Re: License #: CA110200973\n"
            "Dear John Smith:\n"
        )
        result = _extract_cover_letter_name(text)
        assert result == "BERRIEN COUNTY PROBATE COURT"
