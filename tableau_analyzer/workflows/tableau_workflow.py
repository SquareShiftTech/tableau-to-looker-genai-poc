"""
LangGraph workflow for conversational multi-agent Tableau analysis

Workflow:
1. Agent 1: Explores Tableau file and gains deep understanding
2. Agent 2: Asks Agent 1 questions about complexity
3. Agent 3: (Future) Extracts specific features
"""
import sys
from pathlib import Path

from langgraph.graph import StateGraph, END

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1 import agent_1_explore
from agents.agent_2 import agent_2_complexity_analyzer
from agents.agent_3 import agent_3_feature_extractor


def create_tableau_workflow():
    """
    Create the LangGraph workflow for Tableau analysis
    
    Returns:
        Compiled LangGraph application
    """
    print("\n🔧 Creating Tableau Analysis Workflow...")
    
    # Create the state graph
    workflow = StateGraph(AnalysisState)
    
    # Add nodes for each agent
    workflow.add_node("agent_1_explore", agent_1_explore)
    workflow.add_node("agent_2_analyze", agent_2_complexity_analyzer)
    workflow.add_node("agent_3_extract", agent_3_feature_extractor)
    
    # Define the workflow edges
    workflow.set_entry_point("agent_1_explore")
    workflow.add_edge("agent_1_explore", "agent_2_analyze")
    workflow.add_edge("agent_2_analyze", "agent_3_extract")
    workflow.add_edge("agent_3_extract", END)
    
    # Compile the workflow
    app = workflow.compile()
    
    print("✅ Workflow created successfully")
    print("\nWorkflow structure:")
    print("   START → Agent 1 (Explore) → Agent 2 (Analyze) → Agent 3 (Extract) → END")
    print("            ↑                        ↓")
    print("            └── Agent 2 queries Agent 1 ──┘")
    
    return app


def run_tableau_workflow(file_path: str, bi_tool_type: str = "tableau"):
    """
    Run the complete Tableau analysis workflow
    
    Args:
        file_path: Path to Tableau XML file
        bi_tool_type: Type of BI tool (default: "tableau")
        
    Returns:
        Final state with all analysis results
    """
    print("\n" + "="*70)
    print("🚀 STARTING TABLEAU ANALYSIS WORKFLOW")
    print("="*70)
    print(f"File: {file_path}")
    print(f"BI Tool: {bi_tool_type}")
    
    # Create initial state
    initial_state = AnalysisState(
        bi_tool_type=bi_tool_type,
        file_path=file_path,
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
    
    # Create and run workflow
    app = create_tableau_workflow()
    
    print("\n" + "="*70)
    print("▶️  EXECUTING WORKFLOW")
    print("="*70)
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*70)
    print("✅ WORKFLOW COMPLETE")
    print("="*70)
    
    # Save final results to output folder
    save_workflow_results(final_state)
    
    # Print final summary
    print_workflow_summary(final_state)
    
    return final_state


def save_workflow_results(state: AnalysisState) -> None:
    """
    Save workflow results to output folder
    
    Args:
        state: Final workflow state
    """
    import json
    import os
    from datetime import datetime
    
    output_dir = "output/tableau_analyzer"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save inventory
    inventory_file = f"{output_dir}/inventory_{timestamp}.json"
    print(f"\n💾 Saving inventory to: {inventory_file}")
    with open(inventory_file, 'w', encoding='utf-8') as f:
        json.dump(state.get("inventory", {}), f, indent=2, ensure_ascii=False)
    
    # Save complexity analysis
    complexity_file = f"{output_dir}/complexity_analysis_{timestamp}.json"
    print(f"💾 Saving complexity analysis to: {complexity_file}")
    with open(complexity_file, 'w', encoding='utf-8') as f:
        json.dump(state.get("complexity_analysis", {}), f, indent=2, ensure_ascii=False)
    
    # Save conversation log
    conversations_file = f"{output_dir}/agent_conversations_{timestamp}.json"
    print(f"💾 Saving conversations to: {conversations_file}")
    with open(conversations_file, 'w', encoding='utf-8') as f:
        json.dump(state.get("agent_conversations", []), f, indent=2, ensure_ascii=False)
    
    print(f"✅ All results saved to: {output_dir}/")
    print(f"   - Converted JSON (saved during exploration)")
    print(f"   - inventory_{timestamp}.json")
    print(f"   - complexity_analysis_{timestamp}.json")
    print(f"   - agent_conversations_{timestamp}.json")


def print_workflow_summary(state: AnalysisState) -> None:
    """
    Print a summary of the workflow execution
    
    Args:
        state: Final workflow state
    """
    print("\n📊 WORKFLOW SUMMARY")
    print("="*70)
    
    # Inventory summary
    inventory = state.get("inventory", {})
    if inventory:
        summary = inventory.get("summary", {})
        print("\n1️⃣ AGENT 1 - Tableau Understanding:")
        print(f"   ✓ Worksheets:   {summary.get('total_worksheets', len(inventory.get('worksheets', [])))}")
        print(f"   ✓ Dashboards:   {summary.get('total_dashboards', len(inventory.get('dashboards', [])))}")
        print(f"   ✓ Datasources:  {summary.get('total_datasources', len(inventory.get('datasources', [])))}")
        print(f"   ✓ Calculations: {summary.get('total_calculations', len(inventory.get('calculations', [])))}")
    
    # Complexity analysis summary
    complexity = state.get("complexity_analysis", {})
    if complexity:
        print("\n2️⃣ AGENT 2 - Complexity Analysis:")
        print(f"   ✓ Complexity Score: {complexity.get('complexity_score', 'N/A')}")
        print(f"   ✓ Factors Found: {len(complexity.get('complexity_factors', []))}")
        print(f"   ✓ Questions Asked: {len(complexity.get('questions_asked', []))}")
    
    # Conversation summary
    conversations = state.get("agent_conversations", [])
    if conversations:
        print(f"\n💬 AGENT CONVERSATIONS: {len(conversations)} exchanges")
        print("   Recent conversations:")
        for i, conv in enumerate(conversations[-3:], 1):  # Show last 3
            print(f"   {i}. {conv['from']} → {conv['to']}: {conv['question'][:50]}...")
    
    # Errors
    errors = state.get("errors", [])
    if errors:
        print(f"\n❌ ERRORS: {len(errors)}")
        for error in errors:
            print(f"   • {error}")
    else:
        print("\n✅ No errors encountered")
