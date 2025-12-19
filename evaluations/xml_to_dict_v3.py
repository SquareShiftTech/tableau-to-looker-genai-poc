"""
Tableau XML to PostgreSQL - Direct Ingestion (No Agent)
Processes ALL XML files in input_files/tableau folder
Usage: python tableau_ingest.py
"""

import json
from pathlib import Path

import xmltodict
from genson import SchemaBuilder
import psycopg2
from psycopg2.extras import Json


# ============================================================================
# CONFIG
# ============================================================================

INPUT_FOLDER = Path("input_files/tableau")

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tableau_migration",
    "user": "postgres",
    "password": "postgres"
}


# ============================================================================
# DATA MODEL
# ============================================================================

DATA_MODEL = """
CREATE TABLE IF NOT EXISTS json_schema (
    id INT PRIMARY KEY DEFAULT 1,
    schema_data JSONB NOT NULL,
    source_files TEXT[],
    updated_at TIMESTAMP DEFAULT NOW(),
    CHECK (id = 1)
);

CREATE TABLE IF NOT EXISTS raw_tableau_files (
    id SERIAL PRIMARY KEY,
    file_name TEXT,
    raw_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_file_id INT REFERENCES raw_tableau_files(id),
    name TEXT,
    version TEXT,
    site TEXT,
    project_path TEXT,
    manifest JSONB
);

CREATE TABLE IF NOT EXISTS datasources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    caption TEXT,
    connection_type TEXT,
    db_name TEXT,
    db_schema TEXT,
    is_extract BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    datasource_id UUID REFERENCES datasources(id) ON DELETE CASCADE,
    caption TEXT,
    internal_name TEXT,
    formula TEXT,
    data_type TEXT,
    role TEXT,
    is_calculated BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    data_type TEXT,
    current_value TEXT,
    range_options JSONB
);

CREATE TABLE IF NOT EXISTS worksheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    datasource_id UUID REFERENCES datasources(id),
    columns_used TEXT[],
    rows_used TEXT[]
);

CREATE TABLE IF NOT EXISTS worksheet_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worksheet_id UUID REFERENCES worksheets(id) ON DELETE CASCADE,
    pane_id TEXT,
    mark_class TEXT,
    element_type TEXT,
    encoding JSONB,
    style JSONB
);

CREATE TABLE IF NOT EXISTS dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    width INTEGER,
    height INTEGER,
    zones JSONB
);

CREATE TABLE IF NOT EXISTS dashboard_components (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID REFERENCES dashboards(id) ON DELETE CASCADE,
    worksheet_id UUID REFERENCES worksheets(id),
    component_type TEXT,
    x_pos INTEGER,
    y_pos INTEGER,
    width INTEGER,
    height INTEGER,
    is_visible BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    action_type TEXT,
    source_object_name TEXT,
    target_object_name TEXT,
    logic_details JSONB
);
"""


# ============================================================================
# INGESTION SQL - Based on actual JSON Schema (with duplicate prevention)
# ============================================================================

INGEST_WORKBOOKS = """
INSERT INTO workbooks (raw_file_id, name, version, site, project_path, manifest)
SELECT 
    r.id,
    COALESCE(
        r.raw_json->'workbook'->'repository-location'->>'@id',
        r.file_name
    ),
    r.raw_json->'workbook'->>'@version',
    r.raw_json->'workbook'->'repository-location'->>'@site',
    r.raw_json->'workbook'->'repository-location'->>'@path',
    r.raw_json->'workbook'->'document-format-change-manifest'
FROM raw_tableau_files r
WHERE NOT EXISTS (SELECT 1 FROM workbooks w WHERE w.raw_file_id = r.id);
"""

