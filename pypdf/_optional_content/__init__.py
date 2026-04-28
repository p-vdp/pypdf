"""Optional Content Group (OCG) support for pypdf.

This module provides classes and methods to work with Optional Content Groups (OCGs)
in PDF files. OCGs allow organizing content into layers that can be shown or hidden.

Functions:
    get_ocg_list(reader) -> List[str]
        Get a list of all OCG names in the PDF document.

    get_ocg_state(reader) -> Dict[str, bool]
        Get the current ON/OFF state of each OCG in the document.

    get_page_oc_properties(page) -> Optional[PageOCProperties]
        Get OCG properties for a specific page.

Classes:
    PageOCProperties
        Represents Optional Content properties for a page.
    OCGList
        Represents a collection of Optional Content Groups.
    OCG
        Represents an Optional Content Group (layer).
"""

from typing import Any, Dict, List, Optional, Union

from pypdf._page import PageObject, Transformation
from pypdf._reader import PdfReader
from pypdf._writer import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
)


class OCG:
    """Represents an Optional Content Group (layer).

    Attributes:
        name: The name of the OCG layer.
        used: Whether the OCG is used in the document.
        state: The current visibility state ('On' or 'Off').
    """

    def __init__(
        self,
        name: str,
        used: bool = True,
        state: str = "Off",
    ) -> None:
        """Initialize an OCG.

        Args:
            name: The name of the OCG.
            used: Whether the OCG is referenced in the document.
            state: Current visibility state ('On' or 'Off').
        """
        self.name = name
        self.used = used
        self.state = state

    @property
    def is_on(self) -> bool:
        """Check if the OCG is currently visible."""
        return self.state.lower() == "on"

    def __repr__(self) -> str:
        return f"<OCG name='{self.name}' used={self.used} state={self.state}>"


