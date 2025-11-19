"""Phase 1: Generate DSL from Tableau metadata chunks using Gemini."""

import json
from pathlib import Path
from typing import Dict, List
from .config import CHUNKS_DIR, GENERATED_DSL_DIR, DSL_PROMPTS_DIR
from .gemini_client import GeminiClient


class DSLGenerator:
    """Generate Compact DSL from Tableau metadata chunks."""
    
    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client
    
    def load_prompt(self, prompt_file: str) -> str:
        """Load prompt from file."""
        prompt_path = DSL_PROMPTS_DIR / prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding='utf-8')
    
    def generate_connection_dsl(self, connection_chunk_file: str) -> str:
        """
        Generate Connection DSL from connection chunk.
        
        Args:
            connection_chunk_file: Path to connection chunk JSON
            
        Returns:
            Connection DSL string
        """
        prompt = self.load_prompt("connection.txt")
        chunk_path = CHUNKS_DIR / connection_chunk_file
        
        # Use file upload for Gemini
        dsl = self.client.generate_with_file(
            prompt=prompt,
            file_path=str(chunk_path),
            mime_type="application/json"
        )
        
        return dsl
    
    def generate_field_dsl(self, field_chunk_files: List[str], datasource_id: str) -> str:
        """
        Generate Field DSL from field chunks.
        
        Args:
            field_chunk_files: List of field chunk JSON file paths
            datasource_id: Datasource ID for output filename
            
        Returns:
            Combined Field DSL string
        """
        prompt = self.load_prompt("fields.txt")
        all_dsl_blocks = []
        
        for chunk_file in field_chunk_files:
            chunk_path = CHUNKS_DIR / chunk_file
            
            # Generate DSL for this chunk
            dsl_block = self.client.generate_with_file(
                prompt=prompt,
                file_path=str(chunk_path),
                mime_type="application/json"
            )
            
            all_dsl_blocks.append(dsl_block)
        
        # Combine all DSL blocks
        combined_dsl = "\n\n---\n\n".join(all_dsl_blocks)
        
        return combined_dsl
    
    def generate_worksheet_dsl(self, worksheet_batch_files: List[str]) -> str:
        """
        Generate Worksheet DSL from worksheet batch chunks.
        
        Args:
            worksheet_batch_files: List of worksheet batch chunk JSON file paths
            
        Returns:
            Combined Worksheet DSL string
        """
        prompt = self.load_prompt("worksheet.txt")
        all_dsl_blocks = []
        
        for batch_file in worksheet_batch_files:
            batch_path = CHUNKS_DIR / batch_file
            
            # Generate DSL for this batch
            dsl_block = self.client.generate_with_file(
                prompt=prompt,
                file_path=str(batch_path),
                mime_type="application/json"
            )
            
            all_dsl_blocks.append(dsl_block)
        
        # Combine all DSL blocks
        combined_dsl = "\n\n---\n\n".join(all_dsl_blocks)
        
        return combined_dsl
    
    def generate_dashboard_dsl(self, dashboard_batch_files: List[str]) -> str:
        """
        Generate Dashboard DSL from dashboard batch chunks.
        
        Args:
            dashboard_batch_files: List of dashboard batch chunk JSON file paths
            
        Returns:
            Combined Dashboard DSL string
        """
        prompt = self.load_prompt("dashboard.txt")
        all_dsl_blocks = []
        
        for batch_file in dashboard_batch_files:
            batch_path = CHUNKS_DIR / batch_file
            
            # Generate DSL for this batch
            dsl_block = self.client.generate_with_file(
                prompt=prompt,
                file_path=str(batch_path),
                mime_type="application/json"
            )
            
            all_dsl_blocks.append(dsl_block)
        
        # Combine all DSL blocks
        combined_dsl = "\n\n---\n\n".join(all_dsl_blocks)
        
        return combined_dsl
    
    def save_dsl(self, dsl_content: str, filename: str):
        """Save DSL to file."""
        output_path = GENERATED_DSL_DIR / filename
        output_path.write_text(dsl_content, encoding='utf-8')
        print(f"  ✓ Saved: {output_path}")


