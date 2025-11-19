"""Phase 2: Generate LookML from DSL using Gemini."""

import json
from pathlib import Path
from typing import Dict, List
from .config import GENERATED_DSL_DIR, GENERATED_LOOKML_DIR, LOOKML_PROMPTS_DIR
from .gemini_client import GeminiClient


class LookMLGenerator:
    """Generate LookML from Compact DSL."""
    
    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client
    
    def load_prompt(self, prompt_file: str) -> str:
        """Load prompt from file."""
        prompt_path = LOOKML_PROMPTS_DIR / prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding='utf-8')
    
    def load_dsl(self, dsl_file: str) -> str:
        """Load DSL from file."""
        dsl_path = GENERATED_DSL_DIR / dsl_file
        if not dsl_path.exists():
            raise FileNotFoundError(f"DSL file not found: {dsl_path}")
        return dsl_path.read_text(encoding='utf-8')
    
    def generate_model_lookml(self, connection_dsl_file: str) -> str:
        """
        Generate Model LookML from Connection DSL.
        
        Args:
            connection_dsl_file: Path to connection DSL file
            
        Returns:
            Model LookML content
        """
        prompt = self.load_prompt("connection_to_lookml.txt")
        dsl_content = self.load_dsl(connection_dsl_file)
        
        full_prompt = f"{prompt}\n\n---\n\nCONNECTION DSL:\n\n{dsl_content}"
        
        lookml = self.client.generate(full_prompt)
        
        return lookml
    
    def generate_view_lookml(self, field_dsl_file: str) -> Dict[str, str]:
        """
        Generate View LookML files from Field DSL.
        Returns dict mapping table_name -> LookML content.
        
        Args:
            field_dsl_file: Path to field DSL file
            
        Returns:
            Dict of {table_name: lookml_content}
        """
        prompt = self.load_prompt("fields_to_lookml.txt")
        dsl_content = self.load_dsl(field_dsl_file)
        
        full_prompt = f"{prompt}\n\n---\n\nFIELD DSL:\n\n{dsl_content}"
        
        lookml_output = self.client.generate(full_prompt)
        
        # Parse the output to extract individual view files
        # The prompt should output multiple view files, we need to parse them
        views = self._parse_view_files(lookml_output)
        
        return views
    
    def _parse_view_files(self, lookml_output: str) -> Dict[str, str]:
        """
        Parse LookML output to extract individual view files.
        Assumes output format: ```lkml\nview: name { ... }\n``` blocks
        """
        views = {}
        
        # Split by view blocks
        import re
        view_pattern = r'view:\s*(\w+)\s*\{[^}]*\}'
        matches = re.finditer(view_pattern, lookml_output, re.DOTALL)
        
        for match in matches:
            view_name = match.group(1)
            view_content = match.group(0)
            views[view_name] = view_content
        
        # If regex didn't work, try to extract from code blocks
        if not views:
            code_block_pattern = r'```(?:lkml)?\n(.*?)```'
            blocks = re.findall(code_block_pattern, lookml_output, re.DOTALL)
            for block in blocks:
                if 'view:' in block:
                    # Extract view name and content
                    view_match = re.search(r'view:\s*(\w+)', block)
                    if view_match:
                        view_name = view_match.group(1)
                        views[view_name] = block.strip()
        
        return views
    
    def generate_explore_lookml(self, worksheet_dsl_file: str, connection_dsl_file: str = None) -> str:
        """
        Generate Explore definitions from Worksheet DSL.
        
        Args:
            worksheet_dsl_file: Path to worksheet DSL file
            connection_dsl_file: Optional connection DSL for context
            
        Returns:
            Explore LookML content (to append to model)
        """
        prompt = self.load_prompt("worksheet_to_lookml.txt")
        worksheet_dsl = self.load_dsl(worksheet_dsl_file)
        
        full_prompt = f"{prompt}\n\n---\n\nWORKSHEET DSL:\n\n{worksheet_dsl}"
        
        if connection_dsl_file:
            connection_dsl = self.load_dsl(connection_dsl_file)
            full_prompt += f"\n\n---\n\nCONNECTION DSL (for context):\n\n{connection_dsl}"
        
        explore_lookml = self.client.generate(full_prompt)
        
        return explore_lookml
    
    def generate_dashboard_lookml(self, dashboard_dsl_file: str) -> Dict[str, str]:
        """
        Generate Dashboard LookML files from Dashboard DSL.
        Returns dict mapping dashboard_name -> LookML content.
        
        Args:
            dashboard_dsl_file: Path to dashboard DSL file
            
        Returns:
            Dict of {dashboard_name: lookml_content}
        """
        prompt = self.load_prompt("dashboard_to_lookml.txt")
        dsl_content = self.load_dsl(dashboard_dsl_file)
        
        full_prompt = f"{prompt}\n\n---\n\nDASHBOARD DSL:\n\n{dsl_content}"
        
        lookml_output = self.client.generate(full_prompt)
        
        # Parse the output to extract individual dashboard files
        dashboards = self._parse_dashboard_files(lookml_output)
        
        return dashboards
    
    def _parse_dashboard_files(self, lookml_output: str) -> Dict[str, str]:
        """Parse LookML output to extract individual dashboard files."""
        dashboards = {}
        
        import re
        dashboard_pattern = r'dashboard:\s*(\w+)\s*\{[^}]*\}'
        matches = re.finditer(dashboard_pattern, lookml_output, re.DOTALL)
        
        for match in matches:
            dashboard_name = match.group(1)
            dashboard_content = match.group(0)
            dashboards[dashboard_name] = dashboard_content
        
        # If regex didn't work, try code blocks
        if not dashboards:
            code_block_pattern = r'```(?:lkml)?\n(.*?)```'
            blocks = re.findall(code_block_pattern, lookml_output, re.DOTALL)
            for block in blocks:
                if 'dashboard:' in block:
                    dashboard_match = re.search(r'dashboard:\s*(\w+)', block)
                    if dashboard_match:
                        dashboard_name = dashboard_match.group(1)
                        dashboards[dashboard_name] = block.strip()
        
        return dashboards
    
    def save_lookml(self, content: str, filepath: str, append: bool = False):
        """
        Save LookML to file.
        
        Args:
            content: LookML content to save
            filepath: Relative path from GENERATED_LOOKML_DIR
            append: If True and file exists, append content. Otherwise overwrite.
        """
        output_path = GENERATED_LOOKML_DIR / filepath
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if append and output_path.exists():
            # Append to existing file
            existing_content = output_path.read_text(encoding='utf-8')
            updated_content = f"{existing_content}\n\n{content}"
            output_path.write_text(updated_content, encoding='utf-8')
            print(f"  ✓ Appended to: {output_path}")
        else:
            # Create new file or overwrite
            output_path.write_text(content, encoding='utf-8')
            print(f"  ✓ Saved: {output_path}")


