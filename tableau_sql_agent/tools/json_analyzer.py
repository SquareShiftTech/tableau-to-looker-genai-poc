"""JSON structure analysis tools"""
from typing import Dict, Any, List, Union
from langchain.tools import tool
import json


@tool
def analyze_json_hierarchy(json_data: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    Analyze JSON structure depth-based for Tableau XML converted to JSON.
    Level 1-2: Parents (no samples)
    Level 3+: Children (with 10 samples)
    
    Handles XML attributes (keys starting with @) and XML text content (#text).
    
    Args:
        json_data: The JSON data to analyze (dict or JSON string)
    
    Returns:
        Hierarchical structure with depth levels and samples
    """
    
    # Handle string input (from JSONB or serialized data)
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {str(e)}")
    
    # Ensure it's a dict
    if not isinstance(json_data, dict):
        raise ValueError(f"Expected dict or JSON string, got {type(json_data)}")
    
    hierarchy = []
    
    def is_leaf_value(value):
        """Check if value is a leaf (primitive or None)"""
        return isinstance(value, (str, int, float, bool)) or value is None
    
    def extract_sample_fields(obj):
        """Extract sample fields from object, excluding nested structures"""
        sample = {}
        for k, v in obj.items():
            if is_leaf_value(v):
                sample[k] = v
            elif isinstance(v, dict) and '#text' in v:
                # Handle XML text content wrapped in dict
                sample[k] = v['#text']
        return sample if sample else None
    
    def get_children_names(obj):
        """Get names of children (nested dicts/lists)"""
        children = []
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                # Skip if it's just a text wrapper
                if isinstance(value, dict) and set(value.keys()) == {'#text'}:
                    continue
                children.append(key)
        return children
    
    def traverse(obj, path="root", level=0, parent_name=None):
        """Recursively traverse JSON structure"""
        
        if isinstance(obj, dict):
            entity_name = path.split('.')[-1].replace('[]', '')
            
            # Get children names
            children = get_children_names(obj)
            
            # Build entity info
            entity_info = {
                "level": level,
                "entity_name": entity_name,
                "entity_type": "parent" if level <= 2 else "child",
                "json_path": path,
                "parent_entity": parent_name,
                "children": children,
                "component_count": 1,
                "sample_data": None
            }
            
            # Add sample data for children (level 3+)
            if level >= 3:
                sample = extract_sample_fields(obj)
                if sample:
                    entity_info["sample_data"] = [sample]
            
            hierarchy.append(entity_info)
            
            # Recurse into nested structures
            for key, value in obj.items():
                if isinstance(value, dict):
                    # Skip text-only wrappers
                    if set(value.keys()) == {'#text'}:
                        continue
                    traverse(value, f"{path}.{key}", level + 1, entity_name)
                    
                elif isinstance(value, list) and value:
                    # Check first item to determine array type
                    first_item = value[0]
                    
                    if isinstance(first_item, dict):
                        # Array of objects
                        array_entity = {
                            "level": level + 1,
                            "entity_name": key,
                            "entity_type": "parent" if level + 1 <= 2 else "child",
                            "json_path": f"{path}.{key}[]",
                            "parent_entity": entity_name,
                            "children": get_children_names(first_item),
                            "component_count": len(value),
                            "sample_data": None
                        }
                        
                        # Add samples for children (level 3+)
                        if level + 1 >= 3:
                            samples = []
                            for item in value[:10]:  # Max 10 samples
                                if isinstance(item, dict):
                                    sample = extract_sample_fields(item)
                                    if sample:
                                        samples.append(sample)
                            
                            if samples:
                                array_entity["sample_data"] = samples
                        
                        hierarchy.append(array_entity)
                        
                        # Analyze first item for deeper nesting
                        traverse(first_item, f"{path}.{key}[]", level + 1, entity_name)
                    
                    elif is_leaf_value(first_item):
                        # Array of primitives - treat as a field, not separate entity
                        # Already captured in sample_data via extract_sample_fields
                        pass
    
    traverse(json_data)
    
    return {
        "max_depth": max([e["level"] for e in hierarchy]) if hierarchy else 0,
        "total_entities": len(hierarchy),
        "hierarchy": hierarchy
    }


@tool
def get_entity_samples(json_data: Dict[str, Any], json_path: str, count: int = 10) -> List[Dict[str, Any]]:
    """
    Extract sample data from a specific JSON path.
    
    Args:
        json_data: The full JSON data
        json_path: Path to extract from (e.g., "root.dashboards[]")
        count: Number of samples to extract
    
    Returns:
        List of sample records
    """
    
    def navigate_path(obj, path_parts):
        if not path_parts or path_parts[0] == "root":
            path_parts = path_parts[1:] if len(path_parts) > 1 else []
        
        if not path_parts:
            return obj
        
        current = path_parts[0].replace('[]', '')
        remaining = path_parts[1:]
        
        if isinstance(obj, dict) and current in obj:
            value = obj[current]
            if isinstance(value, list):
                return value[:count]
            return navigate_path(value, remaining)
        
        return None
    
    parts = json_path.split('.')
    return navigate_path(json_data, parts) or []