def run_phase1():
    """Run Phase 1: Generate all DSL files."""
    print("=" * 80)
    print("PHASE 1: DSL GENERATION")
    print("=" * 80)
    
    # SECTION: Initialize
    print("\n[DEBUG] SECTION: Initializing Gemini Client and Generator")
    client = GeminiClient()
    generator = DSLGenerator(client)
    print("[DEBUG] ✓ Client and generator initialized")
    
    # Find all chunk files
    chunks_dir = Path(CHUNKS_DIR)
    print(f"[DEBUG] ✓ Chunks directory: {chunks_dir}")
    
    # 1.1 Generate Connection DSL
    print("\n" + "-" * 80)
    print("[1.1] Generating Connection DSL...")
    print("[DEBUG] SECTION: Connection DSL Generation")
    connection_chunks = list(chunks_dir.glob("chunk_*_connection.json"))
    print(f"[DEBUG] Found {len(connection_chunks)} connection chunk(s)")
    
    for idx, conn_chunk in enumerate(connection_chunks, 1):
        ds_id = conn_chunk.stem.replace("chunk_", "").replace("_connection", "")
        print(f"\n[DEBUG] Processing connection {idx}/{len(connection_chunks)}: {conn_chunk.name}")
        print(f"  Processing: {conn_chunk.name}")
        print(f"[DEBUG] Calling generate_connection_dsl...")
        dsl = generator.generate_connection_dsl(conn_chunk.name)
        print(f"[DEBUG] ✓ DSL generated ({len(dsl)} chars)")
        generator.save_dsl(dsl, f"{ds_id}_connection.dsl")
        print(f"[DEBUG] ✓ Saved DSL file")
    
    # 1.2 Generate Field DSL
    print("\n" + "-" * 80)
    print("[1.2] Generating Field DSL...")
    print("[DEBUG] SECTION: Field DSL Generation")
    # Group field chunks by datasource
    field_chunks_by_ds = {}
    for field_chunk in chunks_dir.glob("chunk_*_fields_*.json"):
        # Extract datasource ID (e.g., "federated.09t851k1wb86c512yov0h1usonym" from "chunk_federated.09t851k1wb86c512yov0h1usonym_fields_0.json")
        parts = field_chunk.stem.split("_fields_")
        if len(parts) == 2:
            ds_id = parts[0].replace("chunk_", "")
            if ds_id not in field_chunks_by_ds:
                field_chunks_by_ds[ds_id] = []
            field_chunks_by_ds[ds_id].append(field_chunk.name)
    
    print(f"[DEBUG] Found {len(field_chunks_by_ds)} datasource(s) with field chunks")
    
    for ds_idx, (ds_id, chunk_files) in enumerate(field_chunks_by_ds.items(), 1):
        print(f"\n[DEBUG] Processing datasource {ds_idx}/{len(field_chunks_by_ds)}: {ds_id}")
        print(f"  Processing datasource: {ds_id} ({len(chunk_files)} chunks)")
        print(f"[DEBUG] Calling generate_field_dsl with {len(chunk_files)} chunk files...")
        dsl = generator.generate_field_dsl(sorted(chunk_files), ds_id)
        print(f"[DEBUG] ✓ DSL generated ({len(dsl)} chars)")
        generator.save_dsl(dsl, f"{ds_id}_fields.dsl")
        print(f"[DEBUG] ✓ Saved DSL file")
    
    # 1.3 Generate Worksheet DSL
    print("\n" + "-" * 80)
    print("[1.3] Generating Worksheet DSL...")
    print("[DEBUG] SECTION: Worksheet DSL Generation")
    worksheet_batches = sorted(chunks_dir.glob("chunk_worksheet_batch_*.json"))
    print(f"[DEBUG] Found {len(worksheet_batches)} worksheet batch chunk(s)")
    
    if worksheet_batches:
        batch_files = [f.name for f in worksheet_batches]
        print(f"  Processing {len(batch_files)} worksheet batches")
        print(f"[DEBUG] Calling generate_worksheet_dsl with {len(batch_files)} batch files...")
        dsl = generator.generate_worksheet_dsl(batch_files)
        print(f"[DEBUG] ✓ DSL generated ({len(dsl)} chars)")
        generator.save_dsl(dsl, "worksheets.dsl")
        print(f"[DEBUG] ✓ Saved DSL file")
    else:
        print("  No worksheet batches found")
        print("[DEBUG] ⚠️  Skipping worksheet DSL generation")
    
    # 1.4 Generate Dashboard DSL
    print("\n" + "-" * 80)
    print("[1.4] Generating Dashboard DSL...")
    print("[DEBUG] SECTION: Dashboard DSL Generation")
    dashboard_batches = sorted(chunks_dir.glob("chunk_dashboard_batch_*.json"))
    print(f"[DEBUG] Found {len(dashboard_batches)} dashboard batch chunk(s)")
    
    if dashboard_batches:
        batch_files = [f.name for f in dashboard_batches]
        print(f"  Processing {len(batch_files)} dashboard batches")
        print(f"[DEBUG] Calling generate_dashboard_dsl with {len(batch_files)} batch files...")
        dsl = generator.generate_dashboard_dsl(batch_files)
        print(f"[DEBUG] ✓ DSL generated ({len(dsl)} chars)")
        generator.save_dsl(dsl, "dashboards.dsl")
        print(f"[DEBUG] ✓ Saved DSL file")
    else:
        print("  No dashboard batches found")
        print("[DEBUG] ⚠️  Skipping dashboard DSL generation")
    
    print("\n" + "=" * 80)
    print("PHASE 1 COMPLETE: DSL files generated in generated_dsl/")
    print("=" * 80)
    print("[DEBUG] SECTION: Phase 1 Complete")


if __name__ == "__main__":
    run_phase1()

