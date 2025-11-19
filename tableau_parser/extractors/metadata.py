from typing import List, Dict, Any
import xml.etree.ElementTree as ET

from ..utils import get_text, get_attribute


class MetadataExtractor:
    
    def extract(self, datasource_element: ET.Element) -> List[Dict[str, Any]]:
        metadata_records = []
        
        metadata_section = datasource_element.find('.//metadata-records')
        if metadata_section is None:
            return metadata_records
        
        for record_elem in metadata_section.findall("metadata-record[@class='column']"):
            metadata_records.append(self._extract_record(record_elem))
        
        return metadata_records
    
    def _extract_record(self, record_elem: ET.Element) -> Dict[str, Any]:
        return {
            'class': get_attribute(record_elem, 'class'),
            'remote_name': get_text(record_elem, 'remote-name'),
            'remote_type': get_text(record_elem, 'remote-type'),
            'remote_alias': get_text(record_elem, 'remote-alias'),
            'local_name': get_text(record_elem, 'local-name'),
            'local_type': get_text(record_elem, 'local-type'),
            'parent_name': get_text(record_elem, 'parent-name'),
            'aggregation': get_text(record_elem, 'aggregation'),
            'contains_null': get_text(record_elem, 'contains-null'),
            'collation': get_text(record_elem, 'collation'),
            'ordinal': get_text(record_elem, 'ordinal'),
            'object_id': get_text(record_elem, '_.fcp.ObjectModelEncapsulateLegacy.true...object-id'),
            'family': get_text(record_elem, 'family')
        }