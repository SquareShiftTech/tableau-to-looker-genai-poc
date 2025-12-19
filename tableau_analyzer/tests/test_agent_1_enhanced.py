"""
Test Agent 1 Enhanced: Tableau Domain Expert with Retry Logic and Multi-Pass Exploration
Tests enhanced features: multi-pass exploration, retry logic, on-demand deep dives, completeness evaluation
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1_enhanced import (
    agent_1_explore_enhanced,
    query_tableau_expert_enhanced,
    _evaluate_exploration_completeness
)


def test_enhanced_exploration():
    """Test multi-pass exploration completes successfully"""
    
    print("\n" + "="*70)
    print("🧪 TEST: ENHANCED EXPLORATION (MULTI-PASS)")
    print("="*70)
    
    # Path to test file
    project_root = Path(__file__).parent.parent.parent
    test_file = project_root / "input_files" / "tableau" / "sales_summary_final.xml"
    test_file = str(test_file)
    
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
    
    # Run Agent 1 Enhanced exploration
    result_state = agent_1_explore_enhanced(initial_state)
    
    # Validate results
    print("\n" + "="*70)
    print("📊 VALIDATION")
    print("="*70)
    
    passed = True
    
    # Check for errors
    if result_state.get("errors"):
        print("\n❌ ERRORS:")
        for error in result_state["errors"]:
            print(f"   • {error}")
        passed = False
    else:
        print("\n✅ NO ERRORS - Exploration successful")
    
    # Check Agent 1 Enhanced ready flag
    if not result_state.get("agent_1_enhanced_ready", False):
        print("❌ Agent 1 Enhanced not marked as ready")
        passed = False
    else:
        print("✅ Agent 1 Enhanced marked as ready")
    
    # Check inventory
    inventory = result_state.get("inventory", {})
    worksheets_count = len(inventory.get("worksheets", []))
    dashboards_count = len(inventory.get("dashboards", []))
    datasources_count = len(inventory.get("datasources", []))
    calculations_count = len(inventory.get("calculations", []))
    
    print(f"\n📋 INVENTORY:")
    print(f"   Worksheets: {worksheets_count}")
    print(f"   Dashboards: {dashboards_count}")
    print(f"   Datasources: {datasources_count}")
    print(f"   Calculations: {calculations_count}")
    
    if worksheets_count == 0 and dashboards_count == 0:
        print("⚠️  No components found - this might indicate an issue")
        passed = False
    else:
        print("✅ Components found")
    
    # Check exploration passes
    exploration_passes = result_state.get("agent_1_exploration_passes", [])
    print(f"\n🔄 EXPLORATION PASSES: {len(exploration_passes)}")
    for i, pass_result in enumerate(exploration_passes, 1):
        completeness = pass_result.get("completeness_score", 0.0)
        print(f"   Pass {i}: Completeness {completeness:.1%}")
    
    # Check attempts
    attempts = result_state.get("agent_1_attempts", 0)
    print(f"\n🔄 TOTAL ATTEMPTS: {attempts}")
    
    # Check completeness score
    completeness_score = result_state.get("agent_1_completeness_score", 0.0)
    print(f"📈 FINAL COMPLETENESS SCORE: {completeness_score:.1%}")
    
    if completeness_score < 0.5:
        print("⚠️  Low completeness score - exploration may be incomplete")
    
    # Check retry reasons
    retry_reasons = result_state.get("agent_1_retry_reasons", [])
    if retry_reasons:
        print(f"\n⚠️  RETRY REASONS ({len(retry_reasons)}):")
        for reason in retry_reasons:
            print(f"   • {reason}")
    
    print("\n" + "="*70)
    if passed:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("="*70)
    
    return result_state


def test_retry_logic():
    """Test that retry logic activates when needed"""
    
    print("\n" + "="*70)
    print("🧪 TEST: RETRY LOGIC")
    print("="*70)
    
    # This test verifies that retry logic is working
    # In practice, retries happen when completeness is low
    
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
        errors=[]
    )
    
    result_state = agent_1_explore_enhanced(initial_state)
    
    attempts = result_state.get("agent_1_attempts", 0)
    retry_reasons = result_state.get("agent_1_retry_reasons", [])
    exploration_passes = result_state.get("agent_1_exploration_passes", [])
    
    print(f"\n📊 RETRY LOGIC RESULTS:")
    print(f"   Total Attempts: {attempts}")
    print(f"   Retry Reasons: {len(retry_reasons)}")
    print(f"   Exploration Passes: {len(exploration_passes)}")
    
    # Check if retry logic was used
    if attempts > 1:
        print("✅ Retry logic activated (multiple attempts)")
    else:
        print("ℹ️  Retry logic not needed (completed in first attempt)")
    
    # Check if completeness improved across attempts
    if len(exploration_passes) > 1:
        completeness_scores = [p.get("completeness_score", 0.0) for p in exploration_passes]
        print(f"\n📈 Completeness progression:")
        for i, score in enumerate(completeness_scores, 1):
            print(f"   Attempt {i}: {score:.1%}")
        
        if completeness_scores[-1] > completeness_scores[0]:
            print("✅ Completeness improved across attempts")
        else:
            print("⚠️  Completeness did not improve (may indicate issue)")
    
    print("\n" + "="*70)
    print("✅ RETRY LOGIC TEST COMPLETE")
    print("="*70)
    
    return result_state


def test_query_with_deep_dive():
    """Test on-demand deep dives for specific components"""
    
    print("\n" + "="*70)
    print("🧪 TEST: QUERY WITH ON-DEMAND DEEP DIVE")
    print("="*70)
    
    # First, run exploration
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
        errors=[]
    )
    
    # Run exploration first
    result_state = agent_1_explore_enhanced(initial_state)
    
    if not result_state.get("agent_1_enhanced_ready"):
        print("❌ Agent 1 Enhanced not ready - skipping query test")
        return
    
    # Test questions that should trigger deep dives
    test_questions = [
        "What is the formula for the first calculation?",
        "What worksheets are used in the first dashboard?",
        "What datasources does the first worksheet use?",
        "How many calculations are there in total?"
    ]
    
    print(f"\nAsking {len(test_questions)} questions that may trigger deep dives...\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n--- Test Question {i} ---")
        print(f"Question: {question}")
        answer = query_tableau_expert_enhanced(result_state, question, asking_agent="test_script")
        print(f"Answer: {answer[:300]}...")
    
    # Check conversation log
    conversations = result_state.get("agent_conversations", [])
    print(f"\n📋 Total conversations logged: {len(conversations)}")
    
    print("\n" + "="*70)
    print("✅ QUERY WITH DEEP DIVE TEST COMPLETE")
    print("="*70)
    
    return result_state


def test_manual_query_mode():
    """Test query mode works independently"""
    
    print("\n" + "="*70)
    print("🧪 TEST: MANUAL QUERY MODE")
    print("="*70)
    
    # First, run exploration
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
        errors=[]
    )
    
    # Run exploration
    result_state = agent_1_explore_enhanced(initial_state)
    
    if not result_state.get("agent_1_enhanced_ready"):
        print("❌ Agent 1 Enhanced not ready - skipping query mode test")
        return
    
    # Test various query types
    test_questions = [
        "How many worksheets are in this file?",
        "List all dashboard names",
        "What datasources are connected?",
        "Are there any calculated fields?",
        "What is the structure of the first worksheet?"
    ]
    
    print(f"\nTesting query mode with {len(test_questions)} questions...\n")
    
    all_passed = True
    for i, question in enumerate(test_questions, 1):
        print(f"Question {i}: {question}")
        answer = query_tableau_expert_enhanced(result_state, question, asking_agent="manual_test")
        
        if answer.startswith("ERROR"):
            print(f"❌ Error: {answer}")
            all_passed = False
        elif len(answer) < 10:
            print(f"⚠️  Short answer: {answer}")
        else:
            print(f"✅ Answer received: {answer[:100]}...")
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ MANUAL QUERY MODE TEST PASSED")
    else:
        print("❌ MANUAL QUERY MODE TEST FAILED")
    print("="*70)
    
    return result_state


def test_completeness_evaluation():
    """Test self-evaluation function"""
    
    print("\n" + "="*70)
    print("🧪 TEST: COMPLETENESS EVALUATION")
    print("="*70)
    
    # Create sample inventory
    sample_inventory = {
        "worksheets": [
            {"name": "Sheet 1", "id": "1", "attributes": {}},
            {"name": "Sheet 2", "id": "2", "attributes": {}}
        ],
        "dashboards": [
            {"name": "Dashboard 1", "id": "1", "attributes": {}}
        ],
        "datasources": [
            {"name": "DS 1", "attributes": {}}
        ],
        "calculations": [
            {"name": "Calc 1", "formula": "SUM([Sales])", "attributes": {}}
        ]
    }
    
    # Create sample file_json (minimal)
    sample_file_json = {
        "workbook": {
            "worksheets": {"worksheet": [{"@name": "Sheet 1"}, {"@name": "Sheet 2"}]},
            "dashboards": {"dashboard": [{"@name": "Dashboard 1"}]},
            "datasources": {"datasource": [{"@name": "DS 1"}]}
        }
    }
    
    # Test evaluation
    evaluation = _evaluate_exploration_completeness(sample_inventory, sample_file_json)
    
    print("\n📊 EVALUATION RESULTS:")
    print(f"   Completeness Score: {evaluation.get('completeness_score', 0.0):.1%}")
    print(f"   Components Found: {evaluation.get('components_found', {})}")
    print(f"   Missing Components: {evaluation.get('missing_components', [])}")
    print(f"   Confidence Indicators: {evaluation.get('confidence_indicators', {})}")
    
    # Validate evaluation structure
    required_keys = ["completeness_score", "components_found", "missing_components", "confidence_indicators"]
    all_present = all(key in evaluation for key in required_keys)
    
    if all_present:
        print("\n✅ Evaluation structure is correct")
    else:
        print("\n❌ Evaluation structure is missing keys")
    
    # Check completeness score is reasonable
    completeness = evaluation.get("completeness_score", 0.0)
    if 0.0 <= completeness <= 1.0:
        print(f"✅ Completeness score is in valid range: {completeness:.1%}")
    else:
        print(f"❌ Completeness score is out of range: {completeness}")
    
    print("\n" + "="*70)
    print("✅ COMPLETENESS EVALUATION TEST COMPLETE")
    print("="*70)
    
    return evaluation


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 TESTING AGENT 1 ENHANCED: TABLEAU DOMAIN EXPERT")
    print("="*70)
    
    # Run all tests
    print("\n" + "="*70)
    print("TEST 1: Enhanced Exploration")
    print("="*70)
    state = test_enhanced_exploration()
    
    print("\n" + "="*70)
    print("TEST 2: Retry Logic")
    print("="*70)
    test_retry_logic()
    
    if state and state.get("agent_1_enhanced_ready"):
        print("\n" + "="*70)
        print("TEST 3: Query with Deep Dive")
        print("="*70)
        test_query_with_deep_dive()
        
        print("\n" + "="*70)
        print("TEST 4: Manual Query Mode")
        print("="*70)
        test_manual_query_mode()
    
    print("\n" + "="*70)
    print("TEST 5: Completeness Evaluation")
    print("="*70)
    test_completeness_evaluation()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70)
