"""BigQuery service for writing analysis results."""
import json
from typing import List, Dict, Any, Optional
from utils.logger import logger
from config.settings import get_settings

try:
    from google.cloud import bigquery
    from google.cloud.exceptions import NotFound
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False
    logger.warning("google-cloud-bigquery not available, BigQuery operations will be logged only")


class BigQueryService:
    """Service for BigQuery operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.project_id = self.settings.gcp_project_id
        self.dataset = self.settings.bigquery_dataset
        
        if BIGQUERY_AVAILABLE and self.project_id:
            try:
                self.client = bigquery.Client(project=self.project_id)
                logger.info(f"BigQueryService initialized for project: {self.project_id}, dataset: {self.dataset}")
            except Exception as e:
                logger.error(f"Failed to initialize BigQuery client: {e}")
                self.client = None
        else:
            self.client = None
            if not BIGQUERY_AVAILABLE:
                logger.warning("BigQuery client not available - install google-cloud-bigquery")
            if not self.project_id:
                logger.warning("GCP project ID not configured - BigQuery operations will be logged only")
    
    def _get_table_schema(self, table_name: str) -> List[bigquery.SchemaField]:
        """Get BigQuery table schema for a given table."""
        schemas = {
            'dashboards': [
                bigquery.SchemaField('workbook_name', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('features', 'JSON', mode='NULLABLE'),
                bigquery.SchemaField('complexity', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('dependencies', 'JSON', mode='NULLABLE'),
                bigquery.SchemaField('job_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('created_at', 'TIMESTAMP', mode='REQUIRED'),
            ],
            'worksheets': [
                bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('features', 'JSON', mode='NULLABLE'),
                bigquery.SchemaField('complexity', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('dependencies', 'JSON', mode='NULLABLE'),
                bigquery.SchemaField('job_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('created_at', 'TIMESTAMP', mode='REQUIRED'),
            ],
            'datasources': [
                bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('type', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('complexity', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('job_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('created_at', 'TIMESTAMP', mode='REQUIRED'),
            ],
            'calculation_fields': [
                bigquery.SchemaField('datasource_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('field_name', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('formula', 'STRING', mode='NULLABLE'),
                bigquery.SchemaField('complexity', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('job_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('created_at', 'TIMESTAMP', mode='REQUIRED'),
            ],
        }
        
        return schemas.get(table_name, [])
    
    def _prepare_rows(self, table_name: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare rows for BigQuery insertion - convert JSON fields to strings."""
        prepared_rows = []
        
        for row in rows:
            prepared_row = row.copy()
            
            # Convert JSON fields to JSON strings
            if 'features' in prepared_row and isinstance(prepared_row['features'], dict):
                prepared_row['features'] = json.dumps(prepared_row['features'])
            
            if 'dependencies' in prepared_row and isinstance(prepared_row['dependencies'], dict):
                prepared_row['dependencies'] = json.dumps(prepared_row['dependencies'])
            
            # Ensure created_at is in correct format for TIMESTAMP
            if 'created_at' in prepared_row:
                created_at = prepared_row['created_at']
                # If it's already a string in ISO format, BigQuery will parse it
                # If it's a datetime object, convert to ISO string
                if hasattr(created_at, 'isoformat'):
                    prepared_row['created_at'] = created_at.isoformat()
            
            prepared_rows.append(prepared_row)
        
        return prepared_rows
    
    def create_tables_if_not_exists(self) -> None:
        """Create BigQuery tables if they don't exist."""
        if not self.client or not self.project_id:
            logger.warning("BigQuery client not available, skipping table creation")
            return
        
        table_names = ['dashboards', 'worksheets', 'datasources', 'calculation_fields']
        
        for table_name in table_names:
            try:
                table_id = f"{self.project_id}.{self.dataset}.{table_name}"
                table = bigquery.Table(table_id, schema=self._get_table_schema(table_name))
                table = self.client.create_table(table, exists_ok=True)
                logger.info(f"Table {table_id} exists or was created")
            except NotFound:
                # Dataset doesn't exist, try to create it
                try:
                    dataset_id = f"{self.project_id}.{self.dataset}"
                    dataset = bigquery.Dataset(dataset_id)
                    dataset.location = "US"  # Default location
                    dataset = self.client.create_dataset(dataset, exists_ok=True)
                    logger.info(f"Dataset {dataset_id} created")
                    
                    # Now create the table
                    table_id = f"{self.project_id}.{self.dataset}.{table_name}"
                    table = bigquery.Table(table_id, schema=self._get_table_schema(table_name))
                    table = self.client.create_table(table, exists_ok=True)
                    logger.info(f"Table {table_id} created")
                except Exception as e:
                    logger.error(f"Error creating dataset/table {table_name}: {e}")
            except Exception as e:
                logger.error(f"Error creating table {table_name}: {e}")
    
    def insert_rows(self, table_name: str, rows: List[Dict[str, Any]]) -> None:
        """
        Insert rows into BigQuery table.
        
        TEMPORARILY DISABLED: BigQuery ingestion is disabled.
        This method now only logs the operation.
        
        Args:
            table_name: Name of the BigQuery table
            rows: List of dictionaries representing rows to insert
        """
        if not rows:
            logger.warning(f"No rows to insert into {table_name}")
            return
        
        # TEMPORARILY DISABLED - Just log instead of writing to BigQuery
        logger.info(f"[BIGQUERY DISABLED] Would insert {len(rows)} rows into {table_name}")
        logger.debug(f"Sample row: {rows[0] if rows else 'N/A'}")
        return
        
        # Original BigQuery code (commented out for now)
        # if not self.client or not self.project_id:
        #     logger.warning(f"BigQuery client not available, would insert {len(rows)} rows into {table_name}")
        #     logger.debug(f"Sample row: {rows[0] if rows else 'N/A'}")
        #     return
        # 
        # try:
        #     # Ensure tables exist
        #     self.create_tables_if_not_exists()
        #     
        #     # Prepare rows (convert JSON fields to strings)
        #     prepared_rows = self._prepare_rows(table_name, rows)
        #     
        #     # Insert rows
        #     table_id = f"{self.project_id}.{self.dataset}.{table_name}"
        #     table_ref = self.client.get_table(table_id)
        #     
        #     errors = self.client.insert_rows_json(table_ref, prepared_rows)
        #     
        #     if errors:
        #         logger.error(f"BigQuery insert errors for {table_name}: {errors}")
        #         raise Exception(f"Failed to insert rows: {errors}")
        #     
        #     logger.info(f"Successfully inserted {len(rows)} rows into {table_name}")
        #     
        # except NotFound:
        #     logger.error(f"Table {table_name} not found. Please create it first.")
        #     raise
        # except Exception as e:
        #     logger.error(f"Error inserting rows into {table_name}: {e}", exc_info=True)
        #     raise
    
    def read_rows(self, table_name: str, job_id: str) -> List[Dict[str, Any]]:
        """
        Read rows from BigQuery table filtered by job_id.
        
        Args:
            table_name: Name of the BigQuery table
            job_id: Job ID to filter by
            
        Returns:
            List of dictionaries representing rows
        """
        logger.info(f"Reading rows from {table_name} for job_id: {job_id}")
        
        if not self.client or not self.project_id:
            logger.warning(f"BigQuery client not available, returning empty list")
            return []
        
        try:
            query = f"""
                SELECT * 
                FROM `{self.project_id}.{self.dataset}.{table_name}`
                WHERE job_id = @job_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
                ]
            )
            
            results = self.client.query(query, job_config=job_config)
            rows = [dict(row) for row in results]
            
            logger.info(f"Read {len(rows)} rows from {table_name} for job_id: {job_id}")
            return rows
            
        except Exception as e:
            logger.error(f"Error reading rows from {table_name}: {e}", exc_info=True)
            return []


# Global service instance
bigquery_service = BigQueryService()
