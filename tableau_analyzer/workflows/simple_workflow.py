"""
Simple Workflow: Fast Complexity Analysis

Workflow: Agent 1 (Explore) → Agent 2 (Complexity) → END

This is the fast mode for quick complexity assessment.
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

from langgraph.graph import StateGraph, END

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1 import agent_1_explore
from agents.agent_2_complexity import agent_2_complexity_analyzer


def create_simple_workflow():
    """
    Create the simple workflow for fast complexity analysis
    
    Returns:
        Compiled LangGraph application
    """
    print("\n🔧 Creating Simple Workflow (Fast Mode)...")
    
    # Create the state graph
    workflow = StateGraph(AnalysisState)
    
    # Add nodes
    workflow.add_node("agent_1_explore", agent_1_explore)
    workflow.add_node("agent_2_analyze", agent_2_complexity_analyzer)
    
    # Define the workflow edges
    workflow.set_entry_point("agent_1_explore")
    workflow.add_edge("agent_1_explore", "agent_2_analyze")
    workflow.add_edge("agent_2_analyze", END)
    
    # Compile the workflow
    app = workflow.compile()
    
    print("✅ Simple workflow created")
    print("   Flow: Agent 1 (Explore) → Agent 2 (Complexity) → END")
    
    return app


def run_simple_workflow(file_path: str, bi_tool_type: str = "tableau") -> AnalysisState:
    """
    Run the simple workflow for fast complexity analysis
    
    Args:
        file_path: Path to Tableau XML file
        bi_tool_type: Type of BI tool (default: "tableau")
        
    Returns:
        Final state with complexity analysis
    """
    print("\n" + "="*70)
    print("🚀 SIMPLE WORKFLOW: FAST COMPLEXITY ANALYSIS")
    print("="*70)
    print(f"File: {file_path}")
    print(f"Mode: Simple (Fast)")
    
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
        errors=[],
        # Retry tracking
        agent_1_attempts=0,
        agent_2_attempts=0,
        agent_3_retry_count=0,
        # Extraction stats
        features_attempted=0,
        features_successful=0,
        features_failed=0,
        # Schema
        feature_schema={}
    )
    
    # Create and run workflow
    app = create_simple_workflow()
    
    print("\n" + "="*70)
    print("▶️  EXECUTING SIMPLE WORKFLOW")
    print("="*70)
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*70)
    print("✅ SIMPLE WORKFLOW COMPLETE")
    print("="*70)
    
    # Save results
    save_simple_workflow_results(final_state)
    
    # Print summary
    print_simple_workflow_summary(final_state)
    
    return final_state


def save_simple_workflow_results(state: AnalysisState) -> None:
    """
    Save simple workflow results to output folder
    
    Args:
        state: Final workflow state
    """
    output_dir = "output/tableau_analyzer"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save complexity analysis
    complexity_file = f"{output_dir}/complexity_simple_{timestamp}.json"
    print(f"\n💾 Saving complexity analysis to: {complexity_file}")
    with open(complexity_file, 'w', encoding='utf-8') as f:
        json.dump(state.get("complexity_analysis", {}), f, indent=2, ensure_ascii=False)
    
    # Save conversations
    conversations_file = f"{output_dir}/conversations_simple_{timestamp}.json"
    print(f"💾 Saving conversations to: {conversations_file}")
    with open(conversations_file, 'w', encoding='utf-8') as f:
        json.dump(state.get("agent_conversations", []), f, indent=2, ensure_ascii=False)
    
    print(f"✅ Simple workflow results saved")


def print_simple_workflow_summary(state: AnalysisState) -> None:
    """
    Print summary of simple workflow execution
    
    Args:
        state: Final workflow state
    """
    print("\n📊 SIMPLE WORKFLOW SUMMARY")
    print("="*70)
    
    # Agent 1 results
    inventory = state.get("inventory", {})
    if inventory:
        print("\n1️⃣ AGENT 1 - Tableau Understanding:")
        print(f"   Attempts: {state.get('agent_1_attempts', 1)}")
        print(f"   Worksheets: {len(inventory.get('worksheets', []))}")
        print(f"   Dashboards: {len(inventory.get('dashboards', []))}")
        print(f"   Datasources: {len(inventory.get('datasources', []))}")
        print(f"   Calculations: {len(inventory.get('calculations', []))}")
    
    # Agent 2 results
    complexity = state.get("complexity_analysis", {})
    if complexity:
        print("\n2️⃣ AGENT 2 - Complexity Analysis:")
        print(f"   Complexity Score: {complexity.get('complexity_score', 'N/A')}")
        print(f"   Questions Asked: {len(complexity.get('questions_asked', []))}")
        print(f"   Complexity Factors: {len(complexity.get('complexity_factors', []))}")
        
        retry_stats = complexity.get('retry_stats', {})
        if retry_stats:
            print(f"\n   Retry Statistics:")
            print(f"      First Try Success: {retry_stats.get('successful_first_try', 0)}")
            print(f"      Required Retry: {retry_stats.get('required_retry', 0)}")
            print(f"      Failed: {retry_stats.get('failed', 0)}")
    
    # Conversations
    conversations = state.get("agent_conversations", [])
    print(f"\n💬 Total Conversations: {len(conversations)}")
    
    # Errors
    errors = state.get("errors", [])
    if errors:
        print(f"\n❌ ERRORS: {len(errors)}")
        for error in errors:
            print(f"   • {error}")
    else:
        print("\n✅ No errors encountered")
