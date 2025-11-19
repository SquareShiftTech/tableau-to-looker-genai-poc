from typing import List
import xml.etree.ElementTree as ET

from .models import ParsedDatasource, ParsedWorksheet, ParsedDashboard
from .extractors.connection import ConnectionExtractor
from .extractors.metadata import MetadataExtractor
from .extractors.columns import ColumnExtractor
from .extractors.field_pairing import FieldPairingExtractor
from .extractors.worksheet import WorksheetExtractor
from .extractors.dashboard import DashboardExtractor
from .utils import get_attribute


class TableauParser:
    
    def __init__(self):
        self.connection_extractor = ConnectionExtractor()
        self.metadata_extractor = MetadataExtractor()
        self.column_extractor = ColumnExtractor()
        self.pairing_extractor = FieldPairingExtractor()
        self.worksheet_extractor = WorksheetExtractor()
        self.dashboard_extractor = DashboardExtractor()
    
    def parse_workbook(self, twb_file_path: str) -> List[ParsedDatasource]:
        tree = ET.parse(twb_file_path)
        root = tree.getroot()
        
        datasources = []
        seen_ids = set()  # Track seen datasource IDs to avoid duplicates
        
        # First try to find datasources under <datasources> element (most common structure)
        datasources_elem = root.find('datasources')
        if datasources_elem is not None:
            # Get direct children only (not nested)
            ds_elements = datasources_elem.findall('datasource')
        else:
            # Fallback: search recursively if structure is different
            ds_elements = root.findall('.//datasource')
        
        for ds_elem in ds_elements:
            name = get_attribute(ds_elem, 'name')
            if name and name.startswith('Parameters'):
                continue
            
            # Skip if we've already processed this datasource ID
            if name in seen_ids:
                continue
            seen_ids.add(name)
            
            parsed_ds = self.parse_datasource(ds_elem)
            
            # Only add datasources that have some content
            if (parsed_ds.metadata_records or 
                parsed_ds.column_records or 
                parsed_ds.connection):
                datasources.append(parsed_ds)
        
        return datasources
    
    def parse_datasource(self, datasource_elem: ET.Element) -> ParsedDatasource:
        datasource_id = get_attribute(datasource_elem, 'name')
        caption = get_attribute(datasource_elem, 'caption')
        inline = get_attribute(datasource_elem, 'inline')
        version = get_attribute(datasource_elem, 'version')
        
        connection_elem = datasource_elem.find('connection')
        connection = self.connection_extractor.extract(connection_elem)
        
        metadata_records = self.metadata_extractor.extract(datasource_elem)
        
        column_records = self.column_extractor.extract(datasource_elem)
        
        paired_fields = self.pairing_extractor.extract_pairing(
            metadata_records, 
            column_records
        )
        
        return ParsedDatasource(
            id=datasource_id,
            caption=caption,
            inline=inline,
            version=version,
            connection=connection,
            metadata_records=metadata_records,
            column_records=column_records,
            paired_fields=paired_fields
        )
    
    def parse_worksheets(self, twb_file_path: str) -> List[ParsedWorksheet]:
        tree = ET.parse(twb_file_path)
        root = tree.getroot()
        
        worksheets = []
        
        worksheets_elem = root.find('worksheets')
        if worksheets_elem is None:
            return worksheets
        
        for ws_elem in worksheets_elem.findall('worksheet'):
            parsed_ws = self.parse_worksheet(ws_elem)
            if parsed_ws.name:  # Only add worksheets with names
                worksheets.append(parsed_ws)
        
        return worksheets
    
    def parse_worksheet(self, worksheet_elem: ET.Element) -> ParsedWorksheet:
        worksheet_id = get_attribute(worksheet_elem, 'name')
        worksheet_data = self.worksheet_extractor.extract(worksheet_elem)
        
        return ParsedWorksheet(
            id=worksheet_id,
            name=worksheet_data.get('name', ''),
            layout_options=worksheet_data.get('layout_options', {}),
            table=worksheet_data.get('table', {}),
            simple_id=worksheet_data.get('simple_id')
        )
    
    def parse_dashboards(self, twb_file_path: str) -> List[ParsedDashboard]:
        tree = ET.parse(twb_file_path)
        root = tree.getroot()
        
        dashboards = []
        
        dashboards_elem = root.find('dashboards')
        if dashboards_elem is None:
            return dashboards
        
        for db_elem in dashboards_elem.findall('dashboard'):
            parsed_db = self.parse_dashboard(db_elem)
            if parsed_db.name:  # Only add dashboards with names
                dashboards.append(parsed_db)
        
        return dashboards
    
    def parse_dashboard(self, dashboard_elem: ET.Element) -> ParsedDashboard:
        dashboard_id = get_attribute(dashboard_elem, 'name')
        dashboard_data = self.dashboard_extractor.extract(dashboard_elem)
        
        return ParsedDashboard(
            id=dashboard_id,
            name=dashboard_data.get('name', ''),
            layout_options=dashboard_data.get('layout_options', {}),
            style=dashboard_data.get('style', []),
            size=dashboard_data.get('size', {}),
            datasources=dashboard_data.get('datasources', []),
            datasource_dependencies=dashboard_data.get('datasource_dependencies', []),
            zones=dashboard_data.get('zones', []),
            device_layouts=dashboard_data.get('device_layouts', []),
            simple_id=dashboard_data.get('simple_id')
        )