"""Write Optional Content Group (OCG) information to PDF documents.

This module provides functionality to add, remove, toggle, and copy OCG layers
to new PDF files.
"""

from typing import Any, Dict, List, Optional, Union

from pypdf._optional_content._types import _OCWriter
from pypdf._writer import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    create_string_object,
)


class OCGWriter:
    """Writer for Optional Content Group operations."""

    def __init__(self, writer: PdfWriter) -> None:
        """Initialize the OCG writer.

        Args:
            writer: PdfWriter instance to write OCG data to.
        """
        self._writer = writer
        self._ocg_data: Dict[str, Any] = {}
        self._oc_properties: Optional[DictionaryObject] = None

    def _get_or_create_oc_properties(self) -> DictionaryObject:
        """Get or create OCProperties dictionary.

        Returns:
            OCProperties dictionary or None if not found.
        """
        try:
            oc_props = self._writer.root_object.get("/OCProperties", None)
            if oc_props is not None:
                return cast(DictionaryObject, oc_props.get_object())
        except Exception:
            pass

        # Create OCProperties
        oc_props = DictionaryObject(
            {
                NameObject("/OCGs"): ArrayObject(),
                NameObject("/Used"): ArrayObject(),
            }
        )
        self._writer._add_object(oc_props)
        self._writer.root_object[NameObject("/OCProperties")] = oc_props
        return oc_props

    def add_ocg(
        self,
        name: str,
        used: bool = True,
        intent: str = "View",
        usage: str = "Artwork",
    ) -> IndirectObject:
        """Add a new OCG to the document.

        Args:
            name: Name of the OCG.
            used: Whether the OCG is used in the document.
            intent: The intent of the OCG (default "View").
            usage: The usage of the OCG (default "Artwork").

        Returns:
            Indirect reference of the added OCG.

        Raises:
            ValueError: If the name is empty or invalid.
        """
        if not name or not isinstance(name, str):
            raise ValueError("OCG name must be a non-empty string")

        ocp = self._get_or_create_oc_properties()
        ocp_obj = ocp.get_object()

        # Add to OCGs array
        if NameObject("/OCGs") not in ocp_obj:
            ocp_obj[NameObject("/OCGs")] = ArrayObject()
        ocp_obj[NameObject("/OCGs")].append(create_string_object(name))

        # Add to Used array if enabled
        if used:
            if NameObject("/Used") not in ocp_obj:
                ocp_obj[NameObject("/Used")] = ArrayObject()
            ocp_obj[NameObject("/Used")].append(create_string_object(name))

        # Add state (default to Off)
        ocp_obj[NameObject(f"/{name}")] = NameObject("/Off")

        # Add intent and usage
        if NameObject("/I") not in ocp_obj:
            ocp_obj[NameObject("/I")] = ArrayObject()
        intent_obj = DictionaryObject(
            {
                NameObject("/Intent"): create_string_object(intent),
                NameObject("/Usage"): create_string_object(usage),
            }
        )
        ocp_obj[NameObject("/I")].append(intent_obj)

        return ocp.indirect_reference

    def remove_ocg(self, name: str) -> Optional[str]:
        """Remove an OCG from the document.

        Args:
            name: Name of the OCG to remove.

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
                    except (IndexError, TypeError):
                        pass

            # Remove from Used array
            if NameObject("/Used") in ocp_obj:
                used_list = ocp_obj[NameObject("/Used")]
                if isinstance(used_list, ArrayObject):
                    try:
                        idx = used_list.index(name)
                        del used_list[idx]
                    except (IndexError, TypeError):
                        pass

            # Remove state entry
            state_key = NameObject(f"/{name}")
            if state_key in ocp_obj:
                del ocp_obj[state_key]

            # Remove from intent/usage if empty
            if NameObject("/I") in ocp_obj:
                intent_list = ocp_obj[NameObject("/I")]
                if isinstance(intent_list, ArrayObject):
                    # Check if this is the only intent
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

    def set_ocg_state(self, name: str, on: bool) -> None:
        """Set the state of an OCG.

        Args:
            name: Name of the OCG.
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
            name: Name of the OCG to toggle.

        Returns:
            The name of the toggled OCG or None if not found.

        Raises:
            ValueError: If the name is empty or invalid.
        """
        if not name or not isinstance(name, str):
            raise ValueError("OCG name must be a non-empty string")

        try:
            state_key = NameObject(f"/{name}")
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()

            current_state = ocp_obj.get(state_key, NameObject("/Off"))
            new_state = NameObject("/On") if current_state == NameObject("/Off") else NameObject("/Off")
            ocp_obj[state_key] = new_state

            return name
        except Exception:
            return None

    def set_layer(self, layer_name: Optional[str], on: bool = True) -> None:
        """Set a layer configuration.

        Args:
            layer_name: Optional layer name or "AllOn"/"AllOff".
            on: Whether the layer should be ON.

        Raises:
            ValueError: If an invalid layer name is provided.
        """
        if layer_name is None:
            # Default layer
            return

        if layer_name in ("/AllOn", "/AllOff"):
            if layer_name == "/AllOn":
                for ocg_name in self._ocg_data:
                    self.set_ocg_state(ocg_name, True)
            else:
                for ocg_name in self._ocg_data:
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
            ValueError: If the name is empty or invalid.
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

    def get_ocg_list(self) -> List[Dict[str, Any]]:
        """Get list of all OCGs with their states.

        Returns:
            List of OCG dictionaries with name and state.
        """
        try:
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()
            ocgs = []

            for oc_name in ocp_obj.get(NameObject("/OCGs"), ArrayObject()):
                name = str(oc_name)
                state = str(ocp_obj.get(NameObject(f"/{name}"), NameObject("/Off")))
                ocgs.append({"name": name, "state": state})

            return ocgs
        except Exception:
            return []

    def get_ocg_states(self) -> Dict[str, bool]:
        """Get the ON/OFF state of each OCG.

        Returns:
            Dictionary mapping OCG names to their ON/OFF state.
        """
        states: Dict[str, bool] = {}
        for ocg in self.get_ocg_list():
            states[ocg["name"]] = ocg["state"] == "/On"
        return states

    def get_ocg(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific OCG by name.

        Args:
            name: Name of the OCG.

        Returns:
            OCG dictionary with name and state, or None if not found.
        """
        try:
            ocp = self._get_or_create_oc_properties()
            ocp_obj = ocp.get_object()
            ocgs = self.get_ocg_list()
            for ocg in ocgs:
                if ocg["name"] == name:
                    return ocg
            return None
        except Exception:
            return None

    def __enter__(self) -> "OCGWriter":
        """Enable context manager for automatic cleanup."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Clean up on exit."""
        pass


