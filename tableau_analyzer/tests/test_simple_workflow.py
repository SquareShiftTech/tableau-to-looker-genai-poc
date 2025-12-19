"""
Test Simple Workflow: Fast Complexity Analysis
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.simple_workflow import run_simple_workflow


def test_simple_workflow():
    """Test the simple workflow end-to-end"""
    
    print("\n" + "="*70)
    print("🧪 TEST: SIMPLE WORKFLOW")
    print("="*70)
    
    # Path to test file - resolve from project root
    project_root = Path(__file__).parent.parent.parent
    test_file = project_root / "input_files" / "tableau" / "sales_summary_final.xml"
    test_file = str(test_file)
    
    print(f"Test file: {test_file}")
    print("Expected: Agent 1 explores, Agent 2 analyzes complexity")
    
    # Run workflow
    final_state = run_simple_workflow(test_file, bi_tool_type="tableau")
    
    # Validate results
    print("\n" + "="*70)
    print("📊 VALIDATION")
    print("="*70)
    
    passed = True
    
    # Check Agent 1 results
    if not final_state.get("agent_1_ready"):
        print("❌ Agent 1 not marked as ready")
        passed = False
    else:
        print("✅ Agent 1 completed successfully")
    
    # Check inventory
    inventory = final_state.get("inventory", {})
    if len(inventory.get("worksheets", [])) == 0:
        print("❌ No worksheets found in inventory")
        passed = False
    else:
        print(f"✅ Found {len(inventory.get('worksheets', []))} worksheets")
    
    # Check complexity analysis
    complexity = final_state.get("complexity_analysis", {})
    if "complexity_score" not in complexity:
        print("❌ No complexity score generated")
        passed = False
    else:
        print(f"✅ Complexity score: {complexity.get('complexity_score')}")
    
    # Check conversations
    conversations = final_state.get("agent_conversations", [])
    if len(conversations) == 0:
        print("⚠️  No conversations logged")
    else:
        print(f"✅ {len(conversations)} conversations logged")
    
    # Check retry stats
    if final_state.get("agent_1_attempts", 0) > 1:
        print(f"🔄 Agent 1 required {final_state.get('agent_1_attempts')} attempts")
    
    # Overall result
    print("\n" + "="*70)
    if passed and not final_state.get("errors"):
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
        if final_state.get("errors"):
            print("\nErrors:")
            for error in final_state.get("errors", []):
                print(f"  • {error}")
    print("="*70)
    
    return final_state


if __name__ == "__main__":
    test_simple_workflow()
