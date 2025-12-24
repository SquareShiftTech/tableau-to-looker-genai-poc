"""
Unified Tableau Workflow
Integrates XML ingestion and complexity analysis agents.

Workflow:
1. Ingestion Agent: Parse XML files and load into PostgreSQL
2. Complexity Analysis Agent: Analyze features and generate complexity report
"""

import json
from typing import TypedDict, Annotated, Dict, Any, List
import operator

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Import from existing agents (using relative imports since we're in the same directory)
from xml_to_dict_agent import (
    create_ingestion_agent,
    truncate_all_tables,
    DB_CONFIG,
    DATABASE_URL
)
from complexity_analysis_agent import (
    create_complexity_agent,
    analyze_visualization_complexity,
    analyze_calculated_field_complexity,
    analyze_dashboard_complexity
)


# ============================================================================
# UNIFIED STATE
# ============================================================================

class UnifiedWorkflowState(TypedDict):
    """State for the unified workflow combining ingestion and complexity analysis."""
    messages: Annotated[List, operator.add]
    ingestion_complete: bool
    complexity_results: Dict[str, Any]
    errors: List[str]


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def ingestion_node(state: UnifiedWorkflowState) -> UnifiedWorkflowState:
    """Node to run ingestion agent."""
    print("\n" + "=" * 60)
    print("📁 Step 1: Ingestion Agent")
    print("=" * 60)
    
    ingestion_agent = create_ingestion_agent()
    
    # Check if ingestion is already complete
    if state.get("ingestion_complete", False):
        print("✅ Ingestion already complete, skipping...")
        return {
            "messages": [HumanMessage(content="Ingestion already complete")],
            "ingestion_complete": True,
            "complexity_results": state.get("complexity_results", {}),
            "errors": state.get("errors", [])
        }
    
    # Check if we should start fresh (default is True)
    fresh_requested = not any(
        "no-fresh" in str(msg.content).lower() or "skip truncate" in str(msg.content).lower()
        for msg in state.get("messages", [])
    )
    
    # If fresh start requested, truncate tables first
    if fresh_requested:
        print("🗑️  Truncating all tables (fresh start)...")
        try:
            # truncate_all_tables is a @tool, so we need to call it via .invoke()
            truncate_result = truncate_all_tables.invoke({})
            print(f"   ✅ {truncate_result}")
        except Exception as e:
            error_msg = f"Error truncating tables: {str(e)}"
            print(f"   ⚠️  {error_msg}")
            return {
                "messages": state.get("messages", []) + [HumanMessage(content=error_msg)],
                "ingestion_complete": False,
                "complexity_results": state.get("complexity_results", {}),
                "errors": state.get("errors", []) + [error_msg]
            }
    
    # Run ingestion
    if fresh_requested:
        initial_message = "Start fresh ingestion: initialize database, convert files, ingest to tables, and show final counts."
    else:
        initial_message = "Run ingestion: initialize database if needed, convert any new files, ingest to tables, and show final counts."
    
    try:
        result = ingestion_agent.invoke({
            "messages": [HumanMessage(content=initial_message)]
        })
        
        # Check if ingestion was successful
        ingestion_success = any(
            "complete" in str(msg.content).lower() or "success" in str(msg.content).lower()
            for msg in result.get("messages", [])
        )
        
        return {
            "messages": result.get("messages", []),
            "ingestion_complete": ingestion_success,
            "complexity_results": state.get("complexity_results", {}),
            "errors": state.get("errors", [])
        }
    except Exception as e:
        error_msg = f"Ingestion error: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "messages": [HumanMessage(content=error_msg)],
            "ingestion_complete": False,
            "complexity_results": state.get("complexity_results", {}),
            "errors": state.get("errors", []) + [error_msg]
        }


