from typing import Optional, Dict
import xml.etree.ElementTree as ET


def get_text(element: ET.Element, tag: str) -> Optional[str]:
    child = element.find(tag)
    if child is not None and child.text:
        return child.text
    return None


def get_attribute(element: ET.Element, attr: str) -> Optional[str]:
    return element.get(attr)


def get_all_attributes(element: ET.Element) -> Dict[str, str]:
    return dict(element.attrib)