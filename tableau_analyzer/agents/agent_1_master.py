"""
Master Agent: Quick discovery, component extraction, and delegation to sub-agents

Master-Worker Architecture:
- Master: Quick discovery and coordination
- Sub-Agents: Deep exploration of specific component types
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any

from langchain_google_vertexai import ChatVertexAI
from langchain_community.agent_toolkits.json.base import create_json_agent
from langchain_community.agent_toolkits import JsonToolkit
from langchain_community.tools.json.tool import JsonSpec

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from tools.file_tools import convert_xml_to_json
from tools.component_extractor import (
    build_component_index,
    extract_all_component_sections
)
from agents.sub_agents import (
    explore_worksheets,
    explore_dashboards,
    explore_datasources,
    explore_calculations
)
from config.settings import (
    PROJECT_ID, LOCATION, MODEL_NAME,
    AGENT_TEMPERATURE, AGENT_VERBOSE,
    MAX_ITERATIONS, MAX_EXECUTION_TIME
)


def master_agent_explore(state: AnalysisState) -> AnalysisState:
    """
    Master Agent: Quick discovery + delegation to sub-agents
    
    Workflow:
    1. Quick structure discovery (5-10s)
    2. Component extraction (< 1s)
    3. Sub-agent creation and delegation (10-20s per sub-agent)
    4. Result aggregation (< 1s)
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with comprehensive inventory from sub-agents
    """
    print("\n" + "="*70)
    print("🎯 MASTER AGENT: Quick Discovery + Delegation")
    print("="*70)
    
    # Validate input
    bi_tool = state.get("bi_tool_type", "")
    file_path = state.get("file_path", "")
    
    print(f"📌 BI Tool Type: {bi_tool}")
    print(f"📂 File Path: {file_path}")
    
    if bi_tool != "tableau":
        error_msg = f"Master Agent is for Tableau only. Got: {bi_tool}"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        return state
    
    # Initialize master-worker state
    state["master_ready"] = False
    state["sub_agents_ready"] = {}
    state["component_index"] = None
    state["sub_agent_results"] = {}
    state["sub_agent_specs"] = {}
    
    try:
        # Step 1: Convert XML to JSON (if not already done)
        if "file_json" not in state or not state.get("file_json"):
            print("\n" + "-"*70)
            print("STEP 1: FILE CONVERSION")
            print("-"*70)
            
            file_json = convert_xml_to_json(file_path)
            state["file_json"] = file_json
            
            # Save converted JSON
            from datetime import datetime
            import os
            output_dir = "output/tableau_analyzer"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_output_file = f"{output_dir}/converted_tableau_master_{timestamp}.json"
            
            print(f"💾 Saving converted JSON to: {json_output_file}")
            with open(json_output_file, 'w', encoding='utf-8') as f:
                json.dump(file_json, f, indent=2, ensure_ascii=False)
            print(f"✅ Converted JSON saved successfully")
        else:
            file_json = state["file_json"]
            print("✅ Using existing file_json from state")
        
        # Step 2: Quick Structure Discovery (5-10s)
        print("\n" + "-"*70)
        print("STEP 2: QUICK STRUCTURE DISCOVERY")
        print("-"*70)
        print("🔍 Building component index...")
        
        component_index = build_component_index(file_json)
        state["component_index"] = component_index
        
        print("✅ Component Index Created:")
        print(f"   📄 Worksheets:   {component_index['worksheets']['count']}")
        print(f"   📊 Dashboards:   {component_index['dashboards']['count']}")
        print(f"   🗄️  Datasources:  {component_index['datasources']['count']}")
        print(f"   🔢 Calculations: {component_index['calculations']['count']}")
        
        # Step 3: Extract Component Sections (< 1s)
        print("\n" + "-"*70)
        print("STEP 3: EXTRACTING COMPONENT SECTIONS")
        print("-"*70)
        
        component_sections = extract_all_component_sections(file_json)
        print("✅ Component sections extracted")
        
        # Step 4: Create Sub-Agents and Delegate (10-20s per sub-agent)
        print("\n" + "="*70)
        print("STEP 4: SUB-AGENT CREATION & DELEGATION")
        print("="*70)
        
        sub_agent_results = {}
        sub_agent_specs = {}
        
        # Worksheet Sub-Agent
        if component_index["worksheets"]["count"] > 0:
            print("\n📄 Delegating to Worksheet Sub-Agent...")
            try:
                worksheets_result = explore_worksheets(component_sections["worksheets"], state)
                sub_agent_results["worksheets"] = worksheets_result
                state["sub_agents_ready"]["worksheets"] = True
                print("✅ Worksheet Sub-Agent completed")
            except Exception as e:
                print(f"❌ Worksheet Sub-Agent failed: {e}")
                sub_agent_results["worksheets"] = {"worksheets": [], "error": str(e)}
                state["sub_agents_ready"]["worksheets"] = False
        else:
            print("⏭️  Skipping Worksheet Sub-Agent (no worksheets found)")
            sub_agent_results["worksheets"] = {"worksheets": []}
            state["sub_agents_ready"]["worksheets"] = True
        
        # Dashboard Sub-Agent
        if component_index["dashboards"]["count"] > 0:
            print("\n📊 Delegating to Dashboard Sub-Agent...")
            try:
                dashboards_result = explore_dashboards(component_sections["dashboards"], state)
                sub_agent_results["dashboards"] = dashboards_result
                state["sub_agents_ready"]["dashboards"] = True
                print("✅ Dashboard Sub-Agent completed")
            except Exception as e:
                print(f"❌ Dashboard Sub-Agent failed: {e}")
                sub_agent_results["dashboards"] = {"dashboards": [], "error": str(e)}
                state["sub_agents_ready"]["dashboards"] = False
        else:
            print("⏭️  Skipping Dashboard Sub-Agent (no dashboards found)")
            sub_agent_results["dashboards"] = {"dashboards": []}
            state["sub_agents_ready"]["dashboards"] = True
        
        # Datasource Sub-Agent
        if component_index["datasources"]["count"] > 0:
            print("\n🗄️  Delegating to Datasource Sub-Agent...")
            try:
                datasources_result = explore_datasources(component_sections["datasources"], state)
                sub_agent_results["datasources"] = datasources_result
                state["sub_agents_ready"]["datasources"] = True
                print("✅ Datasource Sub-Agent completed")
            except Exception as e:
                print(f"❌ Datasource Sub-Agent failed: {e}")
                sub_agent_results["datasources"] = {"datasources": [], "error": str(e)}
                state["sub_agents_ready"]["datasources"] = False
        else:
            print("⏭️  Skipping Datasource Sub-Agent (no datasources found)")
            sub_agent_results["datasources"] = {"datasources": []}
            state["sub_agents_ready"]["datasources"] = True
        
        # Calculation Sub-Agent
        if component_index["calculations"]["count"] > 0:
            print("\n🔢 Delegating to Calculation Sub-Agent...")
            try:
                calculations_result = explore_calculations(component_sections["calculations"], state)
                sub_agent_results["calculations"] = calculations_result
                state["sub_agents_ready"]["calculations"] = True
                print("✅ Calculation Sub-Agent completed")
            except Exception as e:
                print(f"❌ Calculation Sub-Agent failed: {e}")
                sub_agent_results["calculations"] = {"calculations": [], "error": str(e)}
                state["sub_agents_ready"]["calculations"] = False
        else:
            print("⏭️  Skipping Calculation Sub-Agent (no calculations found)")
            sub_agent_results["calculations"] = {"calculations": []}
            state["sub_agents_ready"]["calculations"] = True
        
        state["sub_agent_results"] = sub_agent_results
        
        # Step 5: Aggregate Results (< 1s)
        print("\n" + "-"*70)
        print("STEP 5: AGGREGATING RESULTS")
        print("-"*70)
        
        final_inventory = _aggregate_sub_agent_results(sub_agent_results, component_index)
        state["inventory"] = final_inventory
        state["master_ready"] = True
        
        # Create JsonSpecs for query routing
        for component_type in ["worksheets", "dashboards", "datasources", "calculations"]:
            if component_type in component_sections:
                spec = JsonSpec(dict_=component_sections[component_type], max_value_length=100000)
                sub_agent_specs[component_type] = spec
        
        state["sub_agent_specs"] = sub_agent_specs
        
        # Also create full JsonSpec for backward compatibility
        state["json_spec"] = JsonSpec(dict_=file_json, max_value_length=100000)
        state["agent_1_ready"] = True  # For backward compatibility
        
        # Print summary
        print("\n" + "="*70)
        print("📊 FINAL INVENTORY SUMMARY")
        print("="*70)
        _print_inventory_summary(final_inventory)
        print("="*70)
        print("✅ MASTER AGENT: EXPLORATION COMPLETE")
        print("="*70)
        
    except Exception as e:
        error_msg = f"Master agent exploration failed: {str(e)}"
        print(f"\n❌ ERROR: {error_msg}")
        state["errors"].append(error_msg)
        state["master_ready"] = False
        
        state["inventory"] = {
            "worksheets": [],
            "dashboards": [],
            "datasources": [],
            "calculations": [],
            "error": str(e)
        }
    
    return state


def _aggregate_sub_agent_results(
    sub_agent_results: Dict[str, Dict[str, Any]],
    component_index: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Aggregate results from all sub-agents into unified inventory
    
    Args:
        sub_agent_results: Results from each sub-agent
        component_index: Component index for summary
        
    Returns:
        Unified inventory
    """
    inventory = {
        "worksheets": [],
        "dashboards": [],
        "datasources": [],
        "calculations": [],
        "relationships": {},
        "summary": {}
    }
    
    # Aggregate worksheets
    if "worksheets" in sub_agent_results:
        worksheets_data = sub_agent_results["worksheets"]
        inventory["worksheets"] = worksheets_data.get("worksheets", [])
    
    # Aggregate dashboards
    if "dashboards" in sub_agent_results:
        dashboards_data = sub_agent_results["dashboards"]
        inventory["dashboards"] = dashboards_data.get("dashboards", [])
    
    # Aggregate datasources
    if "datasources" in sub_agent_results:
        datasources_data = sub_agent_results["datasources"]
        inventory["datasources"] = datasources_data.get("datasources", [])
    
    # Aggregate calculations
    if "calculations" in sub_agent_results:
        calculations_data = sub_agent_results["calculations"]
        inventory["calculations"] = calculations_data.get("calculations", [])
    
    # Build relationships
    relationships = {}
    
    # Dashboard to worksheets
    dashboard_to_worksheets = {}
    for dashboard in inventory["dashboards"]:
        dashboard_name = dashboard.get("name", "Unknown")
        worksheets_used = dashboard.get("worksheets_used", [])
        if worksheets_used:
            dashboard_to_worksheets[dashboard_name] = worksheets_used
    relationships["dashboard_to_worksheets"] = dashboard_to_worksheets
    
    # Worksheet to datasources (if available in worksheet data)
    worksheet_to_datasources = {}
    for worksheet in inventory["worksheets"]:
        worksheet_name = worksheet.get("name", "Unknown")
        datasources = worksheet.get("datasources", [])
        if datasources:
            worksheet_to_datasources[worksheet_name] = datasources
    relationships["worksheet_to_datasources"] = worksheet_to_datasources
    
    # Calculation to datasource
    calculation_to_datasource = {}
    for calculation in inventory["calculations"]:
        calc_name = calculation.get("name", "Unknown")
        datasource = calculation.get("datasource", "Unknown")
        calculation_to_datasource[calc_name] = datasource
    relationships["calculation_to_datasource"] = calculation_to_datasource
    
    inventory["relationships"] = relationships
    
    # Build summary
    inventory["summary"] = {
        "total_worksheets": len(inventory["worksheets"]),
        "total_dashboards": len(inventory["dashboards"]),
        "total_datasources": len(inventory["datasources"]),
        "total_calculations": len(inventory["calculations"])
    }
    
    return inventory


