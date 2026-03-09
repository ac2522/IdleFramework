"""Export game definitions to YAML and XML formats.

YAML: Manual serialization (no PyYAML dependency).
XML: Uses stdlib xml.etree.ElementTree.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom

from idleframework.model.game import GameDefinition


def _yaml_value(value, indent: int = 0) -> str:
    """Convert a Python value to a YAML-formatted string."""
    prefix = "  " * indent

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # Quote strings that contain special YAML characters or look like numbers
        if (
            ":" in value
            or "#" in value
            or value.startswith(("{", "[", "'", '"', "&", "*", "!", "|", ">", "%", "@"))
            or value in ("true", "false", "null", "yes", "no")
            or value == ""
        ):
            escaped = value.replace('"', '\\"')
            return f'"{escaped}"'
        # Try to see if it parses as a number
        try:
            float(value)
            return f'"{value}"'
        except ValueError:
            return value
    if isinstance(value, list):
        if not value:
            return "[]"
        lines = []
        for item in value:
            if isinstance(item, dict):
                dict_lines = _yaml_dict(item, indent + 1)
                # First key on same line as dash
                first_line = dict_lines[0].lstrip()
                lines.append(f"{prefix}- {first_line}")
                for dl in dict_lines[1:]:
                    lines.append(f"{prefix}  {dl.lstrip()}" if dl.strip() else dl)
            else:
                lines.append(f"{prefix}- {_yaml_value(item)}")
        return "\n" + "\n".join(lines)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = _yaml_dict(value, indent)
        return "\n" + "\n".join(lines)

    return str(value)


def _yaml_dict(d: dict, indent: int = 0) -> list[str]:
    """Convert a dict to a list of YAML lines."""
    lines = []
    prefix = "  " * indent

    for key, value in d.items():
        if isinstance(value, dict) and value:
            lines.append(f"{prefix}{key}:")
            lines.extend(_yaml_dict(value, indent + 1))
        elif isinstance(value, list) and value and isinstance(value[0], (dict, list)):
            lines.append(f"{prefix}{key}:")
            formatted = _yaml_value(value, indent)
            # Remove leading newline since we already have the key line
            lines.extend(formatted.lstrip("\n").split("\n"))
        elif isinstance(value, list) and value:
            lines.append(f"{prefix}{key}:")
            for item in value:
                lines.append(f"{prefix}  - {_yaml_value(item)}")
        else:
            val_str = _yaml_value(value)
            if "\n" in val_str:
                lines.append(f"{prefix}{key}:")
                lines.extend(val_str.lstrip("\n").split("\n"))
            else:
                lines.append(f"{prefix}{key}: {val_str}")

    return lines


def to_yaml(game: GameDefinition) -> str:
    """Convert a GameDefinition to YAML string.

    Uses manual serialization to avoid PyYAML dependency.
    """
    data = game.model_dump(mode="json")
    lines = _yaml_dict(data, indent=0)
    return "\n".join(lines) + "\n"


def _dict_to_xml(parent: ET.Element, data, tag: str = "item") -> None:
    """Recursively convert a Python object to XML elements."""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                list_elem = ET.SubElement(parent, str(key))
                for item in value:
                    child = ET.SubElement(list_elem, "item")
                    _dict_to_xml(child, item)
            elif isinstance(value, dict):
                child = ET.SubElement(parent, str(key))
                _dict_to_xml(child, value)
            else:
                child = ET.SubElement(parent, str(key))
                child.text = str(value) if value is not None else ""
    elif isinstance(data, list):
        for item in data:
            child = ET.SubElement(parent, "item")
            _dict_to_xml(child, item)
    else:
        parent.text = str(data) if data is not None else ""


def to_xml(game: GameDefinition) -> str:
    """Convert a GameDefinition to XML string.

    Uses stdlib xml.etree.ElementTree.
    """
    data = game.model_dump(mode="json")
    root = ET.Element("GameDefinition")
    _dict_to_xml(root, data)

    rough = ET.tostring(root, encoding="unicode", xml_declaration=True)
    # Pretty-print
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ")
