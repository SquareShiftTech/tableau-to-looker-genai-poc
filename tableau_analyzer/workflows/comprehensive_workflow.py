"""
Comprehensive Workflow: Full Data Extraction

Workflow: Agent 1 (Explore) → Agent 2 (Schema) → Agent 3 (Extract) → END

This is the detailed mode for comprehensive feature extraction.
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
from agents.agent_2_schema import agent_2_schema_designer
from agents.agent_3_extractor import agent_3_data_extractor


def create_comprehensive_workflow():
    """
    Create the comprehensive workflow for detailed data extraction
    
    Returns:
        Compiled LangGraph application
    """
    print("\n🔧 Creating Comprehensive Workflow (Detailed Mode)...")
    
    # Create the state graph
    workflow = StateGraph(AnalysisState)
    
    # Add nodes
    workflow.add_node("agent_1_explore", agent_1_explore)
    workflow.add_node("agent_2_schema", agent_2_schema_designer)
    workflow.add_node("agent_3_extract", agent_3_data_extractor)
    
    # Define the workflow edges
    workflow.set_entry_point("agent_1_explore")
    workflow.add_edge("agent_1_explore", "agent_2_schema")
    workflow.add_edge("agent_2_schema", "agent_3_extract")
    workflow.add_edge("agent_3_extract", END)
    
    # Compile the workflow
    app = workflow.compile()
    
    print("✅ Comprehensive workflow created")
    print("   Flow: Agent 1 (Explore) → Agent 2 (Schema) → Agent 3 (Extract) → END")
    
    return app


def run_comprehensive_workflow(file_path: str, bi_tool_type: str = "tableau") -> AnalysisState:
    """
    Run the comprehensive workflow for full data extraction
    
    Args:
        file_path: Path to Tableau XML file
        bi_tool_type: Type of BI tool (default: "tableau")
        
    Returns:
        Final state with extracted features
    """
    print("\n" + "="*70)
    print("🚀 COMPREHENSIVE WORKFLOW: FULL DATA EXTRACTION")
    print("="*70)
    print(f"File: {file_path}")
    print(f"Mode: Comprehensive (Detailed)")
    
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
    app = create_comprehensive_workflow()
    
    print("\n" + "="*70)
    print("▶️  EXECUTING COMPREHENSIVE WORKFLOW")
    print("="*70)
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*70)
    print("✅ COMPREHENSIVE WORKFLOW COMPLETE")
    print("="*70)
    
    # Save results
    save_comprehensive_workflow_results(final_state)
    
    # Print summary
    print_comprehensive_workflow_summary(final_state)
    
    return final_state


def save_comprehensive_workflow_results(state: AnalysisState) -> None:
    """
    Save comprehensive workflow results to output folder
    
    Args:
        state: Final workflow state
    """
    output_dir = "output/tableau_analyzer"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save feature schema
    schema_file = f"{output_dir}/feature_schema_{timestamp}.json"
    print(f"\n💾 Saving feature schema to: {schema_file}")
    with open(schema_file, 'w', encoding='utf-8') as f:
        json.dump(state.get("feature_schema", {}), f, indent=2, ensure_ascii=False)
    
    # Save extracted features
    features_file = f"{output_dir}/extracted_features_{timestamp}.json"
    print(f"💾 Saving extracted features to: {features_file}")
    with open(features_file, 'w', encoding='utf-8') as f:
        json.dump(state.get("extracted_features", {}), f, indent=2, ensure_ascii=False)
    
    # Save extraction stats
    stats_file = f"{output_dir}/extraction_stats_{timestamp}.json"
    print(f"💾 Saving extraction stats to: {stats_file}")
    stats = {
        "agent_1_attempts": state.get("agent_1_attempts", 0),
        "agent_2_attempts": state.get("agent_2_attempts", 0),
        "agent_3_retry_count": state.get("agent_3_retry_count", 0),
        "features_attempted": state.get("features_attempted", 0),
        "features_successful": state.get("features_successful", 0),
        "features_failed": state.get("features_failed", 0),
        "success_rate": (state.get("features_successful", 0) / state.get("features_attempted", 1)) * 100 if state.get("features_attempted", 0) > 0 else 0
    }
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    
    # Save conversations
    conversations_file = f"{output_dir}/conversations_comprehensive_{timestamp}.json"
    print(f"💾 Saving conversations to: {conversations_file}")
    with open(conversations_file, 'w', encoding='utf-8') as f:
        json.dump(state.get("agent_conversations", []), f, indent=2, ensure_ascii=False)
    
    print(f"✅ Comprehensive workflow results saved")


def print_comprehensive_workflow_summary(state: AnalysisState) -> None:
    """
    Print summary of comprehensive workflow execution
    
    Args:
        state: Final workflow state
    """
    print("\n📊 COMPREHENSIVE WORKFLOW SUMMARY")
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
    schema = state.get("feature_schema", {})
    if schema:
        print("\n2️⃣ AGENT 2 - Schema Designer:")
        total_features = sum(len(s) for s in schema.values())
        print(f"   Total Features Defined: {total_features}")
        for comp_type, comp_schema in schema.items():
            print(f"   {comp_type}: {len(comp_schema)} features")
    
    # Agent 3 results
    features = state.get("features_attempted", 0)
    if features > 0:
        success = state.get("features_successful", 0)
        failed = state.get("features_failed", 0)
        retried = state.get("agent_3_retry_count", 0)
        success_rate = (success / features) * 100
        
        print("\n3️⃣ AGENT 3 - Data Extractor:")
        print(f"   Features Attempted: {features}")
        print(f"   Features Successful: {success} ({success_rate:.1f}%)")
        print(f"   Features Failed: {failed}")
        print(f"   Retries Used: {retried}")
    
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
