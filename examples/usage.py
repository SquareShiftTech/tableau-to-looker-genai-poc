import json
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import tableau_parser
sys.path.insert(0, str(Path(__file__).parent.parent))

from tableau_parser import TableauParser
from tableau_parser.extractors.table_inference import TableInferenceExtractor
from workflow.config import CHUNKS_DIR


def parse_datasources(parser, input_file):
    """
    Parse and chunk datasources from TWB file.
    Returns: datasource_chunk_registry dict mapping ds_id -> list of chunk files
    """
    print("=" * 80)
    print("PARSING DATASOURCES")
    print("=" * 80)
    
    datasources = parser.parse_workbook(input_file)
    seen_ids = {}
    datasource_chunk_registry = {}  # ds_id -> [chunk_file_0, chunk_file_1, ...]
    
    for ds in datasources:
        print(f"\nProcessing: {ds.caption}")
        print(f"  ID: {ds.id}")
        print(f"  Metadata records: {len(ds.metadata_records)}")
        print(f"  Column records: {len(ds.column_records)}")
        print(f"  Paired fields: {len(ds.paired_fields)}")
        
        # Handle duplicate IDs
        ds_id = ds.id or 'unknown'
        if ds_id in seen_ids:
            seen_ids[ds_id] += 1
            suffix = f"_{seen_ids[ds_id]}"
        else:
            seen_ids[ds_id] = 0
            suffix = ""
        
        # Chunk immediately
        chunk_size = 100
        paired_fields = ds.paired_fields
        
        # Save connection chunk
        connection_chunk = {
            'datasource_id': ds.id,
            'datasource_caption': ds.caption,
            'connection': ds.connection.__dict__ if hasattr(ds.connection, '__dict__') else ds.connection
        }
        
        conn_file = CHUNKS_DIR / f"chunk_{ds_id}{suffix}_connection.json"
        with open(conn_file, 'w') as f:
            json.dump(connection_chunk, f, indent=2)
        print(f"  Created: {conn_file.name}")
        
        # Initialize registry for this datasource
        if ds_id not in datasource_chunk_registry:
            datasource_chunk_registry[ds_id] = []
        
        # Save field chunks
        # First pass: create all chunks without inference (we need all fields for cross-chunk inference)
        chunks_data = []
        chunk_count = 0
        for i in range(0, len(paired_fields), chunk_size):
            chunk_fields = paired_fields[i:i + chunk_size]
            
            field_chunk = {
                'datasource_id': ds.id,
                'datasource_caption': ds.caption,
                'chunk_id': chunk_count,
                'field_count': len(chunk_fields),
                'fields': chunk_fields
            }
            
            chunks_data.append(field_chunk)
            chunk_count += 1
        
        # Second pass: enrich each chunk with table inference using ALL fields from ALL chunks
        # This allows inference to resolve references across chunks
        all_datasource_fields = []
        for chunk in chunks_data:
            all_datasource_fields.extend(chunk['fields'])
        
        for chunk in chunks_data:
            # Enrich chunk with table inference, passing all fields from all chunks
            enrich_chunk_with_table_inference(chunk, all_datasource_fields)
            
            chunk_file = CHUNKS_DIR / f"chunk_{ds_id}{suffix}_fields_{chunk['chunk_id']}.json"
            with open(chunk_file, 'w') as f:
                json.dump(chunk, f, indent=2)
            
            # Track chunk file in registry (use filename only for compatibility)
            datasource_chunk_registry[ds_id].append(chunk_file.name)
            
            print(f"  Created: {chunk_file.name} ({chunk['field_count']} fields)")
        
        print(f"  Total: 1 connection chunk + {chunk_count} field chunks")
    
    return datasource_chunk_registry


def enrich_chunk_with_table_inference(field_chunk, all_datasource_fields=None):
    """
    Enrich field chunk with inferred table information for calculated fields.
    Uses all datasource fields to resolve cross-chunk field references.
    
    Args:
        field_chunk: The chunk to enrich
        all_datasource_fields: All fields from all chunks of the same datasource (enables cross-chunk inference)
    """
    all_fields = field_chunk.get('fields', [])
    if not all_fields:
        return
    
    inference = TableInferenceExtractor()
    
    # Use all datasource fields for inference (allows cross-chunk references)
    # If not provided, fall back to current chunk only
    inference_fields = all_datasource_fields if all_datasource_fields else all_fields
    
    for field in all_fields:
        # Skip if field already has metadata (base field)
        if field.get('metadata') is not None:
            continue
        
        # Case 1: Calculated field (has calculation formula)
        if field.get('column', {}).get('calculation'):
            # Use all datasource fields for inference (allows cross-chunk references)
            result = inference.infer_tables_for_calculated_field(field, inference_fields)
            
            # Add inferred table information
            field['inferred_table'] = result['primary_table']
            field['ref_tables'] = result['ref_tables']
            field['referenced_fields'] = result['referenced_fields']
            field['inferred'] = True
        
        # Case 2: Field without metadata and without calculation (orphaned field)
        # These fields have no formula to analyze and no metadata - cannot infer table
        # They will remain with inferred_table: null and be handled by DSL generation prompt


