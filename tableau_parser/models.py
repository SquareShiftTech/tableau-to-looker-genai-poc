from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ParsedDatasource:
    id: str
    caption: str
    inline: str
    version: str
    connection: Dict[str, Any]
    metadata_records: List[Dict[str, Any]]
    column_records: List[Dict[str, Any]]
    paired_fields: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'caption': self.caption,
            'inline': self.inline,
            'version': self.version,
            'connection': self.connection,
            'metadata_records': self.metadata_records,
            'column_records': self.column_records,
            'paired_fields': self.paired_fields
        }


@dataclass
class ParsedWorksheet:
    id: Optional[str]
    name: str
    layout_options: Dict[str, Any]
    table: Dict[str, Any]
    simple_id: Optional[Dict[str, str]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'layout_options': self.layout_options,
            'table': self.table,
            'simple_id': self.simple_id
        }


@dataclass
class ParsedDashboard:
    id: Optional[str]
    name: str
    layout_options: Dict[str, Any]
    style: List[Dict[str, Any]]
    size: Dict[str, Any]
    datasources: List[Dict[str, str]]
    datasource_dependencies: List[Dict[str, Any]]
    zones: List[Dict[str, Any]]
    device_layouts: List[Dict[str, Any]]
    simple_id: Optional[Dict[str, str]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'layout_options': self.layout_options,
            'style': self.style,
            'size': self.size,
            'datasources': self.datasources,
            'datasource_dependencies': self.datasource_dependencies,
            'zones': self.zones,
            'device_layouts': self.device_layouts,
            'simple_id': self.simple_id
        }