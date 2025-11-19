"""Main orchestrator for Tableau to Looker migration workflow."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow.phase1_dsl_generation import run_phase1
from workflow.phase2_lookml_generation import run_phase2
from workflow.phase3_mcp_deployment import run_phase3


def main():
    """Run complete migration workflow."""
    print("=" * 80)
    print("TABLEAU TO LOOKER MIGRATION WORKFLOW")
    print("=" * 80)
    print("\nThis workflow will:")
    print("  1. Generate DSL from Tableau chunks")
    print("  2. Generate LookML from DSL")
    print("  3. Deploy LookML to Looker via MCP")
    print()
    
    # Phase 1: DSL Generation
    run_phase1()
    
    # Phase 2: LookML Generation
    run_phase2()
    
    # Phase 3: MCP Deployment
    response = input("\nProceed with MCP deployment to Looker? (y/n): ")
    if response.lower() == 'y':
        run_phase3()
    else:
        print("\nSkipping MCP deployment. LookML files are in generated_lookml/")
    
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

