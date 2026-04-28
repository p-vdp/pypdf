"""Read Optional Content Group (OCG) information from PDF documents.

This module provides functionality to read OCG layer states and configurations
from PDF files.
"""

from typing import Any, Dict, List, Optional, Union

from pypdf._optional_content._types import OCGList, PageOCProperties, _OCReader
from pypdf._reader import PdfReader
from pypdf._utils import logger_warning
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, PdfObject


class _OCReader:
    """Internal reader for OCG information."""

    def __init__(self, reader: PdfReader) -> None:
        """Initialize the OCG reader.

        Args:
            reader: PdfReader instance to read OCG data from.
        """
        self._reader = reader
        self._ocgs: Optional[ArrayObject] = None
        self._used_ocs: Optional[ArrayObject] = None
        self._oc_properties: Optional[DictionaryObject] = None

    def _get_oc_properties(self) -> Optional[DictionaryObject]:
        """Get OCProperties dictionary from the catalog.

        Returns:
            OCProperties dictionary or None if not found.
        """
        try:
            return self._reader.trailer["/Root"].get("/OCProperties", None)
        except (KeyError, TypeError):
            return None

    def _get_ocgs(self) -> List[str]:
        """Get list of OCG names from the OCProperties.

        Returns:
            List of OCG names.
        """
        if self._ocgs is not None:
            return [str(oc) for oc in self._ocgs]

        oc_props = self._get_oc_properties()
        if oc_props is None:
            return []

        try:
            ocs = oc_props.get("/OCGs", ArrayObject())
            self._ocgs = ocs
            return [str(oc) for oc in ocs]
        except (KeyError, TypeError):
            logger_warning(
                "OCGs not found in OCProperties",
                __name__,
            )
            return []

    def _get_used_ocs(self) -> List[str]:
        """Get list of used OCG names.

        Returns:
            List of used OCG names.
        """
        if self._used_ocs is not None:
            return [str(oc) for oc in self._used_ocs]

        oc_props = self._get_oc_properties()
        if oc_props is None:
            return []

        try:
            used = oc_props.get("/Used", ArrayObject())
            if used is None:
                return []
            self._used_ocs = used
            return [str(oc) for oc in used]
        except (KeyError, TypeError):
            logger_warning(
                "Used OCGs not found in OCProperties",
                __name__,
            )
            return []

    def _get_state(self, name: str) -> str:
        """Get the state (On/Off) of a specific OCG.

        Args:
            name: The name of the OCG.

        Returns:
            The state string ("/On" or "/Off").
        """
        oc_props = self._get_oc_properties()
        if oc_props is None:
            return "/Off"

        try:
            # Default to Off if not specified
            return str(oc_props.get(NameObject(f"/{name}"), NameObject("/Off")))
        except (KeyError, TypeError):
            return "/Off"

    def _get_page_oc(
        self,
        page: Union[Any, None],
    ) -> Optional[DictionaryObject]:
        """Get OC dictionary for a specific page.

        Args:
            page: The page object.

        Returns:
            OC dictionary for the page or None.
        """
        if page is None:
            return None

        try:
            return page.get("/OC", None)
        except (KeyError, TypeError):
            return None

    def get_ocr_list(self) -> List[str]:
        """Get a list of all OCG names in the PDF document.

        Returns:
            List of OCG names.
        """
        return self._get_ocgs()

    def get_ocr_state(self) -> Dict[str, bool]:
        """Get the current ON/OFF state of each OCG.

        Returns:
            Dictionary mapping OCG names to their ON/OFF state.
        """
        state: Dict[str, bool] = {}
        ocg_list = self._get_ocgs()

        for name in ocg_list:
            state[name] = self._get_state(name) == "/On"

        return state

    def get_page_ocgs(
        self,
        page: Union[Any, None],
    ) -> Optional[PageOCProperties]:
        """Get OCG properties for a specific page.

        Args:
            page: The page object.

        Returns:
            PageOCProperties object or None if no OCGs are defined.
        """
        oc_dict = self._get_page_oc(page)
        if oc_dict is None:
            return None

        props = PageOCProperties()
        props.oc_properties = oc_dict

        try:
            # Use getattr() for safe attribute access on ArrayObject
            if "/OC" in oc_dict:
                oc_values = getattr(oc_dict, "/OC", ArrayObject())
                props.used_ocs = [str(oc) for oc in oc_values]
            if "/Order" in oc_dict:
                props.order = getattr(oc_dict, "/Order", ArrayObject())
            if "/C" in oc_dict:
                props.c_ocs = getattr(oc_dict, "/C", ArrayObject())
        except (KeyError, TypeError):
            pass

        return props

    def get_all_page_ocgs(self) -> Dict[str, PageOCProperties]:
        """Get OCG properties for all pages in the document.

        Returns:
            Dictionary mapping page numbers to PageOCProperties objects.
        """
        result: Dict[str, PageOCProperties] = {}
        pages = self._reader.pages

        for i, page in enumerate(pages):
            page_props = self.get_page_ocgs(page)
            if page_props:
                result[str(i)] = page_props

        return result


def get_ocg_list(reader: PdfReader) -> List[str]:
    """Get a list of all OCG names in the PDF document.

    Args:
        reader: PdfReader instance.

    Returns:
        List of OCG names.

    Raises:
        PdfReadError: If no OCGs are found in the document.
    """
    reader_obj = _OCReader(reader)
    return reader_obj.get_ocr_list()


def get_ocg_state(reader: PdfReader) -> Dict[str, bool]:
    """Get the current ON/OFF state of each OCG.

    Args:
        reader: PdfReader instance.

    Returns:
        Dictionary mapping OCG names to their ON/OFF state.
    """
    reader_obj = _OCReader(reader)
    return reader_obj.get_ocr_state()


def get_page_oc_properties(
    reader: PdfReader,
    page_number: int,
) -> Optional[PageOCProperties]:
    """Get OCG properties for a specific page.

    Args:
        reader: PdfReader instance.
        page_number: Page number to get OCG properties for.

    Returns:
        PageOCProperties object or None if no OCGs are defined.
    """
    # Handle None page input early
    if page_number is None:
        return None

    try:
        page = reader.pages[page_number]
    except (IndexError, TypeError):
        return None

    reader_obj = _OCReader(reader)
    return reader_obj.get_page_ocgs(page)
