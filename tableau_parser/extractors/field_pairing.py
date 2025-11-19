from typing import List, Dict, Any


class FieldPairingExtractor:
    
    def extract_pairing(
        self, 
        metadata_records: List[Dict[str, Any]], 
        column_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        metadata_map = self._build_metadata_map(metadata_records)
        column_map = self._build_column_map(column_records)
        
        all_field_names = set(metadata_map.keys()) | set(column_map.keys())
        
        paired_fields = []
        for field_name in all_field_names:
            paired_field = {
                'field_name': field_name,
                'metadata': metadata_map.get(field_name),
                'column': column_map.get(field_name)
            }
            paired_fields.append(paired_field)
        
        return paired_fields
    
    def _build_metadata_map(self, metadata_records: List[Dict[str, Any]]) -> Dict[str, Dict]:
        metadata_map = {}
        for record in metadata_records:
            local_name = record.get('local_name')
            if local_name:
                metadata_map[local_name] = record
        return metadata_map
    
    def _build_column_map(self, column_records: List[Dict[str, Any]]) -> Dict[str, Dict]:
        column_map = {}
        for record in column_records:
            name = record.get('name')
            if name:
                column_map[name] = record
        return column_map