def _print_inventory_summary(inventory: Dict[str, Any]) -> None:
    """Print a summary of the inventory"""
    summary = inventory.get("summary", {})
    
    print(f"   📄 Worksheets:   {summary.get('total_worksheets', len(inventory.get('worksheets', [])))}")
    print(f"   📊 Dashboards:   {summary.get('total_dashboards', len(inventory.get('dashboards', [])))}")
    print(f"   🗄️  Datasources:  {summary.get('total_datasources', len(inventory.get('datasources', [])))}")
    print(f"   🔢 Calculations: {summary.get('total_calculations', len(inventory.get('calculations', [])))}")
    
    if "relationships" in inventory:
        print(f"   🔗 Relationships: Found")


def master_agent_query(state: AnalysisState, question: str, asking_agent: str = "manual") -> str:
    """
    Master Agent: Query routing and coordination
    
    Routes queries to appropriate sub-agents or answers from index.
    
    Args:
        state: Current workflow state
        question: Question to answer
        asking_agent: Name of agent asking the question
        
    Returns:
        Answer string
    """
    from agents.query_router import route_query, answer_from_index
    
    print(f"\n💬 {asking_agent.upper()} → MASTER AGENT: \"{question}\"")
    
    if not state.get("master_ready", False):
        error_msg = "Master agent has not completed exploration yet"
        print(f"❌ {error_msg}")
        return f"ERROR: {error_msg}"
    
    # Route the query
    target_agent_type, direct_answer = route_query(question, state)
    
    # If direct answer available, return it
    if direct_answer:
        print(f"✅ Answered from index: {direct_answer}")
        return direct_answer
    
    # Route to appropriate sub-agent
    if target_agent_type == "worksheet":
        return _query_worksheet_sub_agent(state, question, asking_agent)
    elif target_agent_type == "dashboard":
        return _query_dashboard_sub_agent(state, question, asking_agent)
    elif target_agent_type == "datasource":
        return _query_datasource_sub_agent(state, question, asking_agent)
    elif target_agent_type == "calculation":
        return _query_calculation_sub_agent(state, question, asking_agent)
    else:
        # Default: use full JsonSpec for complex queries
        return _query_with_full_spec(state, question, asking_agent)


