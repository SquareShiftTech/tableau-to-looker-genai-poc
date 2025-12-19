"""
Main entry point for Tableau Analyzer - Conversational Multi-Agent System

This demonstrates the TRUE AGENTIC approach where:
- Agent 1 deeply understands the Tableau file
- Agent 2 asks Agent 1 questions about complexity
- All interactions are conversational, not rule-based
"""
import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from workflows.tableau_workflow import run_tableau_workflow
from config.settings import INPUT_FILES_DIR, SAMPLE_FILE


def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("🚀 TABLEAU ANALYZER - CONVERSATIONAL MULTI-AGENT SYSTEM")
    print("="*70)
    print("\nThis system demonstrates TRUE AGENTIC architecture:")
    print("  • Agent 1: Tableau Expert with deep understanding")
    print("  • Agent 2: Complexity Analyzer (asks Agent 1 questions)")
    print("  • Agent 3: Feature Extractor (future)")
    print("\nKey Innovation: Agents CONVERSE instead of just parsing")
    print("="*70)
    
    # Determine file path
    # Try relative path from tableau_analyzer directory
    script_dir = Path(__file__).parent
    test_file = script_dir / INPUT_FILES_DIR / SAMPLE_FILE
    
    # If that doesn't exist, try from project root
    if not test_file.exists():
        test_file = script_dir.parent / "input_files" / "tableau" / SAMPLE_FILE
    
    # If still not found, try absolute path

    if not test_file.exists():
        test_file = Path("input_files/tableau/sales_summary_final.xml")
    
    if not test_file.exists():
        print(f"\n❌ ERROR: Test file not found!")
        print(f"   Tried: {test_file}")
        print(f"\nPlease ensure a Tableau XML file exists at:")
        print(f"   input_files/tableau/sales_summary_final.xml")
        print(f"\nOr set the file path in config/settings.py")
        return
    
    print(f"\n📂 Using file: {test_file}")
    
    # Check GCP configuration
    from config.settings import PROJECT_ID
    if PROJECT_ID == "YOUR_GCP_PROJECT_ID":
        print("\n⚠️  WARNING: GCP Project ID not configured!")
        print("   Please update tableau_analyzer/config/settings.py")
        print("   Or set environment variable: GCP_PROJECT_ID")
        print("\n   The system will attempt to run but may fail without proper auth.")
        input("\n   Press Enter to continue anyway, or Ctrl+C to exit...")
    
    # Run the workflow
    try:
        final_state = run_tableau_workflow(str(test_file), bi_tool_type="tableau")
        
        # Final summary
        print("\n" + "="*70)
        print("🎉 EXECUTION COMPLETE")
        print("="*70)
        
        if final_state.get("errors"):
            print(f"\n⚠️  Completed with {len(final_state['errors'])} error(s)")
        else:
            print("\n✅ Completed successfully with no errors")
        
        print(f"\nAgent Conversations: {len(final_state.get('agent_conversations', []))}")
        print(f"Complexity Score: {final_state.get('complexity_analysis', {}).get('complexity_score', 'N/A')}")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ EXECUTION FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
