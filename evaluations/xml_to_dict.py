
"""
XML to JSON Converter with Schema Generator
Usage: python xml_to_json_schema.py <path_to_xml_file>
"""

import json
import sys
from pathlib import Path
from typing import Any, Union

import xmltodict
from genson import SchemaBuilder


# ============================================================================
# STEP 1: XML TO JSON
# ============================================================================

def xml_to_json(xml_path: str) -> dict:
    """Convert XML file to JSON/dict."""
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    return xmltodict.parse(xml_content)


# ============================================================================
# STEP 2: GENERATE JSON SCHEMA
# ============================================================================

def generate_schema(json_data: Union[dict, list[dict]]) -> dict:
    """
    Generate JSON schema from JSON data using genson library.
    Can handle single JSON object or multiple JSON objects to build unified schema.
    
    Args:
        json_data: Single dict or list of dicts to generate schema from.
                   If list, merges all objects into one comprehensive schema.
    
    Returns:
        Complete JSON schema dictionary
    """
    builder = SchemaBuilder()
    
    # Handle both single dict and list of dicts
    if isinstance(json_data, dict):
        builder.add_object(json_data)
    elif isinstance(json_data, list):
        if not json_data:
            raise ValueError("Cannot generate schema from empty list")
        # Add all objects to builder - genson will merge them
        for obj in json_data:
            if not isinstance(obj, dict):
                raise ValueError(f"All items in list must be dicts, got {type(obj)}")
            builder.add_object(obj)
    else:
        raise ValueError(f"json_data must be dict or list[dict], got {type(json_data)}")
    
    # Get the generated schema
    schema = builder.to_schema()
    
    # Add metadata
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = "Tableau Workbook Schema"
    schema["description"] = "Auto-generated schema from Tableau XML" + (
        f" (merged from {len(json_data)} files)" if isinstance(json_data, list) else ""
    )
    
    return schema


# ============================================================================
# STEP 3: ANALYZE STRUCTURE (BONUS)
# ============================================================================

def analyze_structure(data: Any, path: str = "root", depth: int = 0) -> list:
    """Analyze JSON structure with depth info."""
    nodes = []
    
    if isinstance(data, dict):
        nodes.append({
            "path": path,
            "depth": depth,
            "type": "object",
            "keys": list(data.keys())
        })
        for key, value in data.items():
            nodes.extend(analyze_structure(value, f"{path}.{key}", depth + 1))
    
    elif isinstance(data, list):
        nodes.append({
            "path": path,
            "depth": depth,
            "type": "array",
            "length": len(data)
        })
        if data and isinstance(data[0], (dict, list)):
            nodes.extend(analyze_structure(data[0], f"{path}[]", depth + 1))
    
    return nodes


# ============================================================================
# HELPER: Process Multiple Files
# ============================================================================

def generate_schema_from_multiple_files(xml_paths: list[str]) -> dict:
    """
    Generate a unified JSON schema from multiple XML files.
    
    Args:
        xml_paths: List of paths to XML files
    
    Returns:
        Unified JSON schema covering all files
    """
    json_data_list = []
    
    for xml_path in xml_paths:
        if not Path(xml_path).exists():
            print(f"⚠️  Warning: File not found: {xml_path}, skipping...")
            continue
        
        print(f"📄 Processing: {xml_path}")
        json_data = xml_to_json(xml_path)
        json_data_list.append(json_data)
    
    if not json_data_list:
        raise ValueError("No valid XML files found to process")
    
    print(f"\n🔄 Generating unified schema from {len(json_data_list)} files...")
    return generate_schema(json_data_list)


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Get input files from command line arguments or use default
    if len(sys.argv) > 1:
        xml_paths = sys.argv[1:]
    else:
        # Default: use all XML files in input_files/tableau directory
        tableau_dir = Path("input_files/tableau")
        if tableau_dir.exists():
            xml_paths = list(tableau_dir.glob("*.xml"))
            if not xml_paths:
                print(f"❌ No XML files found in {tableau_dir}")
                sys.exit(1)
            xml_paths = [str(p) for p in xml_paths]
        else:
            # Fallback to single file
            xml_paths = ["input_files/tableau/sales_summary_final.xml"]
    
    # Validate all files exist
    valid_paths = []
    for xml_path in xml_paths:
        if not Path(xml_path).exists():
            print(f"⚠️  Warning: File not found: {xml_path}, skipping...")
            continue
        valid_paths.append(xml_path)
    
    if not valid_paths:
        print("❌ No valid XML files found to process")
        sys.exit(1)
    
    print(f"📄 Processing {len(valid_paths)} XML file(s):")
    for path in valid_paths:
        print(f"   - {path}")
    
    # Step 1: Convert XML to JSON
    print("\n1️⃣ Converting XML to JSON...")
    json_data_list = []
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    for xml_path in valid_paths:
        print(f"   Processing: {Path(xml_path).name}")
        json_data = xml_to_json(xml_path)
        json_data_list.append(json_data)
        
        # Save individual JSON file
        json_file = output_dir / f"{Path(xml_path).stem}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"      ✅ Saved: {json_file}")
    
    # Step 2: Generate Unified Schema
    print(f"\n2️⃣ Generating unified JSON Schema from {len(json_data_list)} file(s)...")
    if len(json_data_list) == 1:
        schema = generate_schema(json_data_list[0])
        schema_file = output_dir / f"{Path(valid_paths[0]).stem}_schema.json"
    else:
        schema = generate_schema(json_data_list)
        # Create unified schema filename
        base_names = "_".join([Path(p).stem for p in valid_paths[:3]])  # First 3 names
        if len(valid_paths) > 3:
            base_names += f"_and_{len(valid_paths) - 3}_more"
        schema_file = output_dir / f"unified_schema_{base_names}.json"
    
    with open(schema_file, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Saved: {schema_file}")
    
    # Step 3: Analyze Structure (from first file or combined)
    print("\n3️⃣ Analyzing Structure...")
    structure = analyze_structure(json_data_list[0])
    
    max_depth = max(n["depth"] for n in structure)
    print(f"   Max depth: {max_depth}")
    print(f"   Total nodes: {len(structure)}")
    
    # Show top-level keys from first file
    if json_data_list and "workbook" in json_data_list[0]:
        wb = json_data_list[0]["workbook"]
        print(f"\n📊 Workbook Structure (from first file):")
        print(f"   Version: {wb.get('@version', 'N/A')}")
        print(f"   Top-level keys: {list(wb.keys())[:10]}")
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ DONE!")
    print(f"   Processed: {len(valid_paths)} file(s)")
    print(f"   JSON files: {len(valid_paths)} individual file(s)")
    print(f"   Schema: {schema_file}")
    print("=" * 50)


if __name__ == "__main__":
    main()