def _query_worksheet_sub_agent(state: AnalysisState, question: str, asking_agent: str) -> str:
    """Query worksheet sub-agent"""
    from langchain_google_vertexai import ChatVertexAI
    from langchain_community.agent_toolkits.json.base import create_json_agent
    from langchain_community.agent_toolkits import JsonToolkit
    
    sub_agent_specs = state.get("sub_agent_specs", {})
    if "worksheets" not in sub_agent_specs:
        return "ERROR: Worksheet sub-agent not available"
    
    try:
        toolkit = JsonToolkit(spec=sub_agent_specs["worksheets"])
        llm = ChatVertexAI(model_name=MODEL_NAME, project=PROJECT_ID, location=LOCATION, temperature=AGENT_TEMPERATURE)
        agent = create_json_agent(llm=llm, toolkit=toolkit, verbose=False, handle_parsing_errors=True, max_iterations=10, max_execution_time=60)
        
        prompt = f"Use your json_spec tools to answer this question about worksheets: {question}\n\nProvide a clear, specific answer."
        result = agent.invoke({"input": prompt})
        answer = result["output"]
        
        # Log conversation
        if "agent_conversations" not in state:
            state["agent_conversations"] = []
        state["agent_conversations"].append({
            "from": asking_agent,
            "to": "worksheet_sub_agent",
            "question": question,
            "answer": answer
        })
        
        return answer
    except Exception as e:
        return f"ERROR: Worksheet query failed: {str(e)}"


