"""Type definitions for Optional Content Group (OCG) support.

This module provides type definitions and helper classes for the OCG module.
"""

from typing import Any, Dict, List, Optional, Union

from pypdf.generic import ArrayObject, DictionaryObject, NameObject


class OCGList:
    """Represents the collection of OCGs in a PDF document."""

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert OCG list to dictionary representation.

        Returns:
            Dictionary with all OCG information.
        """
        return {
            "ocgs": self.ocgs,
            "used_ocs": self.used_ocs,
            "order": self.order,
            "c_ocs": self.c_ocs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OCGList":
        """Create OCGList from dictionary.

        Args:
            data: Dictionary with OCG information.

        Returns:
            OCGList instance.
        """
        return cls(
            ocgs=data.get("ocgs", []),
            used_ocs=data.get("used_ocs", []),
            order=data.get("order"),
            c_ocs=data.get("c_ocs"),
        )


class PageOCProperties:
    """Represents Optional Content properties for a PDF page."""

    def __init__(
        self,
        oc_properties: Optional[DictionaryObject] = None,
        used_ocs: Optional[List[str]] = None,
        order: Optional[ArrayObject] = None,
        c_ocs: Optional[ArrayObject] = None,
    ) -> None:
        """Initialize page OCG properties.

        Args:
            oc_properties: The OCG dictionary for the page.
            used_ocs: List of used OCG names.
            order: The OCG order array.
            c_ocs: Optional Content Configuration Dictionary entries.
        """
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
                ocgs.append({"name": name, "state": state})
        return ocgs

    @property
    def ocgs(self) -> Optional[List[Dict[str, Any]]]:
        """Convenient property to access OCGs."""
        return self.get_ocgs()


class _OCReader:
    """Internal reader for OCG information."""

    def __init__(self, reader: Any) -> None:
        """Initialize the OCG reader.

        Args:
            reader: PdfReader instance to read OCG data from.
        """
        self._reader = reader
        self._ocgs: Optional[ArrayObject] = None
        self._used_ocs: Optional[ArrayObject] = None
        self._oc_properties: Optional[DictionaryObject] = None

    def _get_oc_properties(self) -> Optional[DictionaryObject]:
        """Get OCProperties dictionary from the catalog."""
        try:
            return self._reader.trailer["/Root"].get("/OCProperties", None)
        except (KeyError, TypeError):
            return None

    def _get_ocgs(self) -> List[str]:
        """Get list of OCG names from the OCProperties."""
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
            return []

    def _get_used_ocs(self) -> List[str]:
        """Get list of used OCG names."""
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
            return []

    def _get_state(self, name: str) -> str:
        """Get the state (On/Off) of a specific OCG."""
        oc_props = self._get_oc_properties()
        if oc_props is None:
            return "/Off"

        try:
            return str(oc_props.get(NameObject(f"/{name}"), NameObject("/Off")))
        except (KeyError, TypeError):
            return "/Off"

    def _get_page_oc(self, page: Optional[Any]) -> Optional[DictionaryObject]:
        """Get OC dictionary for a specific page."""
        if page is None:
            return None

        try:
            return page.get("/OC", None)
        except (KeyError, TypeError):
            return None

    def get_ocr_list(self) -> List[str]:
        """Get a list of all OCG names in the PDF document."""
        return self._get_ocgs()

    def get_ocr_state(self) -> Dict[str, bool]:
        """Get the current ON/OFF state of each OCG."""
        state: Dict[str, bool] = {}
        ocg_list = self._get_ocgs()

        for name in ocg_list:
            state[name] = self._get_state(name) == "/On"

        return state

    def get_page_ocgs(
        self,
        page: Optional[Any],
    ) -> Optional[PageOCProperties]:
        """Get OCG properties for a specific page."""
        oc_dict = self._get_page_oc(page)
        if oc_dict is None:
            return None

        props = PageOCProperties()
        props.oc_properties = oc_dict

        try:
            props.used_ocs = [str(oc) for oc in oc_dict.get("/OC", ArrayObject())]
            if "/Order" in oc_dict:
                props.order = oc_dict["/Order"]
            if "/C" in oc_dict:
                props.c_ocs = oc_dict["/C"]
        except (KeyError, TypeError):
            pass

        return props

    def get_all_page_ocgs(self) -> Dict[str, PageOCProperties]:
        """Get OCG properties for all pages in the document."""
        result: Dict[str, PageOCProperties] = {}
        pages = self._reader.pages

        for i, page in enumerate(pages):
            page_props = self.get_page_ocgs(page)
            if page_props:
                result[str(i)] = page_props

        return result


class _OCWriter:
    """Internal writer for OCG information."""

    def __init__(self, writer: Any) -> None:
        """Initialize the OCG writer.

        Args:
            writer: PdfWriter instance to write OCG data to.
        """
        self._writer = writer
        self._ocgs: List[Dict[str, Any]] = []
        self._oc_properties: Optional[DictionaryObject] = None

    def _get_or_create_oc_properties(self) -> DictionaryObject:
        """Get or create OCProperties dictionary."""
        if self._oc_properties is None:
            self._oc_properties = self._writer._add_object(DictionaryObject({NameObject("/OCGs"): ArrayObject()}))
            self._writer.root_object[NameObject("/OCProperties")] = self._oc_properties
        return self._oc_properties

    def add_ocg(
        self,
        name: str,
        used: bool = True,
        intent: str = "View",
        usage: str = "Artwork",
    ) -> str:
        """Add a new OCG to the document.

        Args:
            name: Name of the OCG.
            used: Whether the OCG is used in the document.
            intent: The intent of the OCG.
            usage: The usage of the OCG.

        Returns:
            The indirect reference of the added OCG.
        """
        ocp = self._get_or_create_oc_properties()

        # Add to OCGs array
        ocp[NameObject("/OCGs")].append(create_string_object(name))

        # Add to Used array if enabled
        if used:
            if "/Used" not in ocp:
                ocp[NameObject("/Used")] = ArrayObject()
            ocp[NameObject("/Used")].append(create_string_object(name))

        # Add state (default to Off)
        ocp[NameObject(f"/{name}")] = NameObject("/Off")

        # Add intent and usage
        if "/I" not in ocp:
            ocp[NameObject("/I")] = ArrayObject()
        ocp[NameObject("/I")].append(
            DictionaryObject(
                {
                    NameObject("/Intent"): create_string_object(intent),
                    NameObject("/Usage"): create_string_object(usage),
                }
            )
        )

        return str(ocp.indirect_reference)

    def remove_ocg(self, name: str) -> Optional[str]:
        """Remove an OCG from the document.

        Args:
            name: Name of the OCG to remove.

        Returns:
            The name of the removed OCG or None if not found.
        """
        ocp = self._get_or_create_oc_properties()

        # Remove from OCGs array
        if "/OCGs" in ocp:
            try:
                idx = ocp[NameObject("/OCGs")].index(name)
                del ocp[NameObject("/OCGs")][idx]
            except (IndexError, TypeError):
                pass

        # Remove from Used array
        if "/Used" in ocp:
            try:
                used_list = cast(ArrayObject, ocp[NameObject("/Used")])
                if used_list is not None:
                    try:
                        idx = used_list.index(name)
                        del used_list[idx]
                    except (IndexError, TypeError):
                        pass
            except (KeyError, TypeError):
                pass

        # Remove state entry
        if f"/{name}" in ocp:
            del ocp[f"/{name}"]

        # Remove from intent/usage
        if "/I" in ocp:
            try:
                intent_list = ocp[NameObject("/I")]
                if intent_list is not None:
                    # Check if this is the only intent for this name
                    intent_dict: Optional[Dict[str, Any]] = None
                    for intent_obj in intent_list:
                        if isinstance(intent_obj, DictionaryObject):
                            intent_dict = intent_obj
                            if intent_dict.get(NameObject("/Intent")) == name:
                                break
                    if intent_dict and len(intent_list) == 1:
                        del ocp[NameObject("/I")]

            except (IndexError, TypeError):
                pass

        return name

    def set_ocg_state(self, name: str, on: bool) -> None:
        """Set the state of an OCG.

        Args:
            name: Name of the OCG.
            on: Whether the OCG should be ON or OFF.
        """
        ocp = self._get_or_create_oc_properties()

        state = NameObject("/On") if on else NameObject("/Off")
        ocp[NameObject(f"/{name}")] = state

    def set_layer(self, name: Optional[str] = None, on: bool = True) -> None:
        """Set a layer configuration (all OCGs ON or OFF, or specific OCG).

        Args:
            name: Optional layer name or "AllOn"/"AllOff".
            on: Whether the layer should be ON.

        Raises:
            ValueError: If an invalid layer name is provided.
        """
        if name is None:
            # Default layer
            return

        if name in ("/AllOn", "/AllOff"):
            if name == "/AllOn":
                for ocg in self._ocgs:
                    self.set_ocg_state(ocg["name"], True)
            else:
                for ocg in self._ocgs:
                    self.set_ocg_state(ocg["name"], False)
        else:
            self.set_ocg_state(name, on)

    def get_ocg_list(self) -> List[Dict[str, Any]]:
        """Get list of all OCGs with their states.

        Returns:
            List of OCG dictionaries with name and state.
        """
        ocp = self._get_or_create_oc_properties()
        ocgs = []

        for oc_name in ocp.get(NameObject("/OCGs"), ArrayObject()):
            name = str(oc_name)
            state = str(ocp.get(NameObject(f"/{name}"), NameObject("/Off")))
            ocgs.append({"name": name, "state": state})

        return ocgs

    def get_ocg_states(self) -> Dict[str, bool]:
        """Get the ON/OFF state of each OCG.

        Returns:
            Dictionary mapping OCG names to their ON/OFF state.
        """
        states: Dict[str, bool] = {}
        for ocg in self.get_ocg_list():
            states[ocg["name"]] = ocg["state"] == "/On"
        return states


# Import needed types
from typing import Any, Dict, List, Optional, Union, cast

__all__ = [
    "OCGList",
    "PageOCProperties",
    "_OCReader",
    "_OCWriter",
]
