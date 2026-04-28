"""Optional Content Group (OCG) integration utility for pypdf.

This module provides helper functions and classes to integrate OCG support
into PdfReader and PdfWriter without modifying their core definitions.

Usage with PdfReader:
    from pypdf._optional_content._integrations import use_ocgs
    from pypdf import PdfReader

    reader = PdfReader("document.pdf")
    integration = use_ocgs(reader)
    ocg_names = integration.get_ocg_list()

Usage with PdfWriter:
    from pypdf._optional_content._integrations import use_ocgs_writer
    from pypdf import PdfWriter

    writer = PdfWriter()
    integration = use_ocgs_writer(writer)
    integration.add_ocg("MyLayer")

Note: The integration functions use the underlying OCG API from
pypdf._optional_content to provide a clean, non-intrusive interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Union, cast

from pypdf._optional_content import OCG, OCGList, PageOCProperties
from pypdf._reader import PdfReader
from pypdf._writer import PdfWriter
from pypdf.errors import PdfReadError, PyPdfError
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    create_string_object,
)


def get_ocg_list(reader: PdfReader) -> List[str]:
    """Get a list of all OCG names in the PDF document.

    Args:
        reader: PdfReader instance.

    Returns:
        List of OCG names. Returns empty list if no OCGs are found.

    Raises:
        PdfReadError: If no OCGs are found in the document.
    """
    try:
        ocs = reader.trailer["/Root"]["/OCProperties"]["/OCGs"]
        return [str(oc) for oc in ocs]
    except (KeyError, TypeError):
        return []


def get_ocg_state(reader: PdfReader) -> dict[str, bool]:
    """Get the current ON/OFF state of each OCG in the document.

    Args:
        reader: PdfReader instance.

    Returns:
        Dictionary mapping OCG names to their state (True=ON, False=OFF).
    """
    state: Dict[str, bool] = {}
    try:
        oc_properties = reader.trailer["/Root"]["/OCProperties"].get_object()
        used_ocs = oc_properties.get("/Used", [])
        if isinstance(used_ocs, list):
            for oc_name in used_ocs:
                oc_name = str(oc_name)
                state[oc_name] = True
        else:
            used_ocs_list: list[Any] = list(used_ocs)
            for oc_name in used_ocs_list:
                oc_name = str(oc_name)
                state[oc_name] = True
        # Check each OCG's specific state
        for oc_name in list(state.keys()):
            oc_state = oc_properties.get(NameObject(f"/{oc_name}"), NameObject("/Off"))
            if oc_state == NameObject("/Off"):
                state[oc_name] = False
    except (KeyError, TypeError):
        pass
    return state


def get_page_oc_properties(
    page: Union[Any, "pypdf._page.PageObject"],
) -> Optional[PageOCProperties]:
    """Get OCG properties for a specific page.

    Args:
        page: The page to get OCG properties from.

    Returns:
        PageOCProperties object or None if no OCGs are defined.
    """
    if page is None:
        return None
    oc_properties = getattr(page, "/OC", None)
    if oc_properties is None:
        return None

    prop = PageOCProperties()
    prop.oc_properties = oc_properties

    try:
        used_ocs_list = getattr(oc_properties, "/OC", [])
        prop.used_ocs = [str(oc) for oc in used_ocs_list]
        if "/Order" in oc_properties:
            prop.order = getattr(oc_properties, "/Order", None)
        if "/C" in oc_properties:
            prop.c_ocs = getattr(oc_properties, "/C", None)
    except (KeyError, TypeError):
        pass

    return prop


class PdfReaderOCGIntegration:
    """Integration class to provide OCG functionality to PdfReader.

    This class wraps the OCG API to provide a clean interface for working
    with Optional Content Groups in a PDF document.

    Example:
        >>> from pypdf import PdfReader
        >>> from pypdf._optional_content._integrations import use_ocgs
        >>> reader = PdfReader("document.pdf")
        >>> integration = use_ocgs(reader)
        >>> ocg_names = integration.get_ocg_list()
    """

    def __init__(self, reader: PdfReader) -> None:
        """Initialize the integration with a PdfReader instance.

        Args:
            reader: PdfReader instance to add OCG functionality to.
        """
        self.reader: PdfReader = reader

    def get_ocg_list(self) -> List[str]:
        """Get a list of all OCG names in the PDF document.

        Returns:
            List of OCG names.
        """
        return get_ocg_list(self.reader)

    def get_ocg_state(self) -> Dict[str, bool]:
        """Get the current ON/OFF state of each OCG in the document.

        Returns:
            Dictionary mapping OCG names to their ON/OFF state.
        """
        return get_ocg_state(self.reader)

    def get_page_oc_properties(
        self,
        page: Union[Any, "pypdf._page.PageObject"],
    ) -> Optional[PageOCProperties]:
        """Get OCG properties for a specific page.

        Args:
            page: The page to get OCG properties from.

        Returns:
            PageOCProperties object or None if no OCGs are defined.
        """
        return get_page_oc_properties(page)

    def add_ocg(self, name: str) -> None:
        """Add an OCG name to the list.

        Args:
            name: The name of the OCG to add.

        Raises:
            PdfReadError: If the OCG is not found or cannot be added.
        """
        # Check if OCG exists in the PDF
        try:
            oc_properties = self.reader.trailer["/Root"]["/OCProperties"].get_object()
            if f"/{name}" not in oc_properties:
                raise PdfReadError(f"OCG '{name}' not found in document")
        except (KeyError, TypeError):
            # No OCGs in document
            raise PdfReadError("No OCGs found in document")

    def set_ocg_state(
        self,
        name: str,
        on: bool = True,
    ) -> None:
        """Set the state of an OCG to ON or OFF.

        Args:
            name: The name of the OCG to set.
            on: Whether to set the OCG to ON (default: True).

        Raises:
            PdfReadError: If the OCG is not found or cannot be modified.
        """
        try:
            oc_properties = self.reader.trailer["/Root"]["/OCProperties"].get_object()
            state_obj = NameObject("/On") if on else NameObject("/Off")
            oc_properties[NameObject(f"/{name}")] = state_obj
        except (KeyError, TypeError):
            raise PdfReadError("Cannot modify OCG state")

    def toggle_ocg(self, name: str) -> None:
        """Toggle the state of an OCG.

        Args:
            name: The name of the OCG to toggle.

        Raises:
            PdfReadError: If the OCG is not found or cannot be toggled.
        """
        state = self.get_ocg_state().get(name, False)
        self.set_ocg_state(name, on=not state)

    def remove_ocg(self, name: str) -> None:
        """Remove an OCG from the document.

        Args:
            name: The name of the OCG to remove.

        Raises:
            PdfReadError: If the OCG is not found or cannot be removed.
        """
        try:
            oc_properties = self.reader.trailer["/Root"]["/OCProperties"].get_object()
            if f"/{name}" in oc_properties:
                del oc_properties[NameObject(f"/{name}")]
        except (KeyError, TypeError):
            raise PdfReadError("Cannot remove OCG")


class PdfWriterOCGIntegration:
    """Integration class to provide OCG functionality to PdfWriter.

    This class wraps the OCG API to provide a clean interface for working
    with Optional Content Groups when writing a PDF document.

    Example:
        >>> from pypdf import PdfWriter
        >>> from pypdf._optional_content._integrations import use_ocgs_writer
        >>> writer = PdfWriter()
        >>> integration = use_ocgs_writer(writer)
        >>> integration.add_ocg("MyLayer")
        >>> integration.set_ocg_state("MyLayer", on=True)
    """

    def __init__(self, writer: PdfWriter) -> None:
        """Initialize the integration with a PdfWriter instance.

        Args:
            writer: PdfWriter instance to add OCG functionality to.
        """
        self.writer: PdfWriter = writer

    def add_ocg(
        self,
        name: str,
        used: bool = True,
        intent: str = "View",
        usage: str = "Artwork",
    ) -> None:
        """Add a new OCG to the document.

        Args:
            name: Name of the OCG.
            used: Whether the OCG is used in the document.
            intent: The intent of the OCG (default "View").
            usage: The usage of the OCG (default "Artwork").

        Raises:
            ValueError: If the name is empty or invalid.
        """
        if not name or not isinstance(name, str):
            raise ValueError("OCG name must be a non-empty string")

        # Get or create OCProperties
        if "/OCProperties" not in self.writer.root_object:
            oc_props = DictionaryObject(
                {
                    NameObject("/OCGs"): ArrayObject(),
                    NameObject("/Used"): ArrayObject(),
                }
            )
            self.writer._add_object(oc_props)
            self.writer.root_object[NameObject("/OCProperties")] = oc_props

        # Get OCProperties object
        oc_props_obj = self.writer.root_object["/OCProperties"]
        oc_props_dict = oc_props_obj.get_object()

        # Add to OCGs array
        if "/OCGs" not in oc_props_dict:
            oc_props_dict[NameObject("/OCGs")] = ArrayObject()
        ocs_list = oc_props_dict[NameObject("/OCGs")]
        if isinstance(ocs_list, ArrayObject):
            ocs_list.append(create_string_object(name))

        # Add to Used array if enabled
        if used:
            if "/Used" not in oc_props_dict:
                oc_props_dict[NameObject("/Used")] = ArrayObject()
            used_list = oc_props_dict[NameObject("/Used")]
            if isinstance(used_list, ArrayObject):
                used_list.append(create_string_object(name))

        # Add state (default to Off)
        oc_props_dict[NameObject(f"/{name}")] = NameObject("/Off")

        # Add intent and usage
        if "/I" not in oc_props_dict:
            oc_props_dict[NameObject("/I")] = ArrayObject()
        intent_list = oc_props_dict[NameObject("/I")]
        if isinstance(intent_list, ArrayObject):
            intent_dict = DictionaryObject(
                {
                    NameObject("/Intent"): create_string_object(intent),
                    NameObject("/Usage"): create_string_object(usage),
                }
            )
            intent_list.append(intent_dict)

    def remove_ocg(self, name: str) -> Optional[str]:
        """Remove an OCG from the document.

        Args:
            name: The name of the OCG to remove.

        Returns:
            The name of the removed OCG or None if not found.

        Raises:
            ValueError: If the name is empty or invalid.
        """
        if not name or not isinstance(name, str):
            raise ValueError("OCG name must be a non-empty string")

        try:
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()

            # Remove from OCGs array
            if NameObject("/OCGs") in ocp_obj:
                ocs_list = ocp_obj[NameObject("/OCGs")]
                if isinstance(ocs_list, ArrayObject):
                    try:
                        idx = ocs_list.index(name)
                        del ocs_list[idx]
                    except (IndexError, TypeError, ValueError):
                        pass

            # Remove from Used array
            if NameObject("/Used") in ocp_obj:
                used_list = ocp_obj[NameObject("/Used")]
                if isinstance(used_list, ArrayObject):
                    try:
                        idx = used_list.index(name)
                        del used_list[idx]
                    except (IndexError, TypeError, ValueError):
                        pass

            # Remove state entry
            state_key = NameObject(f"/{name}")
            if state_key in ocp_obj:
                del ocp_obj[state_key]

            # Remove from intent/usage if empty
            if NameObject("/I") in ocp_obj:
                intent_list = ocp_obj[NameObject("/I")]
                if isinstance(intent_list, ArrayObject):
                    # Check if this is the only intent for this name
                    remaining_intents = [
                        i
                        for i in intent_list
                        if isinstance(i, DictionaryObject) and i.get(NameObject("/Intent")) != name
                    ]
                    if len(remaining_intents) == 0:
                        del ocp_obj[NameObject("/I")]

            return name
        except Exception:
            return None

    def set_ocg_state(self, name: str, on: bool = True) -> None:
        """Set the state of an OCG.

        Args:
            name: The name of the OCG.
            on: Whether the OCG should be ON or OFF.

        Raises:
            ValueError: If the name is empty or invalid.
        """
        if not name or not isinstance(name, str):
            raise ValueError("OCG name must be a non-empty string")

        try:
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()
            state = NameObject("/On") if on else NameObject("/Off")
            ocp_obj[NameObject(f"/{name}")] = state
        except Exception:
            pass

    def toggle_ocg(self, name: str) -> Optional[str]:
        """Toggle the state of an OCG.

        Args:
            name: The name of the OCG to toggle.

        Returns:
            The name of the toggled OCG or None if not found.

        Raises:
            ValueError: If the name is empty or invalid.
        """
        if not name or not isinstance(name, str):
            raise ValueError("OCG name must be a non-empty string")

        try:
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()
            state_key = NameObject(f"/{name}")

            current_state = ocp_obj.get(state_key, NameObject("/Off"))
            new_state = NameObject("/On") if current_state == NameObject("/Off") else NameObject("/Off")
            ocp_obj[state_key] = new_state

            return name
        except Exception:
            return None

    def set_layer(self, layer_name: Optional[str], on: bool = True) -> None:
        """Set a layer configuration (all OCGs ON or OFF, or specific OCG).

        Args:
            layer_name: Optional layer name or "/AllOn"/"/AllOff".
            on: Whether the layer should be ON.

        Raises:
            ValueError: If an invalid layer name is provided.
        """
        if layer_name is None:
            # Default layer
            return

        if layer_name in ("/AllOn", "/AllOff"):
            if layer_name == "/AllOn":
                for ocg_name in self.get_ocg_list():
                    self.set_ocg_state(ocg_name, True)
            else:
                for ocg_name in self.get_ocg_list():
                    self.set_ocg_state(ocg_name, False)
        else:
            self.set_ocg_state(layer_name, on)

    def copy_ocg(
        self,
        from_name: str,
        to_name: str,
        on: bool = True,
    ) -> Optional[str]:
        """Copy an OCG to a new name.

        Args:
            from_name: Source OCG name.
            to_name: Destination OCG name.
            on: Whether to copy the OCG to ON state.

        Returns:
            The name of the copied OCG or None if not found.

        Raises:
            ValueError: If names are empty or invalid.
        """
        if not from_name or not isinstance(from_name, str):
            raise ValueError("from_name must be a non-empty string")
        if not to_name or not isinstance(to_name, str):
            raise ValueError("to_name must be a non-empty string")

        try:
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()

            # Add to OCGs array
            if NameObject("/OCGs") not in ocp_obj:
                ocp_obj[NameObject("/OCGs")] = ArrayObject()
            ocp_obj[NameObject("/OCGs")].append(create_string_object(to_name))

            # Copy state
            state_key = NameObject(f"/{from_name}")
            source_state = ocp_obj.get(state_key, NameObject("/Off"))
            ocp_obj[NameObject(f"/{to_name}")] = source_state if on else NameObject("/Off")

            # Copy intent/usage if exists
            if NameObject("/I") in ocp_obj:
                intent_list = ocp_obj[NameObject("/I")]
                if isinstance(intent_list, ArrayObject):
                    for intent_obj in intent_list:
                        if isinstance(intent_obj, DictionaryObject):
                            if intent_obj.get(NameObject("/Intent")) == from_name:
                                intent_list.append(intent_obj)
                                break

            return to_name
        except Exception:
            return None

    def get_ocg_list(self) -> List[str]:
        """Get list of all OCG names.

        Returns:
            List of OCG names.
        """
        try:
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()
            ocgs: List[str] = []

            for oc_name in ocp_obj.get(NameObject("/OCGs"), ArrayObject()):
                ocgs.append(str(oc_name))

            return ocgs
        except Exception:
            return []

    def get_ocg_states(self) -> Dict[str, bool]:
        """Get the ON/OFF state of each OCG.

        Returns:
            Dictionary mapping OCG names to their states.
        """
        states: Dict[str, bool] = {}
        for name in self.get_ocg_list():
            state_key = NameObject(f"/{name}")
            state = ocp_obj.get(state_key, NameObject("/Off"))
            states[name] = state == NameObject("/On")
        return states

    def get_ocg(self, name: str) -> Optional[str]:
        """Get a specific OCG by name.

        Args:
            name: Name of the OCG.

        Returns:
            OCG name or None if not found.
        """
        try:
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()
            states = self.get_ocg_list()
            for ocg in states:
                state_key = NameObject(f"/{ocg}")
                if ocp_obj.get(state_key, NameObject("/Off")) == NameObject("/On"):
                    return ocg
            return None
        except Exception:
            return None

    def _get_or_create_oc_properties(self) -> DictionaryObject:
        """Get or create OCProperties dictionary.

        Returns:
            OCProperties dictionary.
        """
        if "/OCProperties" not in self.writer.root_object:
            oc_props = DictionaryObject(
                {
                    NameObject("/OCGs"): ArrayObject(),
                    NameObject("/Used"): ArrayObject(),
                }
            )
            self.writer._add_object(oc_props)
            self.writer.root_object[NameObject("/OCProperties")] = oc_props
        return self.writer.root_object["/OCProperties"]

    def get_ocg_state(self) -> Dict[str, bool]:
        """Get the current ON/OFF state of each OCG in the document.

        Returns:
            Dictionary mapping OCG names to their states.
        """
        return get_ocg_state(self.writer)

    def __enter__(self) -> "PdfWriterOCGIntegration":
        """Enable context manager for automatic cleanup."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[Type[BaseException]],
    ) -> None:
        """Clean up on exit."""
        pass


def use_ocgs(reader: PdfReader) -> PdfReaderOCGIntegration:
    """Enable OCG support for a PdfReader.

    Args:
        reader: PdfReader instance to add OCG support to.

    Returns:
        PdfReaderOCGIntegration instance with methods for OCG management.

    Example:
        >>> from pypdf import PdfReader
        >>> reader = PdfReader("document.pdf")
        >>> integration = use_ocgs(reader)
        >>> ocg_names = integration.get_ocg_list()
    """
    return PdfReaderOCGIntegration(reader)


def use_ocgs_writer(writer: PdfWriter) -> PdfWriterOCGIntegration:
    """Enable OCG support for a PdfWriter.

    Args:
        writer: PdfWriter instance to add OCG support to.

    Returns:
        PdfWriterOCGIntegration instance with methods for OCG management.

    Example:
        >>> from pypdf import PdfWriter
        >>> writer = PdfWriter()
        >>> integration = use_ocgs_writer(writer)
        >>> integration.add_ocg("MyLayer")
    """
    return PdfWriterOCGIntegration(writer)
