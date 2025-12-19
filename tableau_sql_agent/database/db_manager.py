"""PostgreSQL database manager for raw JSON storage"""
import psycopg2
from psycopg2.extras import Json
from typing import Dict, Any, List, Optional
from config import DB_CONFIG


class DatabaseManager:
    """Handles all PostgreSQL database operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def get_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.config)
    
    def initialize_database(self):
        """Create raw storage table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_tableau_files (
                id SERIAL PRIMARY KEY,
                file_name VARCHAR(255) UNIQUE NOT NULL,
                raw_json JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                file_hash VARCHAR(64)
            );
            
            CREATE INDEX IF NOT EXISTS idx_file_name ON raw_tableau_files(file_name);
            CREATE INDEX IF NOT EXISTS idx_processed ON raw_tableau_files(processed);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized")
    
    def store_raw_json(self, file_name: str, json_data: Dict[str, Any]) -> int:
        """Store raw Tableau JSON in PostgreSQL"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO raw_tableau_files (file_name, raw_json)
            VALUES (%s, %s)
            ON CONFLICT (file_name) 
            DO UPDATE SET 
                raw_json = EXCLUDED.raw_json,
                created_at = CURRENT_TIMESTAMP,
                processed = FALSE
            RETURNING id;
        """, (file_name, Json(json_data)))
        
        file_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return file_id
    
    def get_raw_json(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve raw JSON by file ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT raw_json FROM raw_tableau_files WHERE id = %s;
        """, (file_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result[0] if result else None
    
    def mark_as_processed(self, file_id: int):
        """Mark file as processed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE raw_tableau_files 
            SET processed = TRUE 
            WHERE id = %s;
        """, (file_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