def complexity_analysis_node(state: UnifiedWorkflowState) -> UnifiedWorkflowState:
    """Node to run complexity analysis agent."""
    print("\n" + "=" * 60)
    print("🔍 Step 2: Complexity Analysis Agent")
    print("=" * 60)
    
    # Check if ingestion completed successfully
    if not state.get("ingestion_complete", False):
        error_msg = "Cannot run complexity analysis: ingestion not complete"
        print(f"❌ {error_msg}")
        return {
            "messages": state.get("messages", []) + [HumanMessage(content=error_msg)],
            "ingestion_complete": state.get("ingestion_complete", False),
            "complexity_results": {},
            "errors": state.get("errors", []) + [error_msg]
        }
    
    # Run complexity analysis
    complexity_agent = create_complexity_agent()
    
    try:
        result = complexity_agent.invoke({
            "analysis_results": {},
            "messages": []
        })
        
        complexity_results = result.get("analysis_results", {})
        
        print(f"\n✅ Complexity analysis complete:")
        print(f"   - Visualizations: {len(complexity_results.get('visualization_complexity', []))}")
        print(f"   - Calculated Fields: {len(complexity_results.get('calculated_field_complexity', []))}")
        print(f"   - Dashboards/Actions: {len(complexity_results.get('dashboard_complexity', []))}")
        
        return {
            "messages": state.get("messages", []) + result.get("messages", []),
            "ingestion_complete": state.get("ingestion_complete", True),
            "complexity_results": complexity_results,
            "errors": state.get("errors", [])
        }
    except Exception as e:
        error_msg = f"Complexity analysis error: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "messages": state.get("messages", []) + [HumanMessage(content=error_msg)],
            "ingestion_complete": state.get("ingestion_complete", True),
            "complexity_results": {},
            "errors": state.get("errors", []) + [error_msg]
        }


def should_continue_after_ingestion(state: UnifiedWorkflowState) -> str:
    """Check if we should proceed to complexity analysis."""
    if state.get("ingestion_complete", False):
        return "complexity_analysis"
    return "end"


# ============================================================================
# UNIFIED WORKFLOW
# ============================================================================

def create_unified_workflow():
    """Create unified workflow combining ingestion and complexity analysis."""
    workflow = StateGraph(UnifiedWorkflowState)
    
    # Add nodes
    workflow.add_node("ingestion", ingestion_node)
    workflow.add_node("complexity_analysis", complexity_analysis_node)
    
    # Define flow
    workflow.set_entry_point("ingestion")
    workflow.add_conditional_edges(
        "ingestion",
        should_continue_after_ingestion,
        {
            "complexity_analysis": "complexity_analysis",
            "end": END
        }
    )
    workflow.add_edge("complexity_analysis", END)
    
    return workflow.compile()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point for unified workflow."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Tableau Workflow: Ingestion + Complexity Analysis")
    parser.add_argument('--no-fresh', action='store_true', help='Skip truncating tables (use existing data). By default, runs from fresh.')
    parser.add_argument('--skip-ingestion', action='store_true', help='Skip ingestion (assume data already loaded)')
    parser.add_argument('--complexity-only', action='store_true', help='Run only complexity analysis')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 Unified Tableau Workflow")
    print("=" * 60)
    print("Combining Ingestion + Complexity Analysis")
    if args.no_fresh:
        print("   (Using existing data - no truncation)")
    else:
        print("   (Starting fresh - will truncate existing tables)")
    print()
    
    workflow = create_unified_workflow()
    
    # Prepare initial state
    initial_state = {
        "messages": [],
        "ingestion_complete": args.skip_ingestion or args.complexity_only,
        "complexity_results": {},
        "errors": []
    }
    
    # By default, run from fresh (truncate tables)
    # Only add no-fresh message if explicitly requested
    if args.no_fresh:
        initial_state["messages"].append(
            HumanMessage(content="Skip truncate - use existing data")
        )
    
    # Run workflow
    result = workflow.invoke(initial_state)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"Ingestion Complete: {result.get('ingestion_complete', False)}")
    
    complexity_results = result.get("complexity_results", {})
    if complexity_results:
        print(f"\nComplexity Analysis Results:")
        print(f"  - Visualizations: {len(complexity_results.get('visualization_complexity', []))}")
        print(f"  - Calculated Fields: {len(complexity_results.get('calculated_field_complexity', []))}")
        print(f"  - Dashboards/Actions: {len(complexity_results.get('dashboard_complexity', []))}")
        
        # Save results
        output_file = "evaluations/complexity_analysis_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complexity_results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Results saved to: {output_file}")
    
    if result.get("errors"):
        print(f"\n⚠️  Errors: {len(result['errors'])}")
        for error in result["errors"]:
            print(f"   - {error}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
