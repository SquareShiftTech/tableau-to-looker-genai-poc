from typing import List, Dict, Any
import xml.etree.ElementTree as ET

from ..utils import get_attribute, get_all_attributes


class ColumnExtractor:
    
    def extract(self, datasource_element: ET.Element) -> List[Dict[str, Any]]:
        columns = []
        
        for column_elem in datasource_element.findall('.//column'):
            columns.append(self._extract_column(column_elem))
        
        return columns
    
    def _extract_column(self, column_elem: ET.Element) -> Dict[str, Any]:
        column = get_all_attributes(column_elem)
        
        calc_elem = column_elem.find('calculation')
        if calc_elem is not None:
            column['calculation'] = get_all_attributes(calc_elem)
        
        aliases_elem = column_elem.find('aliases')
        if aliases_elem is not None:
            column['aliases'] = self._extract_aliases(aliases_elem)
        
        range_elem = column_elem.find('range')
        if range_elem is not None:
            column['range'] = get_all_attributes(range_elem)
        
        members = self._extract_members(column_elem)
        if members:
            column['members'] = members
        
        table_calc_elem = column_elem.find('.//table-calc')
        if table_calc_elem is not None:
            column['table_calc'] = get_all_attributes(table_calc_elem)
        
        formatted_aliases = self._extract_formatted_aliases(column_elem)
        if formatted_aliases:
            column['formatted_aliases'] = formatted_aliases
        
        return column
    
    def _extract_aliases(self, aliases_elem: ET.Element) -> Dict[str, str]:
        aliases = {}
        
        for alias_elem in aliases_elem.findall('alias'):
            key = get_attribute(alias_elem, 'key')
            value = get_attribute(alias_elem, 'value')
            if key and value:
                aliases[key] = value
        
        return aliases
    
    def _extract_members(self, column_elem: ET.Element) -> List[Dict[str, str]]:
        members = []
        
        for member_elem in column_elem.findall('.//member'):
            members.append(get_all_attributes(member_elem))
        
        return members
    
    def _extract_formatted_aliases(self, column_elem: ET.Element) -> List[Dict[str, Any]]:
        formatted_aliases = []
        
        for fa_elem in column_elem.findall('.//formatted-alias'):
            formatted_aliases.append({
                'attributes': get_all_attributes(fa_elem),
                'text': fa_elem.text
            })
        
        return formatted_aliases