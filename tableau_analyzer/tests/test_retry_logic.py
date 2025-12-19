"""
Test Retry Logic across all agents
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1 import agent_1_explore


def test_agent_1_retry():
    """Test Agent 1 retry logic"""
    
    print("\n" + "="*70)
    print("🧪 TEST: AGENT 1 RETRY LOGIC")
    print("="*70)
    
    # Test with valid file - resolve from project root
    project_root = Path(__file__).parent.parent.parent
    test_file = project_root / "input_files" / "tableau" / "sales_summary_final.xml"
    test_file = str(test_file)
    
    initial_state = AnalysisState(
        bi_tool_type="tableau",
        file_path=test_file,
        file_json={},
        inventory={},
        agent_1_ready=False,
        json_spec=None,
        complexity_analysis={},
        agent_2_questions=[],
        extracted_features={},
        agent_conversations=[],
        errors=[],
        agent_1_attempts=0,
        agent_2_attempts=0,
        agent_3_retry_count=0,
        features_attempted=0,
        features_successful=0,
        features_failed=0,
        feature_schema={}
    )
    
    print(f"Testing with: {test_file}")
    print("Expecting: Agent 1 to explore with retry capability")
    
    # Run Agent 1
    result_state = agent_1_explore(initial_state)
    
    # Check results
    print("\n" + "="*70)
    print("📊 RETRY TEST RESULTS")
    print("="*70)
    
    attempts = result_state.get("agent_1_attempts", 0)
    print(f"\n🔄 Total Attempts: {attempts}")
    
    if result_state.get("agent_1_ready"):
        print(f"✅ Agent 1 succeeded (attempt {attempts})")
        
        if attempts > 1:
            print(f"   Retry logic was used! ({attempts - 1} retries)")
        else:
            print("   Succeeded on first try")
    else:
        print(f"❌ Agent 1 failed after {attempts} attempts")
    
    # Check inventory
    inventory = result_state.get("inventory", {})
    worksheets = len(inventory.get("worksheets", []))
    print(f"\n📋 Worksheets found: {worksheets}")
    
    if result_state.get("errors"):
        print(f"\n❌ Errors encountered:")
        for error in result_state.get("errors", []):
            print(f"   • {error}")
    
    print("\n" + "="*70)
    print("✅ RETRY TEST COMPLETE")
    print("="*70)
    
    return result_state


if __name__ == "__main__":
    test_agent_1_retry()
