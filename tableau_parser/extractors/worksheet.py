from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET

from ..utils import get_attribute, get_text, get_all_attributes


class WorksheetExtractor:
    
    def extract(self, worksheet_element: ET.Element) -> Dict[str, Any]:
        if worksheet_element is None:
            return {}
        
        worksheet = {
            'name': get_attribute(worksheet_element, 'name'),
            'layout_options': self._extract_layout_options(worksheet_element),
            'table': self._extract_table(worksheet_element),
            'simple_id': self._extract_simple_id(worksheet_element)
        }
        
        return worksheet
    
    def _extract_layout_options(self, worksheet_element: ET.Element) -> Dict[str, Any]:
        layout_elem = worksheet_element.find('layout-options')
        if layout_elem is None:
            return {}
        
        layout = {}
        
        title_elem = layout_elem.find('title')
        if title_elem is not None:
            layout['title'] = self._extract_formatted_text(title_elem)
        
        return layout
    
    def _extract_formatted_text(self, element: ET.Element) -> Optional[str]:
        formatted_text_elem = element.find('formatted-text')
        if formatted_text_elem is None:
            return None
        
        run_elem = formatted_text_elem.find('run')
        if run_elem is not None and run_elem.text:
            return run_elem.text
        
        return formatted_text_elem.text
    
    def _extract_table(self, worksheet_element: ET.Element) -> Dict[str, Any]:
        table_elem = worksheet_element.find('table')
        if table_elem is None:
            return {}
        
        table = {
            'view': self._extract_view(table_elem),
            'style': self._extract_style(table_elem),
            'panes': self._extract_panes(table_elem),
            'rows': get_text(table_elem, 'rows'),
            'cols': get_text(table_elem, 'cols')
        }
        
        return table
    
    def _extract_view(self, table_elem: ET.Element) -> Dict[str, Any]:
        view_elem = table_elem.find('view')
        if view_elem is None:
            return {}
        
        view = {
            'datasources': self._extract_view_datasources(view_elem),
            'datasource_dependencies': self._extract_datasource_dependencies(view_elem),
            'filters': self._extract_filters(view_elem),
            'slices': self._extract_slices(view_elem),
            'aggregation': get_attribute(view_elem.find('aggregation'), 'value') if view_elem.find('aggregation') is not None else None
        }
        
        return view
    
    def _extract_view_datasources(self, view_elem: ET.Element) -> List[Dict[str, str]]:
        datasources = []
        
        datasources_elem = view_elem.find('datasources')
        if datasources_elem is None:
            return datasources
        
        for ds_elem in datasources_elem.findall('datasource'):
            datasources.append({
                'name': get_attribute(ds_elem, 'name'),
                'caption': get_attribute(ds_elem, 'caption')
            })
        
        return datasources
    
    def _extract_datasource_dependencies(self, view_elem: ET.Element) -> List[Dict[str, Any]]:
        dependencies = []
        
        for ds_dep_elem in view_elem.findall('datasource-dependencies'):
            datasource_id = get_attribute(ds_dep_elem, 'datasource')
            
            for col_elem in ds_dep_elem.findall('column'):
                dep = {
                    'datasource': datasource_id,
                    'name': get_attribute(col_elem, 'name'),
                    'caption': get_attribute(col_elem, 'caption'),
                    'datatype': get_attribute(col_elem, 'datatype'),
                    'role': get_attribute(col_elem, 'role'),
                    'type': get_attribute(col_elem, 'type')
                }
                
                calc_elem = col_elem.find('calculation')
                if calc_elem is not None:
                    dep['calculation'] = get_all_attributes(calc_elem)
                
                dependencies.append(dep)
            
            for col_inst_elem in ds_dep_elem.findall('column-instance'):
                dep = {
                    'datasource': datasource_id,
                    'name': get_attribute(col_inst_elem, 'name'),
                    'column': get_attribute(col_inst_elem, 'column'),
                    'derivation': get_attribute(col_inst_elem, 'derivation'),
                    'pivot': get_attribute(col_inst_elem, 'pivot'),
                    'type': get_attribute(col_inst_elem, 'type')
                }
                dependencies.append(dep)
        
        return dependencies
    
    def _extract_filters(self, view_elem: ET.Element) -> List[Dict[str, Any]]:
        filters = []
        
        for filter_elem in view_elem.findall('filter'):
            filter_data = {
                'class': get_attribute(filter_elem, 'class'),
                'column': get_attribute(filter_elem, 'column'),
                'groupfilter': self._extract_groupfilter(filter_elem)
            }
            filters.append(filter_data)
        
        return filters
    
    def _extract_groupfilter(self, filter_elem: ET.Element) -> Optional[Dict[str, Any]]:
        groupfilter_elem = filter_elem.find('groupfilter')
        if groupfilter_elem is None:
            return None
        
        groupfilter = {
            'function': get_attribute(groupfilter_elem, 'function'),
            'members': []
        }
        
        for member_elem in groupfilter_elem.findall('groupfilter'):
            member = {
                'function': get_attribute(member_elem, 'function'),
                'level': get_attribute(member_elem, 'level'),
                'member': get_attribute(member_elem, 'member')
            }
            groupfilter['members'].append(member)
        
        return groupfilter
    
    def _extract_slices(self, view_elem: ET.Element) -> List[str]:
        slices = []
        
        slices_elem = view_elem.find('slices')
        if slices_elem is None:
            return slices
        
        for col_elem in slices_elem.findall('column'):
            if col_elem.text:
                slices.append(col_elem.text)
        
        return slices
    
    def _extract_style(self, table_elem: ET.Element) -> List[Dict[str, Any]]:
        style_rules = []
        
        style_elem = table_elem.find('style')
        if style_elem is None:
            return style_rules
        
        for rule_elem in style_elem.findall('style-rule'):
            rule = {
                'element': get_attribute(rule_elem, 'element'),
                'formats': []
            }
            
            for format_elem in rule_elem.findall('format'):
                format_data = get_all_attributes(format_elem)
                
                # Extract formatted-text if present
                formatted_text_elem = format_elem.find('formatted-text')
                if formatted_text_elem is not None:
                    format_data['formatted_text'] = self._extract_formatted_text(format_elem)
                
                rule['formats'].append(format_data)
            
            style_rules.append(rule)
        
        return style_rules
    
    def _extract_panes(self, table_elem: ET.Element) -> List[Dict[str, Any]]:
        panes = []
        
        panes_elem = table_elem.find('panes')
        if panes_elem is None:
            return panes
        
        for pane_elem in panes_elem.findall('pane'):
            pane = {
                'id': get_attribute(pane_elem, 'id'),
                'view': self._extract_pane_view(pane_elem),
                'mark': self._extract_mark(pane_elem),
                'encodings': self._extract_encodings(pane_elem),
                'style': self._extract_pane_style(pane_elem)
            }
            panes.append(pane)
        
        return panes
    
    def _extract_pane_view(self, pane_elem: ET.Element) -> Dict[str, Any]:
        view_elem = pane_elem.find('view')
        if view_elem is None:
            return {}
        
        breakdown_elem = view_elem.find('breakdown')
        return {
            'breakdown': get_attribute(breakdown_elem, 'value') if breakdown_elem is not None else None
        }
    
    def _extract_mark(self, pane_elem: ET.Element) -> Dict[str, Any]:
        mark_elem = pane_elem.find('mark')
        if mark_elem is None:
            return {}
        
        mark = {
            'class': get_attribute(mark_elem, 'class')
        }
        
        mark_sizing_elem = pane_elem.find('mark-sizing')
        if mark_sizing_elem is not None:
            mark['sizing'] = get_all_attributes(mark_sizing_elem)
        
        return mark
    
    def _extract_encodings(self, pane_elem: ET.Element) -> List[Dict[str, str]]:
        encodings = []
        
        encodings_elem = pane_elem.find('encodings')
        if encodings_elem is None:
            return encodings
        
        for encoding_elem in encodings_elem:
            encoding = {
                'type': encoding_elem.tag,
                'column': get_attribute(encoding_elem, 'column')
            }
            encodings.append(encoding)
        
        return encodings
    
    def _extract_pane_style(self, pane_elem: ET.Element) -> List[Dict[str, Any]]:
        style_rules = []
        
        style_elem = pane_elem.find('style')
        if style_elem is None:
            return style_rules
        
        for rule_elem in style_elem.findall('style-rule'):
            rule = {
                'element': get_attribute(rule_elem, 'element'),
                'formats': []
            }
            
            for format_elem in rule_elem.findall('format'):
                rule['formats'].append(get_all_attributes(format_elem))
            
            style_rules.append(rule)
        
        return style_rules
    
    def _extract_simple_id(self, worksheet_element: ET.Element) -> Optional[Dict[str, str]]:
        simple_id_elem = worksheet_element.find('simple-id')
        if simple_id_elem is None:
            return None
        
        return {
            'uuid': get_attribute(simple_id_elem, 'uuid')
        }