INGEST_DATASOURCES = """
INSERT INTO datasources (workbook_id, name, caption, connection_type, db_name, db_schema)
SELECT DISTINCT
    w.id,
    ds->>'@name',
    ds->>'@caption',
    ds->'connection'->>'@class',
    ds->'connection'->'named-connections'->'named-connection'->'connection'->>'@CATALOG',
    ds->'connection'->'named-connections'->'named-connection'->'connection'->>'@schema'
FROM raw_tableau_files r
JOIN workbooks w ON w.raw_file_id = r.id
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN jsonb_typeof(r.raw_json->'workbook'->'datasources'->'datasource') = 'array' 
        THEN r.raw_json->'workbook'->'datasources'->'datasource'
        WHEN r.raw_json->'workbook'->'datasources'->'datasource' IS NOT NULL
        THEN jsonb_build_array(r.raw_json->'workbook'->'datasources'->'datasource')
        ELSE '[]'::jsonb
    END
) AS ds
WHERE r.raw_json->'workbook'->'datasources'->'datasource' IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM datasources d2 
    WHERE d2.workbook_id = w.id AND d2.name = ds->>'@name'
);
"""

INGEST_FIELDS = """
INSERT INTO fields (datasource_id, caption, internal_name, formula, data_type, role, is_calculated)
SELECT DISTINCT
    d.id,
    col->>'@caption',
    col->>'@name',
    col->'calculation'->>'@formula',
    col->>'@datatype',
    col->>'@role',
    (col->'calculation' IS NOT NULL)
FROM raw_tableau_files r
JOIN workbooks w ON w.raw_file_id = r.id
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN jsonb_typeof(r.raw_json->'workbook'->'datasources'->'datasource') = 'array' 
        THEN r.raw_json->'workbook'->'datasources'->'datasource'
        WHEN r.raw_json->'workbook'->'datasources'->'datasource' IS NOT NULL
        THEN jsonb_build_array(r.raw_json->'workbook'->'datasources'->'datasource')
        ELSE '[]'::jsonb
    END
) AS ds
JOIN datasources d ON d.workbook_id = w.id AND d.name = ds->>'@name'
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN jsonb_typeof(ds->'column') = 'array' 
        THEN ds->'column'
        WHEN ds->'column' IS NOT NULL
        THEN jsonb_build_array(ds->'column')
        ELSE '[]'::jsonb
    END
) AS col
WHERE ds->'column' IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM fields f2 
    WHERE f2.datasource_id = d.id AND f2.internal_name = col->>'@name'
);
"""

INGEST_WORKSHEETS = """
INSERT INTO worksheets (workbook_id, name, datasource_id, columns_used, rows_used)
SELECT DISTINCT
    w.id,
    ws->>'@name',
    d.id,
    -- Extract columns from cols string (split by ][)
    CASE 
        WHEN ws->'table'->>'cols' IS NOT NULL AND ws->'table'->>'cols' != ''
        THEN string_to_array(
            regexp_replace(ws->'table'->>'cols', '[\[\]]', '', 'g'),
            ']['
        )
        ELSE NULL
    END,
    -- Extract rows from rows string
    CASE 
        WHEN ws->'table'->>'rows' IS NOT NULL AND ws->'table'->>'rows' != ''
        THEN string_to_array(
            regexp_replace(ws->'table'->>'rows', '[\[\]]', '', 'g'),
            ']['
        )
        ELSE NULL
    END
FROM raw_tableau_files r
JOIN workbooks w ON w.raw_file_id = r.id
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN jsonb_typeof(r.raw_json->'workbook'->'worksheets'->'worksheet') = 'array' 
        THEN r.raw_json->'workbook'->'worksheets'->'worksheet'
        WHEN r.raw_json->'workbook'->'worksheets'->'worksheet' IS NOT NULL
        THEN jsonb_build_array(r.raw_json->'workbook'->'worksheets'->'worksheet')
        ELSE '[]'::jsonb
    END
) AS ws
LEFT JOIN datasources d ON d.workbook_id = w.id 
    AND d.name = ws->'table'->'view'->'datasources'->'datasource'->>'@name'
WHERE r.raw_json->'workbook'->'worksheets'->'worksheet' IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM worksheets ws2 
    WHERE ws2.workbook_id = w.id AND ws2.name = ws->>'@name'
);
"""

