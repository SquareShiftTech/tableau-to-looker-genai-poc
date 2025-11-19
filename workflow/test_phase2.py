"""Test script for Phase 2: LookML Generation."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow.phase2_lookml_generation import run_phase2, LookMLGenerator
from workflow.gemini_client import GeminiClient


def check_setup():
    """Check if all required setup is complete for Phase 2."""
    print("=" * 80)
    print("PHASE 2 SETUP CHECK")
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
    
    # Check for DSL files
    dsl_dir = Path("generated_dsl")
    if not dsl_dir.exists():
        issues.append("❌ generated_dsl directory not found")
        print("   Run Phase 1 first: python -m workflow.test_phase1")
    else:
        connection_dsl = list(dsl_dir.glob("*_connection.dsl"))
        field_dsl = list(dsl_dir.glob("*_fields.dsl"))
        worksheet_dsl = dsl_dir / "worksheets.dsl"
        dashboard_dsl = dsl_dir / "dashboards.dsl"
        
        if not connection_dsl:
            warnings.append("⚠️  No connection DSL files found (*_connection.dsl)")
        else:
            print(f"✓ Found {len(connection_dsl)} connection DSL file(s)")
            for f in connection_dsl[:3]:
                print(f"    - {f.name}")
            if len(connection_dsl) > 3:
                print(f"    ... and {len(connection_dsl) - 3} more")
        
        if not field_dsl:
            warnings.append("⚠️  No field DSL files found (*_fields.dsl)")
        else:
            print(f"✓ Found {len(field_dsl)} field DSL file(s)")
        
        if not worksheet_dsl.exists():
            warnings.append("⚠️  No worksheets.dsl found")
        else:
            print(f"✓ Found {worksheet_dsl.name}")
        
        if not dashboard_dsl.exists():
            warnings.append("⚠️  No dashboards.dsl found")
        else:
            print(f"✓ Found {dashboard_dsl.name}")
    
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
        print("\nPlease fix the issues above before running Phase 2.")
        return False
    else:
        print("✓ All checks passed! Ready to run Phase 2.")
        return True


def test_phase2():
    """Run Phase 2: LookML Generation."""
    print("\n" + "=" * 80)
    print("RUNNING PHASE 2: LOOKML GENERATION")
    print("=" * 80)
    print()
    
    try:
        run_phase2()
        
        # Check output
        print("\n" + "=" * 80)
        print("PHASE 2 RESULTS")
        print("=" * 80)
        
        lookml_dir = Path("generated_lookml")
        if lookml_dir.exists():
            views_dir = lookml_dir / "views"
            models_dir = lookml_dir / "models"
            dashboards_dir = lookml_dir / "dashboards"
            
            views = list(views_dir.glob("*.view.lkml")) if views_dir.exists() else []
            models = list(models_dir.glob("*.model.lkml")) if models_dir.exists() else []
            dashboards = list(dashboards_dir.glob("*.dashboard.lookml")) if dashboards_dir.exists() else []
            explores_file = lookml_dir / "explores.lkml"
            
            print(f"\n✓ Successfully generated LookML files:\n")
            
            if models:
                print(f"Model files ({len(models)}):")
                for m in models:
                    size = m.stat().st_size
                    print(f"  ✓ {m.name} ({size:,} bytes)")
            
            if views:
                print(f"\nView files ({len(views)}):")
                for v in views[:10]:  # Show first 10
                    size = v.stat().st_size
                    print(f"  ✓ {v.name} ({size:,} bytes)")
                if len(views) > 10:
                    print(f"  ... and {len(views) - 10} more view files")
            
            if explores_file.exists():
                size = explores_file.stat().st_size
                print(f"\n✓ {explores_file.name} ({size:,} bytes)")
            
            if dashboards:
                print(f"\nDashboard files ({len(dashboards)}):")
                for d in dashboards:
                    size = d.stat().st_size
                    print(f"  ✓ {d.name} ({size:,} bytes)")
            
            print("\n" + "=" * 80)
            print("PHASE 2 COMPLETE ✓")
            print("=" * 80)
            print("\nGenerated LookML files are in: generated_lookml/")
            print("\nNext step: Review the LookML files, then run Phase 3 to deploy")
            print("  python -m workflow.test_phase3")
            return True
        else:
            print("\n❌ generated_lookml directory not created")
            return False
    except Exception as e:
        print(f"\n❌ Phase 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("=" * 80)
    print("PHASE 2 TEST: LOOKML GENERATION")
    print("=" * 80)
    print()
    
    # Check setup
    if not check_setup():
        return
    
    # Confirm before running (skip in debug mode)
    import sys
    is_debug = hasattr(sys, 'gettrace') and sys.gettrace() is not None
    
    if not is_debug:
        print("\nReady to run Phase 2. This will:")
        print("  1. Generate Model LookML from Connection DSL")
        print("  2. Generate View LookML files from Field DSL")
        print("  3. Generate Explore definitions from Worksheet DSL")
        print("  4. Generate Dashboard LookML files from Dashboard DSL")
        print("\nThis will make API calls to Vertex AI (Gemini).")
        
        response = input("\nProceed? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
    else:
        print("\n[DEBUG] Running in debug mode - skipping confirmation")
        print("Ready to run Phase 2...")
    
    test_phase2()


if __name__ == "__main__":
    main()