def _query_dashboard_sub_agent(state: AnalysisState, question: str, asking_agent: str) -> str:
    """Query dashboard sub-agent"""
    from langchain_google_vertexai import ChatVertexAI
    from langchain_community.agent_toolkits.json.base import create_json_agent
    from langchain_community.agent_toolkits import JsonToolkit
    
    sub_agent_specs = state.get("sub_agent_specs", {})
    if "dashboards" not in sub_agent_specs:
        return "ERROR: Dashboard sub-agent not available"
    
    try:
        toolkit = JsonToolkit(spec=sub_agent_specs["dashboards"])
        llm = ChatVertexAI(model_name=MODEL_NAME, project=PROJECT_ID, location=LOCATION, temperature=AGENT_TEMPERATURE)
        agent = create_json_agent(llm=llm, toolkit=toolkit, verbose=False, handle_parsing_errors=True, max_iterations=10, max_execution_time=60)
        
        prompt = f"Use your json_spec tools to answer this question about dashboards: {question}\n\nProvide a clear, specific answer."
        result = agent.invoke({"input": prompt})
        answer = result["output"]
        
        # Log conversation
        if "agent_conversations" not in state:
            state["agent_conversations"] = []
        state["agent_conversations"].append({
            "from": asking_agent,
            "to": "dashboard_sub_agent",
            "question": question,
            "answer": answer
        })
        
        return answer
    except Exception as e:
        return f"ERROR: Dashboard query failed: {str(e)}"