INGEST_WORKSHEET_ELEMENTS = """
INSERT INTO worksheet_elements (worksheet_id, pane_id, mark_class, element_type, encoding, style)
SELECT DISTINCT
    wks.id,
    pane->>'@id',
    pane->'mark'->>'@class',
    'pane',
    pane->'encodings',
    pane->'style'
FROM raw_tableau_files r
JOIN workbooks w ON w.raw_file_id = r.id
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN jsonb_typeof(r.raw_json->'workbook'->'worksheets'->'worksheet') = 'array' 
        THEN r.raw_json->'workbook'->'worksheets'->'worksheet'
        WHEN r.raw_json->'workbook'->'worksheets'->'worksheet' IS NOT NULL
        THEN jsonb_build_array(r.raw_json->'workbook'->'worksheets'->'worksheet')
        ELSE '[]'::jsonb
    END
) AS ws
JOIN worksheets wks ON wks.workbook_id = w.id AND wks.name = ws->>'@name'
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN jsonb_typeof(ws->'table'->'panes'->'pane') = 'array' 
        THEN ws->'table'->'panes'->'pane'
        WHEN ws->'table'->'panes'->'pane' IS NOT NULL
        THEN jsonb_build_array(ws->'table'->'panes'->'pane')
        ELSE '[]'::jsonb
    END
) AS pane
WHERE ws->'table'->'panes'->'pane' IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM worksheet_elements we2 
    WHERE we2.worksheet_id = wks.id AND we2.pane_id = pane->>'@id'
);
"""

INGEST_DASHBOARDS = """
INSERT INTO dashboards (workbook_id, name, width, height, zones)
SELECT DISTINCT
    w.id,
    db->>'@name',
    (db->'size'->>'@maxwidth')::INTEGER,
    (db->'size'->>'@maxheight')::INTEGER,
    db->'zones'
FROM raw_tableau_files r
JOIN workbooks w ON w.raw_file_id = r.id
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN jsonb_typeof(r.raw_json->'workbook'->'dashboards'->'dashboard') = 'array' 
        THEN r.raw_json->'workbook'->'dashboards'->'dashboard'
        WHEN r.raw_json->'workbook'->'dashboards'->'dashboard' IS NOT NULL
        THEN jsonb_build_array(r.raw_json->'workbook'->'dashboards'->'dashboard')
        ELSE '[]'::jsonb
    END
) AS db
WHERE r.raw_json->'workbook'->'dashboards'->'dashboard' IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM dashboards d2 
    WHERE d2.workbook_id = w.id AND d2.name = db->>'@name'
);
"""