def analyze_worksheet_dependencies(worksheet, datasource_chunk_registry):
    """
    Analyze which datasource chunks a worksheet needs.
    Returns: set of chunk file names
    """
    required_chunks = set()
    
    # Get datasources used by worksheet
    # worksheet is a ParsedWorksheet object with .table attribute
    table = worksheet.table
    view = table.get('view', {})
    datasources = view.get('datasources', [])
    
    # For each datasource, get all its chunks (conservative approach)
    for ds in datasources:
        ds_id = ds.get('name')
        if ds_id and ds_id in datasource_chunk_registry:
            # Add all chunks for this datasource
            required_chunks.update(datasource_chunk_registry[ds_id])
    
    # If we have dependencies, we could be more precise, but for now
    # we'll use all chunks from referenced datasources
    return required_chunks


def group_worksheets_by_chunks(worksheets, datasource_chunk_registry, batch_size=8):
    """
    Group worksheets by their required datasource chunk sets.
    Returns: list of groups, each group is a list of worksheets with same chunk requirements
    """
    # Analyze each worksheet's dependencies
    worksheet_chunk_map = {}  # frozenset(chunks) -> [worksheets]
    
    for ws in worksheets:
        required_chunks = analyze_worksheet_dependencies(ws, datasource_chunk_registry)
        chunk_key = frozenset(sorted(required_chunks))
        
        if chunk_key not in worksheet_chunk_map:
            worksheet_chunk_map[chunk_key] = []
        worksheet_chunk_map[chunk_key].append(ws)
    
    # Batch worksheets within each group
    batched_groups = []
    for chunk_set, ws_list in worksheet_chunk_map.items():
        # Split into batches
        for i in range(0, len(ws_list), batch_size):
            batch = ws_list[i:i + batch_size]
            batched_groups.append({
                'chunk_set': chunk_set,
                'worksheets': batch
            })
    
    return batched_groups


def parse_worksheets(parser, input_file, datasource_chunk_registry):
    """Parse and chunk worksheets from TWB file with batching."""
    print("\n" + "=" * 80)
    print("PARSING WORKSHEETS")
    print("=" * 80)
    
    worksheets = parser.parse_worksheets(input_file)
    
    print(f"\nFound {len(worksheets)} worksheet(s)")
    
    # Group and batch worksheets
    batched_groups = group_worksheets_by_chunks(worksheets, datasource_chunk_registry, batch_size=8)
    
    print(f"\nGrouped into {len(batched_groups)} worksheet chunk(s)")
    
    # Process each batch
    for batch_idx, batch_group in enumerate(batched_groups):
        chunk_set = batch_group['chunk_set']
        ws_list = batch_group['worksheets']
        
        print(f"\nProcessing Worksheet Batch {batch_idx + 1}: {len(ws_list)} worksheet(s)")
        print(f"  Required datasource chunks: {len(chunk_set)}")
        
        # Build worksheet data for batch
        worksheets_data = []
        for ws in ws_list:
            table = ws.table
            view = table.get('view', {})
            datasources = view.get('datasources', [])
            dependencies = view.get('datasource_dependencies', [])
            filters = view.get('filters', [])
            panes = table.get('panes', [])
            rows = table.get('rows') or ''
            cols = table.get('cols') or ''
            
            worksheet_data = {
                'worksheet_id': ws.id,
                'worksheet_name': ws.name,
                'datasources': datasources,
                'datasource_dependencies': dependencies,
                'table': {
                    'rows': rows or '',
                    'cols': cols or '',
                    'panes': panes,
                    'view': view,
                    'style': table.get('style', [])
                },
                'layout_options': ws.layout_options,
                'simple_id': ws.simple_id
            }
            worksheets_data.append(worksheet_data)
        
        # Create batched worksheet chunk
        worksheet_chunk = {
            'workbook_id': Path(input_file).stem,
            'worksheet_chunk_id': batch_idx,
            'worksheet_count': len(worksheets_data),
            'datasource_chunk_references': sorted(list(chunk_set)),
            'worksheets': worksheets_data
        }
        
        chunk_file = CHUNKS_DIR / f"chunk_worksheet_batch_{batch_idx}.json"
        with open(chunk_file, 'w') as f:
            json.dump(worksheet_chunk, f, indent=2)
        
        print(f"  Created: {chunk_file.name} ({len(worksheets_data)} worksheets, {len(chunk_set)} datasource chunks)")