def _query_datasource_sub_agent(state: AnalysisState, question: str, asking_agent: str) -> str:
    """Query datasource sub-agent"""
    from langchain_google_vertexai import ChatVertexAI
    from langchain_community.agent_toolkits.json.base import create_json_agent
    from langchain_community.agent_toolkits import JsonToolkit
    
    sub_agent_specs = state.get("sub_agent_specs", {})
    if "datasources" not in sub_agent_specs:
        return "ERROR: Datasource sub-agent not available"
    
    try:
        toolkit = JsonToolkit(spec=sub_agent_specs["datasources"])
        llm = ChatVertexAI(model_name=MODEL_NAME, project=PROJECT_ID, location=LOCATION, temperature=AGENT_TEMPERATURE)
        agent = create_json_agent(llm=llm, toolkit=toolkit, verbose=False, handle_parsing_errors=True, max_iterations=10, max_execution_time=60)
        
        prompt = f"Use your json_spec tools to answer this question about datasources: {question}\n\nProvide a clear, specific answer."
        result = agent.invoke({"input": prompt})
        answer = result["output"]
        
        # Log conversation
        if "agent_conversations" not in state:
            state["agent_conversations"] = []
        state["agent_conversations"].append({
            "from": asking_agent,
            "to": "datasource_sub_agent",
            "question": question,
            "answer": answer
        })
        
        return answer
    except Exception as e:
        return f"ERROR: Datasource query failed: {str(e)}"


def _query_calculation_sub_agent(state: AnalysisState, question: str, asking_agent: str) -> str:
    """Query calculation sub-agent"""
    from langchain_google_vertexai import ChatVertexAI
    from langchain_community.agent_toolkits.json.base import create_json_agent
    from langchain_community.agent_toolkits import JsonToolkit
    
    sub_agent_specs = state.get("sub_agent_specs", {})
    if "calculations" not in sub_agent_specs:
        return "ERROR: Calculation sub-agent not available"
    
    try:
        toolkit = JsonToolkit(spec=sub_agent_specs["calculations"])
        llm = ChatVertexAI(model_name=MODEL_NAME, project=PROJECT_ID, location=LOCATION, temperature=AGENT_TEMPERATURE)
        agent = create_json_agent(llm=llm, toolkit=toolkit, verbose=False, handle_parsing_errors=True, max_iterations=10, max_execution_time=60)
        
        prompt = f"Use your json_spec tools to answer this question about calculations: {question}\n\nProvide a clear, specific answer."
        result = agent.invoke({"input": prompt})
        answer = result["output"]
        
        # Log conversation
        if "agent_conversations" not in state:
            state["agent_conversations"] = []
        state["agent_conversations"].append({
            "from": asking_agent,
            "to": "calculation_sub_agent",
            "question": question,
            "answer": answer
        })
        
        return answer
    except Exception as e:
        return f"ERROR: Calculation query failed: {str(e)}"


def _query_with_full_spec(state: AnalysisState, question: str, asking_agent: str) -> str:
    """Query using full JsonSpec for complex cross-component queries"""
    from langchain_google_vertexai import ChatVertexAI
    from langchain_community.agent_toolkits.json.base import create_json_agent
    from langchain_community.agent_toolkits import JsonToolkit
    
    json_spec = state.get("json_spec")
    if not json_spec:
        return "ERROR: JsonSpec not available"
    
    try:
        toolkit = JsonToolkit(spec=json_spec)
        llm = ChatVertexAI(model_name=MODEL_NAME, project=PROJECT_ID, location=LOCATION, temperature=AGENT_TEMPERATURE)
        agent = create_json_agent(llm=llm, toolkit=toolkit, verbose=False, handle_parsing_errors=True, max_iterations=10, max_execution_time=60)
        
        prompt = f"Use your json_spec tools to answer this question: {question}\n\nProvide a clear, specific answer."
        result = agent.invoke({"input": prompt})
        answer = result["output"]
        
        # Log conversation
        if "agent_conversations" not in state:
            state["agent_conversations"] = []
        state["agent_conversations"].append({
            "from": asking_agent,
            "to": "master_agent",
            "question": question,
            "answer": answer
        })
        
        return answer
    except Exception as e:
        return f"ERROR: Query failed: {str(e)}"