class OCGList:
    """Represents the collection of OCGs in a PDF document.

    Attributes:
        ocgs: List of OCG dictionaries with name and state.
        used_ocs: List of OCG names that are currently used.
        order: The OCG order array (optional).
        c_ocs: Optional Content Configuration Dictionary entries.
    """

    def __init__(
        self,
        ocgs: Optional[List[Dict[str, Any]]] = None,
        used_ocs: Optional[List[str]] = None,
        order: Optional[ArrayObject] = None,
        c_ocs: Optional[ArrayObject] = None,
    ) -> None:
        """Initialize OCG list.

        Args:
            ocgs: Optional list of OCG dictionaries with name and state.
            used_ocs: Optional list of used OCG names.
            order: The OCG order array.
            c_ocs: Optional Content Configuration Dictionary entries.
        """
        self.ocgs: List[Dict[str, Any]] = ocgs or []
        self.used_ocs: List[str] = used_ocs or []
        self.order: Optional[ArrayObject] = order
        self.c_ocs: Optional[ArrayObject] = c_ocs

    def add(self, name: str) -> None:
        """Add an OCG name to the list."""
        self.ocgs.append({"name": name, "state": True})

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an OCG by name."""
        for ocg in self.ocgs:
            if ocg["name"] == name:
                return ocg
        return None

    def remove(self, name: str) -> Optional[Dict[str, Any]]:
        """Remove an OCG by name."""
        for i, ocg in enumerate(self.ocgs):
            if ocg["name"] == name:
                removed = self.ocgs.pop(i)
                if name in self.used_ocs:
                    self.used_ocs.remove(name)
                return removed
        return None

    def toggle(self, name: str) -> Optional[Dict[str, Any]]:
        """Toggle the state of an OCG."""
        ocg = self.get(name)
        if ocg:
            ocg["state"] = "On" if ocg["state"] == "Off" else "Off"
            return ocg
        return None

    def set_all_on(self) -> None:
        """Set all OCGs to ON state."""
        for ocg in self.ocgs:
            ocg["state"] = "On"

    def set_all_off(self) -> None:
        """Set all OCGs to OFF state."""
        for ocg in self.ocgs:
            ocg["state"] = "Off"


class PageOCProperties:
    """Represents Optional Content properties for a PDF page."""

    def __init__(
        self,
        oc_properties: Optional[DictionaryObject] = None,
        used_ocs: Optional[List[str]] = None,
        order: Optional[ArrayObject] = None,
        c_ocs: Optional[ArrayObject] = None,
    ) -> None:
        """Initialize page OCG properties."""
        self.oc_properties: Optional[DictionaryObject] = oc_properties
        self.used_ocs: List[str] = used_ocs or []
        self.order: Optional[ArrayObject] = order
        self.c_ocs: Optional[ArrayObject] = c_ocs

    def get_ocgs(self) -> List[Dict[str, Any]]:
        """Get OCGs with their state from this page's properties.

        Returns:
            List of OCG dictionaries with name and state.
        """
        ocgs = []
        if self.oc_properties:
            for name in self.used_ocs:
                state = self.oc_properties.get(NameObject(f"/{name}"), NameObject("/Off"))
                ocgs.append({"name": name, "state": str(state)})
        return ocgs

    @property
    def ocgs(self) -> Optional[List[Dict[str, Any]]]:
        """Convenient property to access OCGs."""
        return self.get_ocgs()


def get_ocg_list(reader: PdfReader) -> List[str]:
    """Get a list of all OCG names in the PDF document.

    Args:
        reader: PdfReader instance.

    Returns:
        List of OCG names.

    Raises:
        PdfReadError: If no OCGs are found in the document.
    """
    try:
        ocs = reader.trailer["/Root"]["/OCProperties"]["/OCGs"]
        return [str(oc) for oc in ocs]
    except (KeyError, TypeError):
        return []


def get_ocg_state(reader: PdfReader) -> Dict[str, bool]:
    """Get the current ON/OFF state of each OCG in the document.

    Args:
        reader: PdfReader instance.

    Returns:
        Dictionary mapping OCG names to their ON/OFF state.
    """
    state: Dict[str, bool] = {}
    try:
        oc_properties = reader.trailer["/Root"]["/OCProperties"].get_object()
        used_ocs = oc_properties.get("/Used", [])
        if isinstance(used_ocs, (list, ArrayObject)):
            for oc_name in used_ocs:
                oc_name = str(oc_name)
                state[oc_name] = True
        else:
            used_ocs_list = [oc_name for oc_name in used_ocs]
            for oc_name in used_ocs_list:
                oc_name = str(oc_name)
                state[oc_name] = True
        # Check each OCG's specific state
        for oc_name in list(state.keys()):
            oc_state = oc_properties.get(
                NameObject(f"/{oc_name}"),
                NameObject("/Off"),
            )
            if oc_state == "/Off":
                state[oc_name] = False
    except (KeyError, TypeError):
        pass
    return state


def get_page_oc_properties(
    page: Union[Page, PageObject],
) -> Optional[PageOCProperties]:
    """Get OCG properties for a specific page.

    Args:
        page: The page to get OCG properties from.

    Returns:
        PageOCProperties object or None if no OCGs are defined.
    """
    if not hasattr(page, "/OC"):
        return None

    oc_properties = page.get("/OC", None)
    if oc_properties is None:
        return None

    prop = PageOCProperties()
    prop.oc_properties = oc_properties

    try:
        prop.used_ocs = [str(oc) for oc in oc_properties.get("/OC", [])]
        if "/Order" in oc_properties:
            prop.order = oc_properties["/Order"]
        if "/C" in oc_properties:
            prop.c_ocs = oc_properties["/C"]
    except (KeyError, TypeError):
        pass

    return prop


__all__ = [
    "OCG",
    "OCGList",
    "PageOCProperties",
    "get_ocg_list",
    "get_ocg_state",
    "get_page_oc_properties",
    "PdfReaderOCGIntegration",
    "PdfWriterOCGIntegration",
    "use_ocgs",
    "use_ocgs_writer",
]
