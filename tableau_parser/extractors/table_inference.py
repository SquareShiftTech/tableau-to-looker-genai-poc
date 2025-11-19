from typing import List, Dict, Any, Set, Optional
import re


class TableInferenceExtractor:
    """
    Extracts table information for calculated fields by analyzing formula dependencies.
    Recursively resolves chained calculations to find base tables.
    """
    
    def extract_field_references(self, formula: str) -> List[str]:
        """
        Extract all field references from Tableau formula.
        Pattern: [FieldName] or [Field Name]
        Skips parameters and function names.
        """
        if not formula:
            return []
        
        # Match [FieldName] or [Field Name] or [Field (copy)_123]
        pattern = r'\[([^\]]+)\]'
        matches = re.findall(pattern, formula)
        
        field_refs = []
        for match in matches:
            # Skip if it's a parameter reference
            if match.startswith("Parameters."):
                continue
            
            # Skip date parts that might appear in brackets (though rare)
            if match.lower() in ["year", "month", "quarter", "day", "week"]:
                continue
            
            # Add brackets back to match field_name format
            field_refs.append(f"[{match}]")
        
        return field_refs
    
    def build_field_registry(self, fields: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Build lookup map: field_name → {has_metadata, parent_name, is_calculated, formula, field_obj}
        """
        registry = {}
        
        for field in fields:
            field_name = field.get('field_name', '')
            if not field_name:
                continue
            
            has_metadata = field.get('metadata') is not None
            parent_name = None
            
            if has_metadata:
                parent_name = field['metadata'].get('parent_name')
            
            # Check if it's a calculated field
            is_calculated = (
                not has_metadata and 
                field.get('column', {}).get('calculation') is not None
            )
            
            formula = None
            if is_calculated:
                formula = field.get('column', {}).get('calculation', {}).get('formula')
            
            registry[field_name] = {
                'has_metadata': has_metadata,
                'parent_name': parent_name,
                'is_calculated': is_calculated,
                'formula': formula,
                'field_obj': field
            }
        
        return registry
    
    def clean_table_name(self, parent_name: Optional[str]) -> Optional[str]:
        """
        Clean table name from metadata.parent_name format.
        [FCT_METRICHOMEPAGEALL_FAC_DAY] → fct_metrichomepageall_fac_day
        """
        if not parent_name:
            return None
        
        # Remove brackets
        cleaned = parent_name.strip('[]')
        # Lowercase
        cleaned = cleaned.lower()
        
        return cleaned
    
    def resolve_tables_recursive(
        self, 
        field_name: str, 
        field_registry: Dict[str, Dict[str, Any]], 
        visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        Recursively resolve all base tables for a field.
        Returns: set of cleaned table names
        """
        if visited is None:
            visited = set()
        
        # Prevent infinite loops
        if field_name in visited:
            return set()
        
        visited.add(field_name)
        
        # Get field from registry
        field_info = field_registry.get(field_name)
        if not field_info:
            return set()  # Field not found
        
        # BASE CASE: Field has metadata (base field)
        if field_info['has_metadata']:
            parent_name = field_info['parent_name']
            if parent_name:
                clean_table = self.clean_table_name(parent_name)
                if clean_table:
                    return {clean_table}
            return set()
        
        # RECURSIVE CASE: It's a calculated field
        if field_info['is_calculated']:
            formula = field_info['formula']
            if not formula:
                return set()
            
            field_refs = self.extract_field_references(formula)
            
            all_tables = set()
            for ref in field_refs:
                # Recursively resolve this reference
                # Use visited.copy() to allow same field in different branches
                ref_tables = self.resolve_tables_recursive(
                    ref, 
                    field_registry, 
                    visited.copy()
                )
                all_tables.update(ref_tables)
            
            return all_tables
        
        return set()
    
    def determine_primary_table(self, tables: Set[str]) -> Optional[str]:
        """
        Determine primary table from set of tables.
        Priority:
        1. Fact table (patterns: fct_*, fact_*, *_fact, transactions, orders, sales)
        2. Most common table (if we had frequency data)
        3. First table alphabetically (fallback)
        """
        if not tables:
            return None
        
        if len(tables) == 1:
            return list(tables)[0]
        
        # Strategy: Look for fact table patterns
        fact_patterns = ["fct_", "fact_", "_fact", "transactions", "orders", "sales"]
        dim_patterns = ["dim_", "_dim", "lookup", "reference"]
        
        # First, try to find fact table
        for table in tables:
            table_lower = table.lower()
            if any(pattern in table_lower for pattern in fact_patterns):
                return table
        
        # If no fact table found, return first table (alphabetically sorted for consistency)
        return sorted(tables)[0]
    
    def infer_tables_for_calculated_field(
        self, 
        field: Dict[str, Any], 
        all_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main function that orchestrates table inference for a calculated field.
        Returns: {
            'primary_table': str or None,
            'ref_tables': str or None (comma-separated if multiple),
            'referenced_fields': List[str]
        }
        """
        # Extract formula
        calculation = field.get('column', {}).get('calculation', {})
        formula = calculation.get('formula', '')
        
        if not formula:
            return {
                'primary_table': None,
                'ref_tables': None,
                'referenced_fields': []
            }
        
        # Extract field references
        referenced_fields = self.extract_field_references(formula)
        
        if not referenced_fields:
            return {
                'primary_table': None,
                'ref_tables': None,
                'referenced_fields': referenced_fields
            }
        
        # Build field registry
        field_registry = self.build_field_registry(all_fields)
        
        # Resolve all base tables (recursive)
        all_tables = set()
        visited = set()
        
        for ref in referenced_fields:
            ref_tables = self.resolve_tables_recursive(
                ref, 
                field_registry, 
                visited.copy()
            )
            all_tables.update(ref_tables)
        
        # Determine primary table
        primary_table = self.determine_primary_table(all_tables)
        
        # Build ref_tables string (comma-separated if multiple)
        ref_tables_str = None
        if len(all_tables) > 1:
            ref_tables_str = ",".join(sorted(all_tables))
        elif len(all_tables) == 1:
            ref_tables_str = list(all_tables)[0]
        
        return {
            'primary_table': primary_table,
            'ref_tables': ref_tables_str,
            'referenced_fields': referenced_fields
        }

