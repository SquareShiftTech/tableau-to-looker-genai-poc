"""
Component Extractor: Utilities for extracting component sections from Tableau JSON

Extracts focused JSON sections for worksheets, dashboards, datasources, and calculations
to enable focused exploration by sub-agents.
"""
from typing import Dict, Any, List, Optional


def build_component_index(file_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a lightweight component index from Tableau JSON
    
    Identifies component types, counts, and locations without deep exploration.
    
    Args:
        file_json: Full Tableau JSON structure
        
    Returns:
        Component index with counts, locations, and names
    """
    index = {
        "worksheets": {
            "count": 0,
            "location": "workbook.worksheets",
            "names": []
        },
        "dashboards": {
            "count": 0,
            "location": "workbook.dashboards",
            "names": []
        },
        "datasources": {
            "count": 0,
            "location": "workbook.datasources",
            "names": []
        },
        "calculations": {
            "count": 0,
            "location": "workbook.datasources.datasource[].column[]",
            "names": []
        }
    }
    
    workbook = file_json.get("workbook", {})
    
    # Worksheets
    worksheets = workbook.get("worksheets", {})
    if worksheets:
        worksheet_list = worksheets.get("worksheet", [])
        if isinstance(worksheet_list, list):
            index["worksheets"]["count"] = len(worksheet_list)
            for ws in worksheet_list:
                name = ws.get("@name") or ws.get("name") or ws.get("@caption")
                if name:
                    index["worksheets"]["names"].append(name)
        elif isinstance(worksheet_list, dict):
            index["worksheets"]["count"] = 1
            name = worksheet_list.get("@name") or worksheet_list.get("name") or worksheet_list.get("@caption")
            if name:
                index["worksheets"]["names"].append(name)
    
    # Dashboards
    dashboards = workbook.get("dashboards", {})
    if dashboards:
        dashboard_list = dashboards.get("dashboard", [])
        if isinstance(dashboard_list, list):
            index["dashboards"]["count"] = len(dashboard_list)
            for db in dashboard_list:
                name = db.get("@name") or db.get("name") or db.get("@caption")
                if name:
                    index["dashboards"]["names"].append(name)
        elif isinstance(dashboard_list, dict):
            index["dashboards"]["count"] = 1
            name = dashboard_list.get("@name") or dashboard_list.get("name") or dashboard_list.get("@caption")
            if name:
                index["dashboards"]["names"].append(name)
    
    # Datasources
    datasources = workbook.get("datasources", {})
    if datasources:
        datasource_list = datasources.get("datasource", [])
        if isinstance(datasource_list, list):
            index["datasources"]["count"] = len(datasource_list)
            for ds in datasource_list:
                name = ds.get("@caption") or ds.get("@name") or ds.get("name")
                if name:
                    index["datasources"]["names"].append(name)
        elif isinstance(datasource_list, dict):
            index["datasources"]["count"] = 1
            name = datasource_list.get("@caption") or datasource_list.get("@name") or datasource_list.get("name")
            if name:
                index["datasources"]["names"].append(name)
    
    # Calculations (found in datasource columns with @formula)
    calculations_count = 0
    calculation_names = []
    if datasources:
        datasource_list = datasources.get("datasource", [])
        if not isinstance(datasource_list, list):
            datasource_list = [datasource_list]
        
        for ds in datasource_list:
            # Check metadata-records for calculated columns
            metadata_records = ds.get("metadata-records", {})
            if metadata_records:
                records = metadata_records.get("metadata-record", [])
                if not isinstance(records, list):
                    records = [records]
                
                for record in records:
                    if record.get("@formula") or record.get("formula"):
                        calculations_count += 1
                        name = record.get("@local-name") or record.get("local-name") or record.get("@name")
                        if name:
                            calculation_names.append(name)
    
    index["calculations"]["count"] = calculations_count
    index["calculations"]["names"] = calculation_names
    
    return index


def extract_worksheets_section(file_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract worksheets section from Tableau JSON
    
    Args:
        file_json: Full Tableau JSON structure
        
    Returns:
        Focused JSON containing only worksheets section
    """
    workbook = file_json.get("workbook", {})
    worksheets = workbook.get("worksheets", {})
    
    return {
        "worksheets": worksheets
    }


def extract_dashboards_section(file_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract dashboards section from Tableau JSON
    
    Args:
        file_json: Full Tableau JSON structure
        
    Returns:
        Focused JSON containing only dashboards section
    """
    workbook = file_json.get("workbook", {})
    dashboards = workbook.get("dashboards", {})
    
    return {
        "dashboards": dashboards
    }


def extract_datasources_section(file_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract datasources section from Tableau JSON
    
    Args:
        file_json: Full Tableau JSON structure
        
    Returns:
        Focused JSON containing only datasources section
    """
    workbook = file_json.get("workbook", {})
    datasources = workbook.get("datasources", {})
    
    return {
        "datasources": datasources
    }


def extract_calculations_section(file_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract calculations section from Tableau JSON
    
    Calculations are found in datasource metadata-records with @formula attribute.
    
    Args:
        file_json: Full Tableau JSON structure
        
    Returns:
        Focused JSON containing calculations extracted from datasources
    """
    workbook = file_json.get("workbook", {})
    datasources = workbook.get("datasources", {})
    
    calculations = []
    
    if datasources:
        datasource_list = datasources.get("datasource", [])
        if not isinstance(datasource_list, list):
            datasource_list = [datasource_list]
        
        for ds in datasource_list:
            ds_name = ds.get("@caption") or ds.get("@name") or "Unknown"
            metadata_records = ds.get("metadata-records", {})
            
            if metadata_records:
                records = metadata_records.get("metadata-record", [])
                if not isinstance(records, list):
                    records = [records]
                
                for record in records:
                    if record.get("@formula") or record.get("formula"):
                        calc = {
                            "name": record.get("@local-name") or record.get("local-name") or record.get("@name"),
                            "formula": record.get("@formula") or record.get("formula"),
                            "datasource": ds_name,
                            "data_type": record.get("@local-type") or record.get("local-type"),
                            "aggregation": record.get("@aggregation") or record.get("aggregation"),
                            "full_record": record
                        }
                        calculations.append(calc)
    
    return {
        "calculations": calculations
    }


def extract_all_component_sections(file_json: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extract all component sections at once
    
    Args:
        file_json: Full Tableau JSON structure
        
    Returns:
        Dictionary with keys: worksheets, dashboards, datasources, calculations
    """
    return {
        "worksheets": extract_worksheets_section(file_json),
        "dashboards": extract_dashboards_section(file_json),
        "datasources": extract_datasources_section(file_json),
        "calculations": extract_calculations_section(file_json)
    }
