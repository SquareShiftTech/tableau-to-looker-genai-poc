"""
Create Tableau Data Model in PostgreSQL
Usage: python create_data_model.py
"""

import psycopg2

# ============================================================================
# CONFIG
# ============================================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tableau_migration",
    "user": "postgres",
    "password": "postgres"
}

# ============================================================================
# DATA MODEL DDL
# ============================================================================

DATA_MODEL = """
-- JSON Schema (single row)
CREATE TABLE IF NOT EXISTS json_schema (
    id INT PRIMARY KEY DEFAULT 1,
    schema_data JSONB NOT NULL,
    source_files TEXT[],
    updated_at TIMESTAMP DEFAULT NOW(),
    CHECK (id = 1)
);

-- Raw Tableau Files
CREATE TABLE IF NOT EXISTS raw_tableau_files (
    id SERIAL PRIMARY KEY,
    file_name TEXT,
    raw_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Workbooks
CREATE TABLE IF NOT EXISTS workbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_file_id INT REFERENCES raw_tableau_files(id),
    name TEXT NOT NULL,
    version TEXT,
    site TEXT,
    project_path TEXT,
    manifest JSONB
);

-- Datasources
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

-- Fields & Calculations
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

-- Parameters
CREATE TABLE IF NOT EXISTS parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    data_type TEXT,
    current_value TEXT,
    range_options JSONB
);

-- Worksheets
CREATE TABLE IF NOT EXISTS worksheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    datasource_id UUID REFERENCES datasources(id),
    columns_used TEXT[],
    rows_used TEXT[],
    viz_definition JSONB
);

-- Dashboards
CREATE TABLE IF NOT EXISTS dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    zones JSONB
);

-- Dashboard Components
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

-- Actions
CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    action_type TEXT,
    source_object_name TEXT,
    target_object_name TEXT,
    logic_details JSONB
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_raw_json ON raw_tableau_files USING GIN (raw_json);
CREATE INDEX IF NOT EXISTS idx_workbooks_raw_file ON workbooks(raw_file_id);
CREATE INDEX IF NOT EXISTS idx_datasources_workbook ON datasources(workbook_id);
CREATE INDEX IF NOT EXISTS idx_fields_datasource ON fields(datasource_id);
CREATE INDEX IF NOT EXISTS idx_worksheets_workbook ON worksheets(workbook_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_workbook ON dashboards(workbook_id);
"""

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("🔧 Creating Tableau Data Model in PostgreSQL")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print()
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("📦 Creating tables...")
        cur.execute(DATA_MODEL)
        conn.commit()
        
        # Verify tables created
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        
        print("\n✅ Tables created:")
        for table in tables:
            print(f"   - {table[0]}")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 50)
        print("✅ DATA MODEL READY")
        print("=" * 50)
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. Database exists: createdb tableau_migration")
        print("  3. Credentials are correct in DB_CONFIG")


if __name__ == "__main__":
    main()