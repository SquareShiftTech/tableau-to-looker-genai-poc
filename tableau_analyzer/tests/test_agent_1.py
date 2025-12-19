"""
Test Agent 1: Tableau Domain Expert
Tests both exploration and query modes
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1 import agent_1_explore, query_tableau_expert


def test_agent_1_exploration():
    """Test Agent 1 exploration mode with sample Tableau file"""
    
    print("\n" + "="*70)
    print("🧪 TEST: AGENT 1 EXPLORATION MODE")
    print("="*70)
    
    # Path to test file (use existing file from your project)
    test_file = "../input_files/tableau/sales_summary_final.xml"
    
    # Create initial state
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
        errors=[]
    )
    
    print(f"📂 Testing with file: {test_file}")
    
    # Run Agent 1 exploration
    result_state = agent_1_explore(initial_state)
    
    # Display results
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    
    if result_state["errors"]:
        print("\n❌ ERRORS:")
        for error in result_state["errors"]:
            print(f"   • {error}")
        return False
    else:
        print("\n✅ NO ERRORS - Exploration successful")
    
    print(f"\n✅ Agent 1 Ready: {result_state.get('agent_1_ready', False)}")
    
    print("\n📋 INVENTORY:")
    inventory = result_state.get("inventory", {})
    print(json.dumps({
        "worksheets_count": len(inventory.get("worksheets", [])),
        "dashboards_count": len(inventory.get("dashboards", [])),
        "datasources_count": len(inventory.get("datasources", [])),
        "calculations_count": len(inventory.get("calculations", []))
    }, indent=2))
    
    return result_state


def test_agent_1_query(state: AnalysisState):
    """Test Agent 1 query mode"""
    
    print("\n" + "="*70)
    print("🧪 TEST: AGENT 1 QUERY MODE")
    print("="*70)
    
    if not state.get("agent_1_ready"):
        print("❌ Agent 1 not ready - skipping query test")
        return
    
    # Test questions
    test_questions = [
        "How many worksheets are in this Tableau file?",
        "What are the names of the dashboards?",
        "Are there any calculated fields in the datasources?"
    ]
    
    print(f"\nAsking {len(test_questions)} test questions...\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n--- Test Question {i} ---")
        answer = query_tableau_expert(state, question, asking_agent="test_script")
        print(f"Question: {question}")
        print(f"Answer: {answer[:200]}...")
    
    print("\n" + "="*70)
    print("✅ QUERY MODE TEST COMPLETE")
    print("="*70)
    
    # Show conversation log
    conversations = state.get("agent_conversations", [])
    print(f"\nTotal conversations logged: {len(conversations)}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 TESTING AGENT 1: TABLEAU DOMAIN EXPERT")
    print("="*70)
    
    # Test exploration
    state = test_agent_1_exploration()
    
    # Test query mode if exploration succeeded
    if state and state.get("agent_1_ready"):
        test_agent_1_query(state)
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70)
