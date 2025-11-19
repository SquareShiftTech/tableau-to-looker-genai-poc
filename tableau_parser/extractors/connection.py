from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET

from ..utils import get_attribute, get_text, get_all_attributes


class ConnectionExtractor:
    
    def extract(self, connection_element: ET.Element) -> Dict[str, Any]:
        if connection_element is None:
            return {}
        
        return {
            'class': get_attribute(connection_element, 'class'),
            'named_connections': self._extract_named_connections(connection_element),
            'relation': self._extract_relation(connection_element),
            'cols': self._extract_cols_mapping(connection_element),
            'refresh': self._extract_refresh(connection_element)
        }
    
    def _extract_named_connections(self, connection_element: ET.Element) -> List[Dict]:
        named_conns = []
        
        nc_section = connection_element.find('named-connections')
        if nc_section is None:
            return named_conns
        
        for nc_elem in nc_section.findall('named-connection'):
            named_conn = {
                'name': get_attribute(nc_elem, 'name'),
                'caption': get_attribute(nc_elem, 'caption')
            }
            
            conn_detail = nc_elem.find('connection')
            if conn_detail is not None:
                named_conn['details'] = get_all_attributes(conn_detail)
            
            named_conns.append(named_conn)
        
        return named_conns
    
    def _extract_relation(self, connection_element: ET.Element) -> Optional[Dict]:
        relation_elem = (
            connection_element.find('./_.fcp.ObjectModelEncapsulateLegacy.false...relation') or
            connection_element.find('./_.fcp.ObjectModelEncapsulateLegacy.true...relation') or
            connection_element.find('relation')
        )
        
        if relation_elem is None:
            return None
        
        relation_type = get_attribute(relation_elem, 'type')
        
        if relation_type == 'join':
            return self._extract_join_relation(relation_elem)
        elif relation_type == 'table':
            return self._extract_table_relation(relation_elem)
        elif relation_type == 'text':
            return self._extract_custom_sql_relation(relation_elem)
        else:
            return {
                'type': relation_type,
                'attributes': get_all_attributes(relation_elem)
            }
    
    def _extract_join_relation(self, relation_elem: ET.Element) -> Dict:
        return {
            'type': 'join',
            'join': get_attribute(relation_elem, 'join'),
            'clauses': self._extract_join_clauses(relation_elem),
            'tables': self._extract_relation_tables(relation_elem)
        }
    
    def _extract_join_clauses(self, relation_elem: ET.Element) -> List[Dict]:
        clauses = []
        
        for clause_elem in relation_elem.findall('clause'):
            clause = {
                'type': get_attribute(clause_elem, 'type'),
                'expressions': []
            }
            
            expr_elem = clause_elem.find('expression')
            if expr_elem is not None:
                clause['operator'] = get_attribute(expr_elem, 'op')
                
                for sub_expr in expr_elem.findall('expression'):
                    clause['expressions'].append({
                        'op': get_attribute(sub_expr, 'op')
                    })
            
            clauses.append(clause)
        
        return clauses
    
    def _extract_relation_tables(self, relation_elem: ET.Element) -> List[Dict]:
        tables = []
        
        for table_elem in relation_elem.findall('relation'):
            tables.append(self._extract_table_relation(table_elem))
        
        return tables
    
    def _extract_table_relation(self, relation_elem: ET.Element) -> Dict:
        return {
            'type': 'table',
            'name': get_attribute(relation_elem, 'name'),
            'table': get_attribute(relation_elem, 'table'),
            'connection': get_attribute(relation_elem, 'connection'),
            'table_type': get_attribute(relation_elem, 'type')
        }
    
    def _extract_custom_sql_relation(self, relation_elem: ET.Element) -> Dict:
        return {
            'type': 'custom_sql',
            'name': get_attribute(relation_elem, 'name'),
            'connection': get_attribute(relation_elem, 'connection'),
            'sql': relation_elem.text
        }
    
    def _extract_cols_mapping(self, connection_element: ET.Element) -> Dict[str, str]:
        mapping = {}
        
        cols_elem = connection_element.find('cols')
        if cols_elem is None:
            return mapping
        
        for map_elem in cols_elem.findall('map'):
            key = get_attribute(map_elem, 'key')
            value = get_attribute(map_elem, 'value')
            if key and value:
                mapping[key] = value
        
        return mapping
    
    def _extract_refresh(self, connection_element: ET.Element) -> Dict:
        refresh_elem = connection_element.find('refresh')
        if refresh_elem is None:
            return {}
        
        return get_all_attributes(refresh_elem)