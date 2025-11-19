from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET

from ..utils import get_attribute, get_text, get_all_attributes


class DashboardExtractor:
    
    def extract(self, dashboard_element: ET.Element) -> Dict[str, Any]:
        if dashboard_element is None:
            return {}
        
        dashboard = {
            'name': get_attribute(dashboard_element, 'name'),
            'layout_options': self._extract_layout_options(dashboard_element),
            'style': self._extract_style(dashboard_element),
            'size': self._extract_size(dashboard_element),
            'datasources': self._extract_datasources(dashboard_element),
            'datasource_dependencies': self._extract_datasource_dependencies(dashboard_element),
            'zones': self._extract_zones(dashboard_element),
            'device_layouts': self._extract_device_layouts(dashboard_element),
            'simple_id': self._extract_simple_id(dashboard_element)
        }
        
        return dashboard
    
    def _extract_layout_options(self, dashboard_element: ET.Element) -> Dict[str, Any]:
        layout_elem = dashboard_element.find('layout-options')
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
    
    def _extract_style(self, dashboard_element: ET.Element) -> List[Dict[str, Any]]:
        style_rules = []
        
        style_elem = dashboard_element.find('style')
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
    
    def _extract_size(self, dashboard_element: ET.Element) -> Dict[str, Any]:
        size_elem = dashboard_element.find('size')
        if size_elem is None:
            return {}
        
        return get_all_attributes(size_elem)
    
    def _extract_datasources(self, dashboard_element: ET.Element) -> List[Dict[str, str]]:
        datasources = []
        
        datasources_elem = dashboard_element.find('datasources')
        if datasources_elem is None:
            return datasources
        
        for ds_elem in datasources_elem.findall('datasource'):
            datasources.append({
                'name': get_attribute(ds_elem, 'name'),
                'caption': get_attribute(ds_elem, 'caption')
            })
        
        return datasources
    
    def _extract_datasource_dependencies(self, dashboard_element: ET.Element) -> List[Dict[str, Any]]:
        dependencies = []
        
        for ds_dep_elem in dashboard_element.findall('datasource-dependencies'):
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
    
    def _extract_zones(self, dashboard_element: ET.Element) -> List[Dict[str, Any]]:
        zones = []
        
        zones_elem = dashboard_element.find('zones')
        if zones_elem is None:
            return zones
        
        for zone_elem in zones_elem.findall('zone'):
            zone = {
                'id': get_attribute(zone_elem, 'id'),
                'name': get_attribute(zone_elem, 'name'),
                'type': get_attribute(zone_elem, 'type-v2'),
                'x': get_attribute(zone_elem, 'x'),
                'y': get_attribute(zone_elem, 'y'),
                'w': get_attribute(zone_elem, 'w'),
                'h': get_attribute(zone_elem, 'h'),
                'param': get_attribute(zone_elem, 'param'),
                'mode': get_attribute(zone_elem, 'mode'),
                'is_fixed': get_attribute(zone_elem, 'is-fixed'),
                'fixed_size': get_attribute(zone_elem, 'fixed-size')
            }
            
            # Extract zone style
            zone_style_elem = zone_elem.find('zone-style')
            if zone_style_elem is not None:
                zone['style'] = self._extract_zone_style(zone_style_elem)
            
            # Extract layout cache
            layout_cache_elem = zone_elem.find('layout-cache')
            if layout_cache_elem is not None:
                zone['layout_cache'] = get_all_attributes(layout_cache_elem)
            
            # Extract nested zones (children)
            nested_zones = zone_elem.findall('zone')
            if nested_zones:
                zone['children'] = []
                for nested_zone_elem in nested_zones:
                    nested_zone = self._extract_zone_recursive(nested_zone_elem)
                    if nested_zone:
                        zone['children'].append(nested_zone)
            
            zones.append(zone)
        
        return zones
    
    def _extract_zone_recursive(self, zone_elem: ET.Element) -> Dict[str, Any]:
        zone = {
            'id': get_attribute(zone_elem, 'id'),
            'name': get_attribute(zone_elem, 'name'),
            'type': get_attribute(zone_elem, 'type-v2'),
            'x': get_attribute(zone_elem, 'x'),
            'y': get_attribute(zone_elem, 'y'),
            'w': get_attribute(zone_elem, 'w'),
            'h': get_attribute(zone_elem, 'h'),
            'param': get_attribute(zone_elem, 'param'),
            'mode': get_attribute(zone_elem, 'mode'),
            'is_fixed': get_attribute(zone_elem, 'is-fixed'),
            'fixed_size': get_attribute(zone_elem, 'fixed-size')
        }
        
        # Extract nested zones
        nested_zones = zone_elem.findall('zone')
        if nested_zones:
            zone['children'] = []
            for nested_zone_elem in nested_zones:
                nested_zone = self._extract_zone_recursive(nested_zone_elem)
                if nested_zone:
                    zone['children'].append(nested_zone)
        
        return zone
    
    def _extract_zone_style(self, zone_style_elem: ET.Element) -> List[Dict[str, Any]]:
        formats = []
        
        for format_elem in zone_style_elem.findall('format'):
            formats.append(get_all_attributes(format_elem))
        
        return formats
    
    def _extract_device_layouts(self, dashboard_element: ET.Element) -> List[Dict[str, Any]]:
        device_layouts = []
        
        device_layouts_elem = dashboard_element.find('devicelayouts')
        if device_layouts_elem is None:
            return device_layouts
        
        for layout_elem in device_layouts_elem.findall('devicelayout'):
            layout = {
                'name': get_attribute(layout_elem, 'name'),
                'auto_generated': get_attribute(layout_elem, 'auto-generated'),
                'layout_options': self._extract_layout_options(layout_elem),
                'size': self._extract_size(layout_elem),
                'zones': self._extract_zones(layout_elem)
            }
            device_layouts.append(layout)
        
        return device_layouts
    
    def _extract_simple_id(self, dashboard_element: ET.Element) -> Optional[Dict[str, str]]:
        simple_id_elem = dashboard_element.find('simple-id')
        if simple_id_elem is None:
            return None
        
        return {
            'uuid': get_attribute(simple_id_elem, 'uuid')
        }