def analyze_dashboard_dependencies(dashboard, datasource_chunk_registry, worksheet_chunk_registry):
    """
    Analyze which datasource and worksheet chunks a dashboard needs.
    Returns: (datasource_chunks, worksheet_chunks)
    """
    required_ds_chunks = set()
    required_ws_chunks = set()
    
    # Get datasources used by dashboard
    for ds in dashboard.datasources:
        ds_id = ds.get('name')
        if ds_id and ds_id in datasource_chunk_registry:
            required_ds_chunks.update(datasource_chunk_registry[ds_id])
    
    # Get worksheets referenced in zones
    worksheet_names = set()
    for zone in dashboard.zones:
        zone_name = zone.get('name')
        if zone_name:
            worksheet_names.add(zone_name)
    
    # Map worksheet names to worksheet chunks
    # For now, we'll need to track worksheet chunks as they're created
    # This is a simplified version - in practice, you'd maintain a registry
    # of worksheet_name -> worksheet_chunk_file
    
    return required_ds_chunks, required_ws_chunks


def parse_dashboards(parser, input_file, datasource_chunk_registry, batch_size=5):
    """Parse and chunk dashboards from TWB file with batching."""
    print("\n" + "=" * 80)
    print("PARSING DASHBOARDS")
    print("=" * 80)
    
    dashboards = parser.parse_dashboards(input_file)
    
    print(f"\nFound {len(dashboards)} dashboard(s)")
    
    # Batch dashboards
    dashboard_batches = []
    for i in range(0, len(dashboards), batch_size):
        batch = dashboards[i:i + batch_size]
        dashboard_batches.append(batch)
    
    print(f"\nGrouped into {len(dashboard_batches)} dashboard chunk(s)")
    
    # Process each batch
    for batch_idx, db_batch in enumerate(dashboard_batches):
        print(f"\nProcessing Dashboard Batch {batch_idx + 1}: {len(db_batch)} dashboard(s)")
        
        # Build dashboard data for batch
        dashboards_data = []
        all_ds_chunks = set()
        
        for db in db_batch:
            # Count worksheet instances in zones
            worksheet_zones = [z for z in db.zones if z.get('name')]
            
            # Analyze dependencies
            ds_chunks, _ = analyze_dashboard_dependencies(db, datasource_chunk_registry, {})
            all_ds_chunks.update(ds_chunks)
            
            dashboard_data = {
                'dashboard_id': db.id,
                'dashboard_name': db.name,
                'datasources': db.datasources,
                'datasource_dependencies': db.datasource_dependencies,
                'zones': db.zones,
                'filters': _extract_dashboard_filters(db.zones),
                'size': db.size,
                'layout_options': db.layout_options,
                'style': db.style,
                'device_layouts': db.device_layouts,
                'simple_id': db.simple_id,
                'worksheet_instances': len(worksheet_zones)
            }
            dashboards_data.append(dashboard_data)
        
        # Create batched dashboard chunk
        dashboard_chunk = {
            'workbook_id': Path(input_file).stem,
            'dashboard_chunk_id': batch_idx,
            'dashboard_count': len(dashboards_data),
            'datasource_chunk_references': sorted(list(all_ds_chunks)),
            'dashboards': dashboards_data
        }
        
        chunk_file = CHUNKS_DIR / f"chunk_dashboard_batch_{batch_idx}.json"
        with open(chunk_file, 'w') as f:
            json.dump(dashboard_chunk, f, indent=2)
        
        print(f"  Created: {chunk_file.name} ({len(dashboards_data)} dashboards, {len(all_ds_chunks)} datasource chunks)")


def _extract_dashboard_filters(zones):
    """Extract filter zones from dashboard zones."""
    filters = []
    for zone in zones:
        if zone.get('type') == 'filter' or zone.get('type-v2') == 'filter':
            filters.append({
                'zone_id': zone.get('id'),
                'name': zone.get('name'),
                'param': zone.get('param'),
                'mode': zone.get('mode'),
                'position': {
                    'x': zone.get('x'),
                    'y': zone.get('y'),
                    'w': zone.get('w'),
                    'h': zone.get('h')
                }
            })
    return filters


def main():
    parser = TableauParser()
    
    # Update this path to your TWB file
    input_file = 'C:\\squareshift\\data_validation\\Metrics_Homepage_NP_Pop_up_MODIFIED.twb'
    # Alternative: use a file from twb_files directory
    # input_file = str(Path(__file__).parent.parent / 'twb_files' / 'Sales Summary_final.twb')
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        print("Please update the input_file path in main()")
        return
    
    # Parse datasources and get chunk registry
    datasource_chunk_registry = parse_datasources(parser, input_file)
    
    # Parse worksheets (with batching and chunk references)
    parse_worksheets(parser, input_file, datasource_chunk_registry)
    
    # Parse dashboards (with batching)
    parse_dashboards(parser, input_file, datasource_chunk_registry)
    
    print("\n" + "=" * 80)
    print("PARSING COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()