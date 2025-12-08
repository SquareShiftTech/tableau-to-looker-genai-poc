"""File structure analyzers for different BI platforms."""
import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from utils.logger import logger


class TableauStructureAnalyzer:
    """Analyzer for Tableau .twb/.twbx files (XML-based)."""
    
    def extract_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Extract Tableau XML structure without loading full content.
        Uses streaming parser - memory efficient.
        
        Args:
            file_path: Path to the Tableau XML file
            
        Returns:
            Dict with structure metadata:
            - file_size_bytes: int
            - file_type: str
            - platform: str
            - root_elements: List[str]
            - element_counts: Dict[str, int]
            - element_hierarchy: Dict[str, List[str]]
            - sample_content: str (first 20KB)
            - estimated_sections: List[Dict[str, Any]]
        """
        file_size = os.path.getsize(file_path)
        
        structure = {
            "file_size_bytes": file_size,
            "file_type": "xml",
            "platform": "tableau",
            "root_elements": [],
            "element_counts": {},
            "element_hierarchy": {},
            "sample_content": "",
            "estimated_sections": []
        }
        
        # Read first 20KB for structure sample
        with open(file_path, 'rb') as f:
            sample_bytes = f.read(20000)
            try:
                structure["sample_content"] = sample_bytes.decode('utf-8', errors='ignore')
            except:
                structure["sample_content"] = sample_bytes.decode('latin-1', errors='ignore')
        
        # Use iterparse to extract structure (streaming - memory efficient)
        element_stack: List[str] = []
        
        try:
            for event, elem in ET.iterparse(file_path, events=('start', 'end')):
                if event == 'start':
                    element_stack.append(elem.tag)
                    
                    # Track element types and counts
                    tag = elem.tag
                    if tag not in structure["element_counts"]:
                        structure["element_counts"][tag] = 0
                        structure["element_hierarchy"][tag] = []
                    
                    structure["element_counts"][tag] += 1
                    
                    # Track hierarchy (parent-child relationships)
                    if len(element_stack) > 1:
                        parent = element_stack[-2] if len(element_stack) > 1 else None
                        if parent and parent not in structure["element_hierarchy"][tag]:
                            structure["element_hierarchy"][tag].append(parent)
                    
                    # Track root elements
                    if len(element_stack) == 1:
                        if tag not in structure["root_elements"]:
                            structure["root_elements"].append(tag)
                
                if event == 'end':
                    if element_stack:
                        element_stack.pop()
                    elem.clear()  # Free memory immediately
                    
        except ET.ParseError as e:
            logger.warning(f"XML parse error (may be incomplete): {e}")
            # Continue with what we have
        except Exception as e:
            logger.error(f"Error parsing XML structure: {e}")
            # Return partial structure
        
        # Estimate section sizes (approximate)
        structure["estimated_sections"] = self._estimate_section_sizes(
            file_path, 
            structure["element_counts"]
        )
        
        return structure
    
    def _estimate_section_sizes(
        self, 
        file_path: str, 
        element_counts: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """
        Estimate sizes of major sections for splitting strategy.
        Uses sampling to estimate without full file read.
        
        Args:
            file_path: Path to the file
            element_counts: Dictionary of element counts
            
        Returns:
            List of estimated section information
        """
        sections = []
        
        # Key Tableau elements to track
        key_elements = ['datasources', 'worksheets', 'dashboards', 'parameters']
        
        # Sample file to find approximate positions
        # This is a simplified estimation - can be enhanced
        file_size = os.path.getsize(file_path)
        
        for elem in key_elements:
            if elem in element_counts:
                # Rough estimate: assume elements are evenly distributed
                # More sophisticated: actually find byte positions
                estimated_size = file_size // len(key_elements) if key_elements else file_size
                sections.append({
                    "name": elem,
                    "count": element_counts[elem],
                    "estimated_size_bytes": estimated_size,
                    "priority": "high" if elem in ['datasources', 'worksheets'] else "medium"
                })
        
        return sections