def run_phase2():
    """Run Phase 2: Generate all LookML files."""
    print("=" * 80)
    print("PHASE 2: LOOKML GENERATION")
    print("=" * 80)
    
    # SECTION: Initialize
    print("\n[DEBUG] SECTION: Initializing Gemini Client and Generator")
    client = GeminiClient()
    generator = LookMLGenerator(client)
    print("[DEBUG] ✓ Client and generator initialized")
    
    dsl_dir = Path(GENERATED_DSL_DIR)
    print(f"[DEBUG] ✓ DSL directory: {dsl_dir}")
    
    # 2.1 Generate Model LookML
    print("\n" + "-" * 80)
    print("[2.1] Generating Model LookML...")
    print("[DEBUG] SECTION: Model LookML Generation")
    connection_dsl_files = list(dsl_dir.glob("*_connection.dsl"))
    print(f"[DEBUG] Found {len(connection_dsl_files)} connection DSL file(s)")
    
    for idx, conn_dsl in enumerate(connection_dsl_files, 1):
        ds_id = conn_dsl.stem.replace("_connection", "")
        print(f"\n[DEBUG] Processing model {idx}/{len(connection_dsl_files)}: {conn_dsl.name}")
        print(f"  Processing: {conn_dsl.name}")
        print(f"[DEBUG] Calling generate_model_lookml...")
        lookml = generator.generate_model_lookml(conn_dsl.name)
        print(f"[DEBUG] ✓ LookML generated ({len(lookml)} chars)")
        
        # Normalize dataset name to snake_case for file name
        import re
        normalized_ds_id = re.sub(r'[^a-z0-9_]', '', ds_id.lower().replace(' ', '_').replace('-', '_'))
        generator.save_lookml(lookml, f"models/{normalized_ds_id}.model.lkml")
        print(f"[DEBUG] ✓ Saved model file: {normalized_ds_id}.model.lkml")
    
    # 2.2 Generate View LookML Files
    print("\n" + "-" * 80)
    print("[2.2] Generating View LookML Files...")
    print("[DEBUG] SECTION: View LookML Generation")
    field_dsl_files = list(dsl_dir.glob("*_fields.dsl"))
    print(f"[DEBUG] Found {len(field_dsl_files)} field DSL file(s)")
    
    for idx, field_dsl in enumerate(field_dsl_files, 1):
        ds_id = field_dsl.stem.replace("_fields", "")
        print(f"\n[DEBUG] Processing field DSL {idx}/{len(field_dsl_files)}: {field_dsl.name}")
        print(f"  Processing: {field_dsl.name}")
        print(f"[DEBUG] Calling generate_view_lookml...")
        views = generator.generate_view_lookml(field_dsl.name)
        print(f"[DEBUG] ✓ Generated {len(views)} view(s)")
        
        for view_idx, (table_name, view_content) in enumerate(views.items(), 1):
            # Normalize table name to snake_case
            import re
            normalized_name = table_name.lower().replace(' ', '_').replace('-', '_')
            # Remove special characters, keep only alphanumeric and underscores
            normalized_name = re.sub(r'[^a-z0-9_]', '', normalized_name)
            
            print(f"[DEBUG]   Saving view {view_idx}/{len(views)}: {normalized_name}.view.lkml ({len(view_content)} chars)")
            generator.save_lookml(
                view_content, 
                f"views/{normalized_name}.view.lkml",
                append=False  # Overwrite to ensure complete view files
            )
        print(f"[DEBUG] ✓ Saved {len(views)} view file(s) for {field_dsl.name}")
    
    # 2.3 Generate Explore Definitions and Append to Model Files
    print("\n" + "-" * 80)
    print("[2.3] Generating Explore Definitions...")
    print("[DEBUG] SECTION: Explore LookML Generation")
    worksheet_dsl = dsl_dir / "worksheets.dsl"
    print(f"[DEBUG] Checking for worksheets.dsl: {worksheet_dsl.exists()}")
    
    if worksheet_dsl.exists():
        print(f"  Processing: {worksheet_dsl.name}")
        # Get connection DSL for context (use first one found)
        connection_dsl = connection_dsl_files[0] if connection_dsl_files else None
        print(f"[DEBUG] Using connection DSL for context: {connection_dsl.name if connection_dsl else 'None'}")
        print(f"[DEBUG] Calling generate_explore_lookml...")
        explore_lookml = generator.generate_explore_lookml(
            "worksheets.dsl",
            connection_dsl.name if connection_dsl else None
        )
        print(f"[DEBUG] ✓ Explore LookML generated ({len(explore_lookml)} chars)")
        
        # Append explores to the corresponding model file(s)
        # For now, append to first model file found (can be enhanced to match by datasource)
        if connection_dsl_files:
            model_file = connection_dsl_files[0]
            ds_id = model_file.stem.replace("_connection", "")
            # Normalize dataset name
            import re
            normalized_ds_id = re.sub(r'[^a-z0-9_]', '', ds_id.lower().replace(' ', '_').replace('-', '_'))
            print(f"[DEBUG] Appending explores to model: {normalized_ds_id}.model.lkml")
            generator.save_lookml(
                explore_lookml, 
                f"models/{normalized_ds_id}.model.lkml",
                append=True
            )
            print(f"[DEBUG] ✓ Appended explores to model file")
        else:
            # Fallback: save to separate file if no model file exists
            print(f"[DEBUG] No model file found, saving to explores.lkml")
            generator.save_lookml(explore_lookml, "explores.lkml")
    else:
        print("  No worksheets.dsl found")
        print("[DEBUG] ⚠️  Skipping explore generation")
    
    # 2.4 Generate Dashboard LookML Files
    print("\n" + "-" * 80)
    print("[2.4] Generating Dashboard LookML Files...")
    print("[DEBUG] SECTION: Dashboard LookML Generation")
    dashboard_dsl = dsl_dir / "dashboards.dsl"
    print(f"[DEBUG] Checking for dashboards.dsl: {dashboard_dsl.exists()}")
    
    if dashboard_dsl.exists():
        print(f"  Processing: {dashboard_dsl.name}")
        print(f"[DEBUG] Calling generate_dashboard_lookml...")
        dashboards = generator.generate_dashboard_lookml("dashboards.dsl")
        print(f"[DEBUG] ✓ Generated {len(dashboards)} dashboard(s)")
        
        for dash_idx, (dashboard_name, dashboard_content) in enumerate(dashboards.items(), 1):
            # Normalize dashboard name to snake_case
            import re
            normalized_name = re.sub(r'[^a-z0-9_]', '', dashboard_name.lower().replace(' ', '_').replace('-', '_'))
            print(f"[DEBUG]   Saving dashboard {dash_idx}/{len(dashboards)}: {normalized_name}.dashboard.lookml ({len(dashboard_content)} chars)")
            # Each dashboard gets its own file (no appending)
            generator.save_lookml(dashboard_content, f"dashboards/{normalized_name}.dashboard.lookml")
        print(f"[DEBUG] ✓ Saved {len(dashboards)} dashboard file(s)")
    else:
        print("  No dashboards.dsl found")
        print("[DEBUG] ⚠️  Skipping dashboard generation")
    
    print("\n" + "=" * 80)
    print("PHASE 2 COMPLETE: LookML files generated in generated_lookml/")
    print("=" * 80)
    print("[DEBUG] SECTION: Phase 2 Complete")


if __name__ == "__main__":
    run_phase2()