INGEST_DASHBOARD_COMPONENTS = """
WITH RECURSIVE zone_tree AS (
    -- Base: top-level zones
    SELECT 
        d.id as dashboard_id,
        z->>'@id' as zone_id,
        z->>'@type-v2' as component_type,
        (z->>'@x')::INTEGER as x_pos,
        (z->>'@y')::INTEGER as y_pos,
        (z->>'@w')::INTEGER as width,
        (z->>'@h')::INTEGER as height,
        z->>'@param' as param,
        z->'zone' as child_zones
    FROM dashboards d
    CROSS JOIN LATERAL jsonb_array_elements(
        CASE 
            WHEN jsonb_typeof(d.zones->'zone') = 'array' 
            THEN d.zones->'zone'
            WHEN d.zones->'zone' IS NOT NULL
            THEN jsonb_build_array(d.zones->'zone')
            ELSE '[]'::jsonb
        END
    ) AS z
    WHERE d.zones->'zone' IS NOT NULL
    
    UNION ALL
    
    -- Recursive: nested zones
    SELECT 
        zt.dashboard_id,
        cz->>'@id' as zone_id,
        cz->>'@type-v2' as component_type,
        (cz->>'@x')::INTEGER as x_pos,
        (cz->>'@y')::INTEGER as y_pos,
        (cz->>'@w')::INTEGER as width,
        (cz->>'@h')::INTEGER as height,
        cz->>'@param' as param,
        cz->'zone' as child_zones
    FROM zone_tree zt
    CROSS JOIN LATERAL jsonb_array_elements(
        CASE 
            WHEN jsonb_typeof(zt.child_zones) = 'array' 
            THEN zt.child_zones
            WHEN zt.child_zones IS NOT NULL AND jsonb_typeof(zt.child_zones) = 'object'
            THEN jsonb_build_array(zt.child_zones)
            ELSE '[]'::jsonb
        END
    ) AS cz
    WHERE zt.child_zones IS NOT NULL
)
INSERT INTO dashboard_components (dashboard_id, worksheet_id, component_type, x_pos, y_pos, width, height, is_visible)
SELECT DISTINCT
    zt.dashboard_id,
    ws.id as worksheet_id,
    zt.component_type,
    zt.x_pos,
    zt.y_pos,
    zt.width,
    zt.height,
    TRUE
FROM zone_tree zt
LEFT JOIN worksheets ws ON ws.name = zt.param
WHERE zt.zone_id IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM dashboard_components dc2 
    WHERE dc2.dashboard_id = zt.dashboard_id 
    AND COALESCE(dc2.x_pos, 0) = COALESCE(zt.x_pos, 0)
    AND COALESCE(dc2.y_pos, 0) = COALESCE(zt.y_pos, 0)
);
"""