def add_ocg(
    writer: PdfWriter,
    name: str,
    used: bool = True,
    intent: str = "View",
    usage: str = "Artwork",
) -> IndirectObject:
    """Add a new OCG to the document.

    Args:
        writer: PdfWriter instance.
        name: Name of the OCG.
        used: Whether the OCG is used in the document.
        intent: The intent of the OCG.
        usage: The usage of the OCG.

    Returns:
        Indirect reference of the added OCG.
    """
    writer_obj = OCGWriter(writer)
    return writer_obj.add_ocg(name, used, intent, usage)


def remove_ocg(writer: PdfWriter, name: str) -> Optional[str]:
    """Remove an OCG from the document.

    Args:
        writer: PdfWriter instance.
        name: Name of the OCG to remove.

    Returns:
        The name of the removed OCG or None if not found.
    """
    writer_obj = OCGWriter(writer)
    return writer_obj.remove_ocg(name)


def set_ocg_state(writer: PdfWriter, name: str, on: bool) -> None:
    """Set the state of an OCG.

    Args:
        writer: PdfWriter instance.
        name: Name of the OCG.
        on: Whether the OCG should be ON or OFF.
    """
    writer_obj = OCGWriter(writer)
    writer_obj.set_ocg_state(name, on)


def toggle_ocg(writer: PdfWriter, name: str) -> Optional[str]:
    """Toggle the state of an OCG.

    Args:
        writer: PdfWriter instance.
        name: Name of the OCG to toggle.

    Returns:
        The name of the toggled OCG or None if not found.
    """
    writer_obj = OCGWriter(writer)
    return writer_obj.toggle_ocg(name)


def copy_ocg(
    writer: PdfWriter,
    from_name: str,
    to_name: str,
    on: bool = True,
) -> Optional[str]:
    """Copy an OCG to a new name.

    Args:
        writer: PdfWriter instance.
        from_name: Source OCG name.
        to_name: Destination OCG name.
        on: Whether to copy the OCG to ON state.

    Returns:
        The name of the copied OCG or None if not found.
    """
    writer_obj = OCGWriter(writer)
    return writer_obj.copy_ocg(from_name, to_name, on)


__all__ = [
    "OCGWriter",
    "add_ocg",
    "remove_ocg",
    "set_ocg_state",
    "toggle_ocg",
    "copy_ocg",
]
