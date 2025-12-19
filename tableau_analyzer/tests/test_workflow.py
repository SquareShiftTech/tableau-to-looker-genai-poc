"""
Test the full conversational multi-agent workflow
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.tableau_workflow import run_tableau_workflow


def test_full_workflow():
    """Test the complete workflow: Agent 1 → Agent 2 → Agent 3"""
    
    print("\n" + "="*70)
    print("🧪 TEST: FULL CONVERSATIONAL WORKFLOW")
    print("="*70)
    
    # Path to test file (use existing file from your project)
    test_file = "../input_files/tableau/sales_summary_final.xml"
    
    print(f"📂 Test file: {test_file}")
    print("This will run:")
    print("  1. Agent 1: Explore and understand Tableau file")
    print("  2. Agent 2: Ask Agent 1 questions about complexity")
    print("  3. Agent 3: Placeholder feature extraction")
    
    # Run the complete workflow
    final_state = run_tableau_workflow(test_file, bi_tool_type="tableau")
    
    # Analyze results
    print("\n" + "="*70)
    print("📊 DETAILED TEST RESULTS")
    print("="*70)
    
    # Check for errors
    errors = final_state.get("errors", [])
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"   • {error}")
    else:
        print("\n✅ No errors - workflow executed successfully")
    
    # Agent 1 results
    print("\n1️⃣ AGENT 1 RESULTS:")
    print(f"   Ready: {final_state.get('agent_1_ready', False)}")
    inventory = final_state.get("inventory", {})
    if inventory:
        print(f"   Worksheets: {len(inventory.get('worksheets', []))}")
        print(f"   Dashboards: {len(inventory.get('dashboards', []))}")
        print(f"   Datasources: {len(inventory.get('datasources', []))}")
        print(f"   Calculations: {len(inventory.get('calculations', []))}")
    
    # Agent 2 results
    print("\n2️⃣ AGENT 2 RESULTS:")
    complexity = final_state.get("complexity_analysis", {})
    if complexity:
        print(f"   Complexity Score: {complexity.get('complexity_score', 'N/A')}")
        print(f"   Questions Asked: {len(complexity.get('questions_asked', []))}")
        print(f"   Complexity Factors: {len(complexity.get('complexity_factors', []))}")
        
        factors = complexity.get('complexity_factors', [])
        if factors:
            print("   Factors Found:")
            for factor in factors:
                print(f"      • {factor}")
        
        risks = complexity.get('migration_risks', [])
        if risks:
            print("   Migration Risks:")
            for risk in risks[:3]:  # Show first 3
                print(f"      • {risk}")
    
    # Conversations
    print("\n💬 AGENT CONVERSATIONS:")
    conversations = final_state.get("agent_conversations", [])
    print(f"   Total exchanges: {len(conversations)}")
    if conversations:
        print("   Sample conversations:")
        for i, conv in enumerate(conversations[:3], 1):  # Show first 3
            print(f"\n   {i}. {conv['from']} → {conv['to']}:")
            print(f"      Q: {conv['question'][:60]}...")
            print(f"      A: {conv['answer'][:60]}...")
    
    # Save detailed results to file
    output_file = "test_workflow_results.json"
    try:
        with open(output_file, 'w') as f:
            # Create serializable version of state
            serializable_state = {
                "bi_tool_type": final_state.get("bi_tool_type"),
                "file_path": final_state.get("file_path"),
                "agent_1_ready": final_state.get("agent_1_ready"),
                "inventory": final_state.get("inventory"),
                "complexity_analysis": final_state.get("complexity_analysis"),
                "agent_2_questions": final_state.get("agent_2_questions"),
                "agent_conversations": final_state.get("agent_conversations"),
                "errors": final_state.get("errors")
            }
            json.dump(serializable_state, f, indent=2)
        print(f"\n💾 Detailed results saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save results: {e}")
    
    print("\n" + "="*70)
    print("✅ WORKFLOW TEST COMPLETE")
    print("="*70)
    
    return final_state


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 TESTING FULL CONVERSATIONAL WORKFLOW")
    print("="*70)
    
    test_full_workflow()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70)
