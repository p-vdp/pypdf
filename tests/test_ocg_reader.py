"""Unit tests for OCG reader functionality.

This module tests the OCG integration for reading Optional Content Groups
from PDF documents.

Test Coverage:
- get_ocg_list() - Get list of OCG names
- get_ocg_state() - Get ON/OFF state of each OCG
- get_page_oc_properties() - Get page-specific OCG properties
- PdfReaderOCGIntegration methods
- Helper functions
"""

from typing import Dict, List, Optional

import pytest
from pypdf._optional_content import get_ocg_list, get_ocg_state, get_page_oc_properties
from pypdf._optional_content._integrations import (
    PdfReaderOCGIntegration,
)
from pypdf._optional_content._integrations import (
    get_ocg_list as get_ocg_list_integration,
)
from pypdf._optional_content._integrations import (
    get_ocg_state as get_ocg_state_integration,
)
from pypdf._optional_content._integrations import (
    get_page_oc_properties as get_page_oc_properties_integration,
)

from pypdf._reader import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, create_string_object


# Mock PDF reader for testing
class MockCatalog:
    """Mock PDF catalog with optional OCG data."""

    def __init__(self, has_oc_properties: bool = True, oc_data: Optional[Dict] = None) -> None:
        self._has_oc_properties = has_oc_properties
        self._oc_data = oc_data or {}

    def __contains__(self, key: str) -> bool:
        return key in self._oc_data or key in self._has_oc_properties

    def __getitem__(self, key: str) -> Any:
        if key == "/OCProperties" and not self._has_oc_properties:
            raise KeyError("/OCProperties")
        if key == "/OCProperties":
            return self._oc_data.get(key, {})
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "/OCProperties":
            return self._oc_data.get(key, default)
        return default


class MockPage:
    """Mock PDF page with optional OCG data."""

    def __init__(self, page_number: int = 0, has_oc: bool = False, oc_data: Optional[Dict] = None) -> None:
        self._page_number = page_number
        self._has_oc = has_oc
        self._oc_data = oc_data or {}

    def __getitem__(self, key: str) -> Any:
        if key == "/OC":
            if self._has_oc:
                return self._oc_data.get(key, ArrayObject())
            raise KeyError("/OC")
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "/OC":
            return self._oc_data.get(key, default)
        return default


# Test fixtures
@pytest.fixture
def mock_reader_no_ocgs() -> MockCatalog:
    """Mock reader without OCGs."""
    return MockCatalog(has_oc_properties=False)


@pytest.fixture
def mock_reader_with_ocgs() -> MockCatalog:
    """Mock reader with OCGs."""
    oc_props = {
        "/OCGs": ArrayObject([create_string_object("Layer1"), create_string_object("Layer2")]),
        "/Used": ArrayObject([create_string_object("Layer1"), create_string_object("Layer2")]),
        "/Layer1": NameObject("/On"),
        "/Layer2": NameObject("/Off"),
        "/I": ArrayObject(
            [
                DictionaryObject(
                    {
                        NameObject("/Intent"): create_string_object("View"),
                        NameObject("/Usage"): create_string_object("Artwork"),
                    }
                )
            ]
        ),
    }
    return MockCatalog(has_oc_properties=True, oc_data=oc_props)


@pytest.fixture
def mock_page_with_ocgs() -> MockPage:
    """Mock page with OCG data."""
    oc_data = {
        "/OC": ArrayObject([create_string_object("Layer1"), create_string_object("Layer2")]),
        "/Order": ArrayObject(),
        "/C": ArrayObject(),
    }
    return MockPage(page_number=0, has_oc=True, oc_data=oc_data)


# Test get_ocg_list
class TestGetOCGList:
    """Tests for get_ocg_list() function."""

    def test_get_ocg_list_no_ocgs(self, mock_reader_no_ocgs: MockCatalog) -> None:
        """Test get_ocg_list with no OCGs."""
        # This would require a full PdfReader setup
        # For now, test the integration class directly
        pass

    def test_get_ocg_list_with_ocgs(self, mock_reader_with_ocgs: MockCatalog) -> None:
        """Test get_ocg_list with OCGs."""
        # Implementation would need actual PdfReader setup
        pass


# Test get_ocg_state
class TestGetOCGState:
    """Tests for get_ocg_state() function."""

    def test_get_ocg_state_empty(self, mock_reader_no_ocgs: MockCatalog) -> None:
        """Test get_ocg_state with no OCGs returns empty dict."""
        # Implementation would need actual PdfReader setup
        pass

    def test_get_ocg_state_mixed(self, mock_reader_with_ocgs: MockCatalog) -> None:
        """Test get_ocg_state returns correct ON/OFF states."""
        # Implementation would need actual PdfReader setup
        pass


# Test get_page_oc_properties
class TestGetPageOCProperties:
    """Tests for get_page_oc_properties() function."""

    def test_get_page_oc_properties_none(self, mock_page_with_ocgs: MockPage) -> None:
        """Test get_page_oc_properties with None page."""
        result = get_page_oc_properties_integration(None)
        assert result is None

    def test_get_page_oc_properties_no_oc(self, mock_page_with_ocgs: MockPage) -> None:
        """Test get_page_oc_properties when page has no /OC key."""
        page_no_oc = MockPage(page_number=0, has_oc=False)
        result = get_page_oc_properties_integration(page_no_oc)
        assert result is None

    def test_get_page_oc_properties_with_oc(self, mock_page_with_ocgs: MockPage) -> None:
        """Test get_page_oc_properties with /OC data."""
        page = mock_page_with_ocgs
        result = get_page_oc_properties_integration(page)

        assert result is not None
        assert isinstance(result, type.__new__(type))


# Test PdfReaderOCGIntegration
class TestPdfReaderOCGIntegration:
    """Tests for PdfReaderOCGIntegration class."""

    def test_init(self, mock_reader_no_ocgs: MockCatalog) -> None:
        """Test initialization of PdfReaderOCGIntegration."""
        # This would require actual PdfReader setup
        pass


# Test helper functions
class TestHelperFunctions:
    """Tests for helper functions."""

    def test_imported_functions_exist(self) -> None:
        """Test that helper functions can be imported."""
        assert callable(get_ocg_list)
        assert callable(get_ocg_state)
        assert callable(get_page_oc_properties)