INGEST_ACTIONS = """
INSERT INTO actions (workbook_id, name, action_type, source_object_name, logic_details)
SELECT DISTINCT
    w.id,
    act->>'@name',
    act->'activation'->>'@type',
    act->'source'->>'@worksheet',
    act
FROM raw_tableau_files r
JOIN workbooks w ON w.raw_file_id = r.id
CROSS JOIN LATERAL jsonb_array_elements(
    CASE 
        WHEN jsonb_typeof(r.raw_json->'workbook'->'actions'->'action') = 'array' 
        THEN r.raw_json->'workbook'->'actions'->'action'
        WHEN r.raw_json->'workbook'->'actions'->'action' IS NOT NULL
        THEN jsonb_build_array(r.raw_json->'workbook'->'actions'->'action')
        ELSE '[]'::jsonb
    END
) AS act
WHERE r.raw_json->'workbook'->'actions'->'action' IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM actions a2 
    WHERE a2.workbook_id = w.id AND a2.name = act->>'@name'
);
"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def xml_to_json(xml_path: Path) -> dict:
    with open(xml_path, 'r', encoding='utf-8') as f:
        return xmltodict.parse(f.read())


def get_xml_files(folder: Path) -> list[Path]:
    return list(folder.glob("*.xml")) + list(folder.glob("*.twb"))


def generate_unified_schema(json_data_list: list[dict]) -> dict:
    builder = SchemaBuilder()
    for json_data in json_data_list:
        builder.add_object(json_data)
    schema = builder.to_schema()
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = "Tableau Workbook Schema"
    return schema


# ============================================================================
# DATABASE CLASS
# ============================================================================

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
    
    def initialize(self):
        with self.conn.cursor() as cur:
            cur.execute(DATA_MODEL)
            self.conn.commit()
        print("✅ Database initialized")
    
    def store_raw_json(self, file_name: str, json_data: dict) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO raw_tableau_files (file_name, raw_json) VALUES (%s, %s) RETURNING id",
                (file_name, Json(json_data))
            )
            file_id = cur.fetchone()[0]
            self.conn.commit()
        return file_id
    
    def store_schema(self, schema: dict, file_names: list[str]):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO json_schema (id, schema_data, source_files, updated_at)
                VALUES (1, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    schema_data = %s,
                    source_files = %s,
                    updated_at = NOW()
            """, (Json(schema), file_names, Json(schema), file_names))
            self.conn.commit()
    
    def run_ingestion(self):
        """Run all ingestion SQL statements."""
        ingestion_queries = [
            ("workbooks", INGEST_WORKBOOKS),
            ("datasources", INGEST_DATASOURCES),
            ("fields", INGEST_FIELDS),
            ("worksheets", INGEST_WORKSHEETS),
            ("worksheet_elements", INGEST_WORKSHEET_ELEMENTS),
            ("dashboards", INGEST_DASHBOARDS),
            ("dashboard_components", INGEST_DASHBOARD_COMPONENTS),
            ("actions", INGEST_ACTIONS),
        ]
        
        for table_name, query in ingestion_queries:
            try:
                with self.conn.cursor() as cur:
                    cur.execute(query)
                    rows = cur.rowcount
                    self.conn.commit()
                print(f"   ✅ {table_name}: {rows} rows inserted")
            except Exception as e:
                self.conn.rollback()
                print(f"   ⚠️  {table_name}: {e}")
    
    def get_counts(self) -> dict:
        """Get row counts for all tables."""
        tables = ["workbooks", "datasources", "fields", "worksheets", "worksheet_elements", "dashboards", "dashboard_components", "actions"]
        counts = {}
        with self.conn.cursor() as cur:
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
        return counts
    
    def truncate_all(self):
        """Truncate all tables for fresh start."""
        with self.conn.cursor() as cur:
            cur.execute("""
                TRUNCATE TABLE actions, dashboard_components, dashboards, 
                worksheet_elements, worksheets, fields, parameters, datasources, 
                workbooks, raw_tableau_files, json_schema 
                CASCADE;
            """)
            self.conn.commit()
        print("   ✅ All tables truncated")
    
    def close(self):
        self.conn.close()


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true', help='Truncate all tables before ingestion')
    args = parser.parse_args()
    
    print("=" * 60)
    print("📁 Tableau Multi-File Ingestion")
    print("=" * 60)
    
    # Get all XML files
    xml_files = get_xml_files(INPUT_FOLDER)
    
    if not xml_files:
        print(f"❌ No XML/TWB files found in {INPUT_FOLDER}")
        return
    
    print(f"\n📄 Found {len(xml_files)} file(s):")
    for f in xml_files:
        print(f"   - {f.name}")
    
    # Step 1: Convert all XML to JSON
    print("\n1️⃣  Converting XML files to JSON...")
    json_data_list = []
    file_names = []
    
    for xml_path in xml_files:
        json_data = xml_to_json(xml_path)
        json_data_list.append(json_data)
        file_names.append(xml_path.name)
    print(f"   ✅ Converted {len(json_data_list)} files")
    
    # Step 2: Generate unified schema
    print("\n2️⃣  Generating unified JSON Schema...")
    json_schema = generate_unified_schema(json_data_list)
    print(f"   ✅ Schema generated")
    
    # Step 3: Initialize database
    print("\n3️⃣  Initializing database...")
    db = Database()
    db.initialize()
    
    # Optional: Fresh start
    if args.fresh:
        print("\n🗑️  Truncating existing data...")
        db.truncate_all()
    
    # Step 4: Store all raw JSONs
    print("\n4️⃣  Storing raw JSON files...")
    for json_data, file_name in zip(json_data_list, file_names):
        file_id = db.store_raw_json(file_name, json_data)
        print(f"   ✅ {file_name} → file_id = {file_id}")
    
    # Step 5: Store schema
    print("\n5️⃣  Storing unified JSON Schema...")
    db.store_schema(json_schema, file_names)
    print(f"   ✅ Schema stored")
    
    # Step 6: Run ingestion
    print("\n6️⃣  Running ingestion (JSONB → Tables)...")
    db.run_ingestion()
    
    # Step 7: Summary
    print("\n" + "=" * 60)
    print("📊 FINAL COUNTS")
    print("=" * 60)
    counts = db.get_counts()
    for table, count in counts.items():
        print(f"   {table}: {count}")
    
    print("\n✅ DONE!")
    db.close()


if __name__ == "__main__":
    main()