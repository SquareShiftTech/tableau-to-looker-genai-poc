"""
File processing tools for converting XML to JSON
"""
import xmltodict
from bs4 import BeautifulSoup
from typing import Dict, Any


def convert_xml_to_json(file_path: str) -> Dict[str, Any]:
    """
    Convert XML file to JSON dictionary
    
    Args:
        file_path: Path to XML file
        
    Returns:
        Dictionary representation of XML
    """
    print(f"📖 Reading XML file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    print(f"✅ Loaded {len(xml_content):,} characters")
    print("🔄 Converting XML to JSON...")
    
    # Parse with xmltodict using recover mode for malformed XML
    try:
        # Use force_list to handle single items consistently
        file_json = xmltodict.parse(
            xml_content,
            process_namespaces=False,  # Ignore namespaces
            force_list=False           # Don't force lists
        )
        print("✅ Conversion complete")
        return file_json
    except Exception as e:
        print(f"⚠️  Standard parsing failed: {e}")
        print("🔄 Trying with lxml recover mode...")
        
        # Try with lxml's recover mode for malformed XML
        from lxml import etree
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        try:
            tree = etree.fromstring(xml_content.encode('utf-8'), parser)
            cleaned_xml = etree.tostring(tree, encoding='utf-8').decode('utf-8')
            file_json = xmltodict.parse(cleaned_xml)
            print("✅ Conversion complete (with recovery)")
            return file_json
        except Exception as e2:
            print(f"❌ Recovery parsing also failed: {e2}")
            raise
