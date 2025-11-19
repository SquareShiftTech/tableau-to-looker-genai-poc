"""Test script for Phase 1: DSL Generation."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow.phase1_dsl_generation import run_phase1, DSLGenerator
from workflow.gemini_client import GeminiClient


def check_setup():
    """Check if all required setup is complete for Phase 1."""
    print("=" * 80)
    print("PHASE 1 SETUP CHECK")
    print("=" * 80)
    
    issues = []
    warnings = []
    
    # Check Vertex AI credentials (service account OR gcloud auth)
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        if not Path(creds_path).exists():
            issues.append(f"❌ Credentials file not found: {creds_path}")
        else:
            print(f"✓ GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
    else:
        # Check if using gcloud auth (personal account)
        print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
        print("   Using gcloud application-default credentials (personal account)")
        print("   Make sure you've run: gcloud auth application-default login")
    
    # Check Google Cloud Project
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        # Check config file
        from workflow.config import VERTEX_AI_PROJECT
        if VERTEX_AI_PROJECT:
            project_id = VERTEX_AI_PROJECT
            print(f"✓ Using project from config: {project_id}")
        else:
            issues.append("❌ GOOGLE_CLOUD_PROJECT not set")
            print("   Set it with: export GOOGLE_CLOUD_PROJECT=your-project-id")
    else:
        print(f"✓ GOOGLE_CLOUD_PROJECT: {project_id}")
    
    # Check for chunk files
    from workflow.config import CHUNKS_DIR
    chunks_dir = Path(CHUNKS_DIR)
    connection_chunks = list(chunks_dir.glob("chunk_*_connection.json"))
    field_chunks = list(chunks_dir.glob("chunk_*_fields_*.json"))
    worksheet_chunks = list(chunks_dir.glob("chunk_worksheet_batch_*.json"))
    dashboard_chunks = list(chunks_dir.glob("chunk_dashboard_batch_*.json"))
    
    if not connection_chunks:
        issues.append("❌ No connection chunk files found (chunk_*_connection.json)")
    else:
        print(f"✓ Found {len(connection_chunks)} connection chunk(s)")
        for chunk in connection_chunks[:3]:
            print(f"    - {chunk.name}")
        if len(connection_chunks) > 3:
            print(f"    ... and {len(connection_chunks) - 3} more")
    
    if not field_chunks:
        warnings.append("⚠️  No field chunk files found (chunk_*_fields_*.json)")
    else:
        print(f"✓ Found {len(field_chunks)} field chunk(s)")
    
    if not worksheet_chunks:
        warnings.append("⚠️  No worksheet batch chunks found (chunk_worksheet_batch_*.json)")
    else:
        print(f"✓ Found {len(worksheet_chunks)} worksheet batch chunk(s)")
    
    if not dashboard_chunks:
        warnings.append("⚠️  No dashboard batch chunks found (chunk_dashboard_batch_*.json)")
    else:
        print(f"✓ Found {len(dashboard_chunks)} dashboard batch chunk(s)")
    
    # Test Gemini client
    print("\nTesting Gemini client...")
    try:
        client = GeminiClient()
        print("✓ Gemini client initialized successfully")
    except Exception as e:
        issues.append(f"❌ Gemini client initialization failed: {e}")
        print(f"   Error: {e}")
    
    print()
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
        print("\nPlease fix the issues above before running Phase 1.")
        return False
    else:
        print("✓ All checks passed! Ready to run Phase 1.")
        return True


def test_phase1():
    """Run Phase 1: DSL Generation."""
    print("\n" + "=" * 80)
    print("RUNNING PHASE 1: DSL GENERATION")
    print("=" * 80)
    print()
    
    try:
        run_phase1()
        
        # Check output
        print("\n" + "=" * 80)
        print("PHASE 1 RESULTS")
        print("=" * 80)
        
        dsl_dir = Path("generated_dsl")
        if dsl_dir.exists():
            dsl_files = list(dsl_dir.glob("*.dsl"))
            if dsl_files:
                print(f"\n✓ Successfully generated {len(dsl_files)} DSL file(s):\n")
                
                # Group by type
                connection_files = [f for f in dsl_files if "_connection.dsl" in f.name]
                field_files = [f for f in dsl_files if "_fields.dsl" in f.name]
                worksheet_file = dsl_dir / "worksheets.dsl"
                dashboard_file = dsl_dir / "dashboards.dsl"
                
                if connection_files:
                    print("Connection DSL files:")
                    for f in connection_files:
                        size = f.stat().st_size
                        print(f"  ✓ {f.name} ({size:,} bytes)")
                
                if field_files:
                    print("\nField DSL files:")
                    for f in field_files:
                        size = f.stat().st_size
                        print(f"  ✓ {f.name} ({size:,} bytes)")
                
                if worksheet_file.exists():
                    size = worksheet_file.stat().st_size
                    print(f"\n✓ {worksheet_file.name} ({size:,} bytes)")
                
                if dashboard_file.exists():
                    size = dashboard_file.stat().st_size
                    print(f"✓ {dashboard_file.name} ({size:,} bytes)")
                
                print("\n" + "=" * 80)
                print("PHASE 1 COMPLETE ✓")
                print("=" * 80)
                print("\nNext step: Run Phase 2 to generate LookML files")
                print("  python -m workflow.test_phase2")
                return True
            else:
                print("\n❌ No DSL files generated")
                return False
        else:
            print("\n❌ generated_dsl directory not created")
            return False
    except Exception as e:
        print(f"\n❌ Phase 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("=" * 80)
    print("PHASE 1 TEST: DSL GENERATION")
    print("=" * 80)
    print()
    
    # Check setup
    if not check_setup():
        return
    
    # Confirm before running (skip in debug mode)
    import sys
    is_debug = hasattr(sys, 'gettrace') and sys.gettrace() is not None
    
    if not is_debug:
        print("\nReady to run Phase 1. This will:")
        print("  1. Generate Connection DSL from connection chunks")
        print("  2. Generate Field DSL from field chunks")
        print("  3. Generate Worksheet DSL from worksheet batches")
        print("  4. Generate Dashboard DSL from dashboard batches")
        print("\nThis will make API calls to Vertex AI (Gemini).")
        
        response = input("\nProceed? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
    else:
        print("\n[DEBUG] Running in debug mode - skipping confirmation")
        print("Ready to run Phase 1...")
    
    test_phase1()


if __name__ == "__main__":
    main()

