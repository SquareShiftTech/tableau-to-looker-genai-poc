"""
Agent 1 Enhanced: Tableau Domain Expert with Retry Logic and Multi-Pass Exploration

This enhanced agent has THREE modes:
1. EXPLORATION MODE: Multi-pass deep understanding with retry logic
2. QUERY MODE: Answer questions with on-demand deep dives
3. SELF-EVALUATION: Assess completeness and trigger retries if needed
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from langchain_google_vertexai import ChatVertexAI
from langchain_community.agent_toolkits.json.base import create_json_agent
from langchain_community.agent_toolkits import JsonToolkit
from langchain_community.tools.json.tool import JsonSpec

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from tools.file_tools import convert_xml_to_json
from config.settings import (
    PROJECT_ID, LOCATION, MODEL_NAME, 
    AGENT_TEMPERATURE, AGENT_VERBOSE,
    MAX_ITERATIONS, MAX_EXECUTION_TIME
)

# Constants
MAX_RETRY_ATTEMPTS = 3
COMPLETENESS_THRESHOLD = 0.80  # 80% completeness required


def agent_1_explore_enhanced(state: AnalysisState) -> AnalysisState:
    """
    Agent 1 Enhanced: EXPLORATION MODE with Multi-Pass and Retry Logic
    
    Performs 3-pass exploration:
    1. High-level structure discovery
    2. Component enumeration
    3. Deep attribute extraction
    
    With retry logic if completeness is insufficient.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with comprehensive inventory and exploration metadata
    """
    print("\n" + "="*70)
    print("🤖 AGENT 1 ENHANCED: TABLEAU DOMAIN EXPERT (MULTI-PASS EXPLORATION)")
    print("="*70)
    
    # Validate input
    bi_tool = state.get("bi_tool_type", "")
    file_path = state.get("file_path", "")
    
    print(f"📌 BI Tool Type: {bi_tool}")
    print(f"📂 File Path: {file_path}")
    
    if bi_tool != "tableau":
        error_msg = f"Agent 1 Enhanced is for Tableau only. Got: {bi_tool}"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        return state
    
    # Initialize retry tracking
    state["agent_1_attempts"] = 0
    state["agent_1_retry_reasons"] = []
    state["agent_1_exploration_passes"] = []
    state["agent_1_enhanced_ready"] = False
    
    try:
        # Step 1: Convert XML to JSON (if not already done)
        if "file_json" not in state or not state.get("file_json"):
            print("\n" + "-"*70)
            print("STEP 1: FILE CONVERSION")
            print("-"*70)
            
            file_json = convert_xml_to_json(file_path)
            state["file_json"] = file_json
            
            # Save converted JSON to output folder
            from datetime import datetime
            import os
            output_dir = "output/tableau_analyzer"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_output_file = f"{output_dir}/converted_tableau_enhanced_{timestamp}.json"
            
            print(f"💾 Saving converted JSON to: {json_output_file}")
            with open(json_output_file, 'w', encoding='utf-8') as f:
                json.dump(file_json, f, indent=2, ensure_ascii=False)
            print(f"✅ Converted JSON saved successfully")
        else:
            file_json = state["file_json"]
            print("✅ Using existing file_json from state")
        
        # Step 2: Create JSON agent tools
        print("\n" + "-"*70)
        print("STEP 2: CREATING AGENTIC TOOLS")
        print("-"*70)
        
        print("🔧 Initializing JsonSpec...")
        json_spec = JsonSpec(dict_=file_json, max_value_length=100000)
        state["json_spec"] = json_spec
        
        print("🔧 Creating JsonToolkit...")
        toolkit = JsonToolkit(spec=json_spec)
        
        print("🔧 Initializing Vertex AI Gemini LLM...")
        print(f"   Using Project: {PROJECT_ID}")
        print(f"   Using Model: {MODEL_NAME}")
        print(f"   Using Location: {LOCATION}")
        print(f"   Using Temperature: {AGENT_TEMPERATURE}")
        
        llm = ChatVertexAI(
            model_name=MODEL_NAME,
            project=PROJECT_ID,
            location=LOCATION,
            temperature=AGENT_TEMPERATURE,
        )
        
        print("✅ Agent tools created")
        
        # Step 3: Multi-pass exploration with retry logic
        print("\n" + "="*70)
        print("STEP 3: MULTI-PASS EXPLORATION WITH RETRY LOGIC")
        print("="*70)
        
        best_inventory = None
        best_completeness = 0.0
        
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            state["agent_1_attempts"] = attempt
            print(f"\n🔄 EXPLORATION ATTEMPT {attempt}/{MAX_RETRY_ATTEMPTS}")
            print("-"*70)
            
            # Create agent for this attempt
            agent = create_json_agent(
                llm=llm,
                toolkit=toolkit,
                verbose=AGENT_VERBOSE,
                handle_parsing_errors=True,
                max_iterations=MAX_ITERATIONS,
                max_execution_time=MAX_EXECUTION_TIME
            )
            
            # Perform 3-pass exploration
            inventory = _perform_multi_pass_exploration(
                agent, file_json, attempt, state.get("agent_1_retry_reasons", [])
            )
            
            # Evaluate completeness
            evaluation = _evaluate_exploration_completeness(inventory, file_json)
            completeness_score = evaluation.get("completeness_score", 0.0)
            
            print(f"\n📊 Completeness Score: {completeness_score:.1%}")
            print(f"   Components Found: {evaluation.get('components_found', {})}")
            
            # Store pass results
            pass_result = {
                "attempt": attempt,
                "inventory": inventory,
                "completeness_score": completeness_score,
                "evaluation": evaluation
            }
            state["agent_1_exploration_passes"].append(pass_result)
            
            # Track best result
            if completeness_score > best_completeness:
                best_completeness = completeness_score
                best_inventory = inventory
            
            # Check if we should retry
            if completeness_score >= COMPLETENESS_THRESHOLD:
                print(f"✅ Completeness threshold met ({COMPLETENESS_THRESHOLD:.0%})")
                break
            elif attempt < MAX_RETRY_ATTEMPTS:
                retry_reason = f"Completeness {completeness_score:.1%} below threshold {COMPLETENESS_THRESHOLD:.0%}. Missing: {evaluation.get('missing_components', [])}"
                state["agent_1_retry_reasons"].append(retry_reason)
                print(f"⚠️  {retry_reason}")
                print(f"🔄 Retrying with refined approach...")
            else:
                print(f"⚠️  Maximum attempts reached. Using best result (completeness: {best_completeness:.1%})")
        
        # Store final results
        state["inventory"] = best_inventory or inventory
        state["agent_1_completeness_score"] = best_completeness
        state["agent_1_enhanced_ready"] = True
        
        # Print summary
        print("\n" + "="*70)
        print("📊 FINAL EXPLORATION SUMMARY")
        print("="*70)
        print_inventory_summary(state["inventory"])
        print(f"📈 Completeness: {best_completeness:.1%}")
        print(f"🔄 Attempts: {state['agent_1_attempts']}")
        if state["agent_1_retry_reasons"]:
            print(f"⚠️  Retry Reasons:")
            for reason in state["agent_1_retry_reasons"]:
                print(f"   • {reason}")
        print("="*70)
        print("✅ AGENT 1 ENHANCED: EXPLORATION COMPLETE - READY FOR QUERIES")
        print("="*70)
        
    except Exception as e:
        error_msg = f"Agent 1 Enhanced exploration failed: {str(e)}"
        print(f"\n❌ ERROR: {error_msg}")
        state["errors"].append(error_msg)
        
        state["inventory"] = {
            "worksheets": [],
            "dashboards": [],
            "datasources": [],
            "calculations": [],
            "error": str(e)
        }
        state["agent_1_enhanced_ready"] = False
    
    return state


def _perform_multi_pass_exploration(
    agent: Any, 
    file_json: Dict[str, Any], 
    attempt: int,
    previous_retry_reasons: List[str]
) -> Dict[str, Any]:
    """
    Perform 3-pass exploration of the Tableau file
    
    Args:
        agent: The JSON agent to use
        file_json: The JSON representation of the file
        attempt: Current attempt number
        previous_retry_reasons: Reasons from previous attempts
        
    Returns:
        Combined inventory from all passes
    """
    print("\n" + "-"*70)
    print("MULTI-PASS EXPLORATION")
    print("-"*70)
    
    all_inventory = {
        "worksheets": [],
        "dashboards": [],
        "datasources": [],
        "calculations": [],
        "relationships": {},
        "summary": {}
    }
    
    # Pass 1: High-level structure discovery
    print("\n📋 PASS 1: High-Level Structure Discovery")
    print("-"*70)
    prompt_1 = _create_pass_1_prompt(attempt, previous_retry_reasons)
    pass_1_result = _invoke_agent_safely(agent, prompt_1)
    pass_1_inventory = parse_agent_output(pass_1_result)
    
    # Merge Pass 1 results
    all_inventory["worksheets"].extend(pass_1_inventory.get("worksheets", []))
    all_inventory["dashboards"].extend(pass_1_inventory.get("dashboards", []))
    all_inventory["datasources"].extend(pass_1_inventory.get("datasources", []))
    all_inventory["calculations"].extend(pass_1_inventory.get("calculations", []))
    
    print(f"✅ Pass 1: Found {len(pass_1_inventory.get('worksheets', []))} worksheets, "
          f"{len(pass_1_inventory.get('dashboards', []))} dashboards, "
          f"{len(pass_1_inventory.get('datasources', []))} datasources")
    
    # Pass 2: Component enumeration
    print("\n📋 PASS 2: Component Enumeration")
    print("-"*70)
    prompt_2 = _create_pass_2_prompt(pass_1_inventory, attempt, previous_retry_reasons)
    pass_2_result = _invoke_agent_safely(agent, prompt_2)
    pass_2_inventory = parse_agent_output(pass_2_result)
    
    # Merge Pass 2 results (deduplicate by name)
    _merge_inventory(all_inventory, pass_2_inventory)
    
    print(f"✅ Pass 2: Updated counts - "
          f"{len(all_inventory.get('worksheets', []))} worksheets, "
          f"{len(all_inventory.get('dashboards', []))} dashboards, "
          f"{len(all_inventory.get('datasources', []))} datasources, "
          f"{len(all_inventory.get('calculations', []))} calculations")
    
    # Pass 3: Deep attribute extraction
    print("\n📋 PASS 3: Deep Attribute Extraction")
    print("-"*70)
    prompt_3 = _create_pass_3_prompt(all_inventory, attempt, previous_retry_reasons)
    pass_3_result = _invoke_agent_safely(agent, prompt_3)
    pass_3_inventory = parse_agent_output(pass_3_result)
    
    # Merge Pass 3 results (enrich existing entries)
    _merge_inventory(all_inventory, pass_3_inventory, enrich=True)
    
    # Update relationships
    if "relationships" in pass_3_inventory:
        all_inventory["relationships"] = pass_3_inventory.get("relationships", {})
    
    # Calculate summary
    all_inventory["summary"] = {
        "total_worksheets": len(all_inventory.get("worksheets", [])),
        "total_dashboards": len(all_inventory.get("dashboards", [])),
        "total_datasources": len(all_inventory.get("datasources", [])),
        "total_calculations": len(all_inventory.get("calculations", []))
    }
    
    print(f"✅ Pass 3: Final counts - "
          f"{all_inventory['summary']['total_worksheets']} worksheets, "
          f"{all_inventory['summary']['total_dashboards']} dashboards, "
          f"{all_inventory['summary']['total_datasources']} datasources, "
          f"{all_inventory['summary']['total_calculations']} calculations")
    
    return all_inventory


def _merge_inventory(
    target: Dict[str, Any], 
    source: Dict[str, Any], 
    enrich: bool = False
) -> None:
    """
    Merge source inventory into target, deduplicating by name
    
    Args:
        target: Target inventory to merge into
        source: Source inventory to merge from
        enrich: If True, enrich existing entries; if False, only add new ones
    """
    for component_type in ["worksheets", "dashboards", "datasources", "calculations"]:
        existing_names = {item.get("name") for item in target.get(component_type, []) if item.get("name")}
        
        for item in source.get(component_type, []):
            item_name = item.get("name")
            if not item_name:
                # Add items without names
                target[component_type].append(item)
            elif item_name not in existing_names:
                # New item
                target[component_type].append(item)
                existing_names.add(item_name)
            elif enrich:
                # Enrich existing item
                for existing_item in target[component_type]:
                    if existing_item.get("name") == item_name:
                        # Merge attributes
                        existing_item.update(item)
                        break


def _invoke_agent_safely(agent: Any, prompt: str) -> str:
    """
    Safely invoke agent and extract output, handling parsing errors
    
    Args:
        agent: The agent to invoke
        prompt: The prompt to send
        
    Returns:
        Extracted output text
    """
    try:
        result = agent.invoke({"input": prompt})
        return result["output"]
    except Exception as e:
        error_msg = str(e)
        if "Could not parse LLM output:" in error_msg:
            start_idx = error_msg.find("Could not parse LLM output:") + len("Could not parse LLM output:")
            output_text = error_msg[start_idx:].strip().strip('`').strip()
            return output_text
        else:
            # Return error message wrapped in JSON-like structure
            return f'{{"error": "{str(e)}"}}'


def _create_pass_1_prompt(attempt: int, retry_reasons: List[str]) -> str:
    """Create prompt for Pass 1: High-level structure discovery"""
    base_prompt = """
You are a Tableau workbook expert analyzing a Tableau XML structure.

CRITICAL OUTPUT REQUIREMENT: 
- Your FINAL response MUST be ONLY the JSON object
- Do NOT include ANY explanatory text, preamble, or commentary
- Start your final response with { and end with }
- Everything between { and } must be valid JSON

PASS 1: HIGH-LEVEL STRUCTURE DISCOVERY

Use your json_spec tools to explore the top-level structure:
1. Use json_spec_list_keys to explore the root structure
2. Find where worksheets are stored (look for 'worksheet', 'worksheets', 'worksheet' keys)
3. Find where dashboards are stored (look for 'dashboard', 'dashboards' keys)
4. Find where datasources are stored (look for 'datasource', 'datasources' keys)
5. Find where calculations are stored (look for 'column' with '@formula', 'calculation', 'calculated-field' keys)

For this pass, focus on DISCOVERY - find the structure and location of each component type.
Extract basic information: name (from '@name', 'name', or '@caption'), and id if available.

Return ONLY this JSON structure (no other text):
{
    "worksheets": [
        {"name": "worksheet_name", "id": "...", "attributes": {}}
    ],
    "dashboards": [
        {"name": "dashboard_name", "id": "...", "attributes": {}}
    ],
    "datasources": [
        {"name": "datasource_name", "attributes": {}}
    ],
    "calculations": [
        {"name": "calc_name", "attributes": {}}
    ]
}
"""
    
    if attempt > 1 and retry_reasons:
        base_prompt += f"\n\nRETRY CONTEXT (Attempt {attempt}):\n"
        base_prompt += "Previous attempts missed some components. Be thorough and explore ALL branches of the JSON structure.\n"
        base_prompt += "Previous issues:\n"
        for reason in retry_reasons:
            base_prompt += f"- {reason}\n"
    
    return base_prompt


def _create_pass_2_prompt(
    pass_1_inventory: Dict[str, Any], 
    attempt: int, 
    retry_reasons: List[str]
) -> str:
    """Create prompt for Pass 2: Component enumeration"""
    base_prompt = """
You are a Tableau workbook expert analyzing a Tableau XML structure.

CRITICAL OUTPUT REQUIREMENT: 
- Your FINAL response MUST be ONLY the JSON object
- Do NOT include ANY explanatory text
- Start your final response with { and end with }

PASS 2: COMPONENT ENUMERATION

From Pass 1, we found:
"""
    
    base_prompt += f"- Worksheets: {len(pass_1_inventory.get('worksheets', []))}\n"
    base_prompt += f"- Dashboards: {len(pass_1_inventory.get('dashboards', []))}\n"
    base_prompt += f"- Datasources: {len(pass_1_inventory.get('datasources', []))}\n"
    base_prompt += f"- Calculations: {len(pass_1_inventory.get('calculations', []))}\n"
    
    base_prompt += """
Now, ENUMERATE ALL INSTANCES of each component type. Be exhaustive:
1. For worksheets: Find ALL worksheets, even nested ones
2. For dashboards: Find ALL dashboards, check all dashboard sections
3. For datasources: Find ALL datasources, including embedded and published ones
4. For calculations: Find ALL calculated fields, including those in different datasources

Extract: name, id, and basic attributes for each.

Return ONLY this JSON structure:
{
    "worksheets": [
        {"name": "worksheet_name", "id": "...", "attributes": {...}}
    ],
    "dashboards": [
        {"name": "dashboard_name", "id": "...", "worksheets_used": [...], "attributes": {...}}
    ],
    "datasources": [
        {"name": "datasource_name", "connection_type": "...", "attributes": {...}}
    ],
    "calculations": [
        {"name": "calc_name", "formula": "...", "datasource": "...", "attributes": {...}}
    ]
}
"""
    
    if attempt > 1:
        base_prompt += "\n\nRETRY: Be more thorough. Check ALL branches, nested structures, and alternative locations.\n"
    
    return base_prompt


def _create_pass_3_prompt(
    current_inventory: Dict[str, Any], 
    attempt: int, 
    retry_reasons: List[str]
) -> str:
    """Create prompt for Pass 3: Deep attribute extraction"""
    base_prompt = """
You are a Tableau workbook expert analyzing a Tableau XML structure.

CRITICAL OUTPUT REQUIREMENT: 
- Your FINAL response MUST be ONLY the JSON object
- Do NOT include ANY explanatory text
- Start your final response with { and end with }

PASS 3: DEEP ATTRIBUTE EXTRACTION

Current inventory:
"""
    
    base_prompt += f"- Worksheets: {len(current_inventory.get('worksheets', []))}\n"
    base_prompt += f"- Dashboards: {len(current_inventory.get('dashboards', []))}\n"
    base_prompt += f"- Datasources: {len(current_inventory.get('datasources', []))}\n"
    base_prompt += f"- Calculations: {len(current_inventory.get('calculations', []))}\n"
    
    base_prompt += """
Now, extract DEEP ATTRIBUTES for each component:
1. For worksheets: Extract all visualizations, filters, parameters used, data fields
2. For dashboards: Extract which worksheets are used, layout, filters, actions
3. For datasources: Extract connection details, tables, joins, custom SQL
4. For calculations: Extract full formulas, dependencies, data types

Also map relationships:
- Which dashboards use which worksheets
- Which worksheets use which datasources
- Which calculations belong to which datasources

Return ONLY this JSON structure:
{
    "worksheets": [
        {"name": "...", "id": "...", "attributes": {...all attributes...}, "filters": [...], "parameters": [...]}
    ],
    "dashboards": [
        {"name": "...", "id": "...", "worksheets_used": [...], "attributes": {...all attributes...}}
    ],
    "datasources": [
        {"name": "...", "connection_type": "...", "attributes": {...all attributes...}, "tables": [...], "joins": [...]}
    ],
    "calculations": [
        {"name": "...", "formula": "...full formula...", "datasource": "...", "attributes": {...all attributes...}}
    ],
    "relationships": {
        "dashboard_to_worksheets": {"dashboard_name": ["worksheet1", "worksheet2"]},
        "worksheet_to_datasources": {"worksheet_name": ["datasource1"]},
        "calculation_to_datasource": {"calculation_name": "datasource_name"}
    },
    "summary": {
        "total_worksheets": 0,
        "total_dashboards": 0,
        "total_datasources": 0,
        "total_calculations": 0
    }
}
"""
    
    return base_prompt


def _evaluate_exploration_completeness(
    inventory: Dict[str, Any], 
    file_json: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate the completeness of the exploration
    
    Args:
        inventory: The inventory to evaluate
        file_json: The full JSON file for reference
        
    Returns:
        Evaluation dictionary with completeness score and details
    """
    evaluation = {
        "completeness_score": 0.0,
        "components_found": {},
        "missing_components": [],
        "confidence_indicators": {}
    }
    
    # Count components found
    worksheets_count = len(inventory.get("worksheets", []))
    dashboards_count = len(inventory.get("dashboards", []))
    datasources_count = len(inventory.get("datasources", []))
    calculations_count = len(inventory.get("calculations", []))
    
    evaluation["components_found"] = {
        "worksheets": worksheets_count,
        "dashboards": dashboards_count,
        "datasources": datasources_count,
        "calculations": calculations_count
    }
    
    # Check for expected patterns in file_json (heuristic)
    file_json_str = json.dumps(file_json).lower()
    
    # Heuristic: count occurrences of key terms
    worksheet_indicators = file_json_str.count("worksheet")
    dashboard_indicators = file_json_str.count("dashboard")
    datasource_indicators = file_json_str.count("datasource")
    calculation_indicators = file_json_str.count("@formula") + file_json_str.count("calculation")
    
    # Calculate completeness (simple heuristic)
    # If we found components and there are indicators, that's good
    # If indicators exist but we found 0, that's bad
    
    scores = []
    
    # Worksheets score
    if worksheet_indicators > 0:
        if worksheets_count > 0:
            scores.append(min(1.0, worksheets_count / max(1, worksheet_indicators / 10)))
        else:
            scores.append(0.0)
            evaluation["missing_components"].append("worksheets")
    else:
        scores.append(1.0 if worksheets_count == 0 else 0.8)
    
    # Dashboards score
    if dashboard_indicators > 0:
        if dashboards_count > 0:
            scores.append(min(1.0, dashboards_count / max(1, dashboard_indicators / 5)))
        else:
            scores.append(0.0)
            evaluation["missing_components"].append("dashboards")
    else:
        scores.append(1.0 if dashboards_count == 0 else 0.8)
    
    # Datasources score
    if datasource_indicators > 0:
        if datasources_count > 0:
            scores.append(min(1.0, datasources_count / max(1, datasource_indicators / 5)))
        else:
            scores.append(0.0)
            evaluation["missing_components"].append("datasources")
    else:
        scores.append(1.0 if datasources_count == 0 else 0.8)
    
    # Calculations score
    if calculation_indicators > 0:
        if calculations_count > 0:
            scores.append(min(1.0, calculations_count / max(1, calculation_indicators / 2)))
        else:
            scores.append(0.0)
            evaluation["missing_components"].append("calculations")
    else:
        scores.append(1.0 if calculations_count == 0 else 0.8)
    
    # Check attribute completeness
    attribute_scores = []
    for worksheet in inventory.get("worksheets", []):
        if worksheet.get("name"):
            attribute_scores.append(1.0)
        else:
            attribute_scores.append(0.5)
    
    for dashboard in inventory.get("dashboards", []):
        if dashboard.get("name"):
            attribute_scores.append(1.0)
        else:
            attribute_scores.append(0.5)
    
    # Overall completeness score
    if scores:
        base_score = sum(scores) / len(scores)
    else:
        base_score = 0.0
    
    # Adjust based on attribute completeness
    if attribute_scores:
        attr_score = sum(attribute_scores) / len(attribute_scores)
        evaluation["completeness_score"] = (base_score * 0.7) + (attr_score * 0.3)
    else:
        evaluation["completeness_score"] = base_score
    
    evaluation["confidence_indicators"] = {
        "worksheet_indicators": worksheet_indicators,
        "dashboard_indicators": dashboard_indicators,
        "datasource_indicators": datasource_indicators,
        "calculation_indicators": calculation_indicators
    }
    
    return evaluation


def query_tableau_expert_enhanced(
    state: AnalysisState, 
    question: str, 
    asking_agent: str = "manual"
) -> str:
    """
    Agent 1 Enhanced: QUERY MODE with On-Demand Deep Dives
    
    Answer questions with automatic deep dives if needed.
    If question references a specific component that's missing or incomplete,
    performs targeted exploration before answering.
    
    Args:
        state: Current workflow state (must have json_spec and agent_1_enhanced_ready=True)
        question: Question to ask Agent 1
        asking_agent: Name of the agent asking the question
        
    Returns:
        Answer string from Agent 1
    """
    print(f"\n💬 {asking_agent.upper()} → AGENT 1 ENHANCED: \"{question}\"")
    
    # Check if Agent 1 Enhanced is ready
    if not state.get("agent_1_enhanced_ready", False):
        error_msg = "Agent 1 Enhanced has not completed exploration yet"
        print(f"❌ {error_msg}")
        return f"ERROR: {error_msg}"
    
    json_spec = state.get("json_spec")
    if json_spec is None:
        error_msg = "JsonSpec not found in state"
        print(f"❌ {error_msg}")
        return f"ERROR: {error_msg}"
    
    inventory = state.get("inventory", {})
    
    # Check if question references specific components that might need deep dive
    question_lower = question.lower()
    needs_deep_dive = False
    target_component = None
    
    # Check for component references
    for worksheet in inventory.get("worksheets", []):
        if worksheet.get("name") and worksheet.get("name").lower() in question_lower:
            needs_deep_dive = True
            target_component = ("worksheet", worksheet.get("name"))
            break
    
    for calculation in inventory.get("calculations", []):
        if calculation.get("name") and calculation.get("name").lower() in question_lower:
            # Check if calculation has formula
            if not calculation.get("formula") or len(calculation.get("formula", "")) < 10:
                needs_deep_dive = True
                target_component = ("calculation", calculation.get("name"))
                break
    
    if needs_deep_dive and target_component:
        print(f"🔍 Performing on-demand deep dive for {target_component[0]}: {target_component[1]}")
        _perform_targeted_exploration(state, target_component[0], target_component[1])
    
    try:
        # Create toolkit and agent for this query
        toolkit = JsonToolkit(spec=json_spec)
        
        llm = ChatVertexAI(
            model_name=MODEL_NAME,
            project=PROJECT_ID,
            location=LOCATION,
            temperature=AGENT_TEMPERATURE,
        )
        
        agent = create_json_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=10,
            max_execution_time=60
        )
        
        # Ask the question with retry logic
        max_query_retries = 2
        answer = None
        
        for query_attempt in range(1, max_query_retries + 1):
            prompt = _create_enhanced_query_prompt(question, inventory, query_attempt)
            
            try:
                result = agent.invoke({"input": prompt})
                answer = result["output"]
                
                # Check if answer is satisfactory (not an error)
                if answer and not answer.startswith("ERROR") and len(answer) > 10:
                    break
            except Exception as e:
                error_msg = str(e)
                if "Could not parse LLM output:" in error_msg:
                    start_idx = error_msg.find("Could not parse LLM output:") + len("Could not parse LLM output:")
                    answer = error_msg[start_idx:].strip().strip('`').strip()
                    if answer and len(answer) > 10:
                        break
                else:
                    answer = f"Query failed (attempt {query_attempt}): {str(e)}"
        
        if not answer or len(answer) < 10:
            answer = "Unable to find answer in the Tableau file structure."
        
        # Log the conversation
        conversation_entry = {
            "from": asking_agent,
            "to": "agent_1_enhanced",
            "question": question,
            "answer": answer
        }
        
        if "agent_conversations" not in state:
            state["agent_conversations"] = []
        state["agent_conversations"].append(conversation_entry)
        
        print(f"✅ AGENT 1 ENHANCED → {asking_agent.upper()}: {answer[:200]}...")
        
        return answer
        
    except Exception as e:
        error_msg = f"Query failed: {str(e)}"
        print(f"❌ {error_msg}")
        return f"ERROR: {error_msg}"


def _perform_targeted_exploration(
    state: AnalysisState, 
    component_type: str, 
    component_name: str
) -> None:
    """
    Perform targeted exploration for a specific component
    
    Args:
        state: Current workflow state
        component_type: Type of component ("worksheet", "calculation", etc.)
        component_name: Name of the component
    """
    json_spec = state.get("json_spec")
    if not json_spec:
        return
    
    toolkit = JsonToolkit(spec=json_spec)
    
    llm = ChatVertexAI(
        model_name=MODEL_NAME,
        project=PROJECT_ID,
        location=LOCATION,
        temperature=AGENT_TEMPERATURE,
    )
    
    agent = create_json_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=5,
        max_execution_time=30
    )
    
    prompt = f"""
Use your json_spec tools to find detailed information about this {component_type}: "{component_name}".

Extract ALL attributes, formulas, relationships, and nested structures for this specific component.
Return a detailed JSON object with all information found.
"""
    
    try:
        result = agent.invoke({"input": prompt})
        output = result["output"]
        
        # Try to parse and merge into inventory
        try:
            detailed_info = json.loads(output)
            # Update inventory with detailed info
            inventory = state.get("inventory", {})
            component_list = inventory.get(f"{component_type}s", [])
            
            for item in component_list:
                if item.get("name") == component_name:
                    item.update(detailed_info)
                    break
        except:
            pass  # If parsing fails, continue with original inventory
    except:
        pass  # If exploration fails, continue with original inventory


def _create_enhanced_query_prompt(
    question: str, 
    inventory: Dict[str, Any], 
    attempt: int = 1
) -> str:
    """Create an enhanced query prompt with context"""
    base_prompt = f"""
You are a Tableau workbook expert. Use your json_spec tools to answer this question.

Question: {question}

Current inventory context:
- Worksheets: {len(inventory.get('worksheets', []))}
- Dashboards: {len(inventory.get('dashboards', []))}
- Datasources: {len(inventory.get('datasources', []))}
- Calculations: {len(inventory.get('calculations', []))}

Use the tools to find the answer. Provide a clear, specific answer based on what you find.
Keep your answer concise and factual. If you cannot find the answer, say so clearly.
"""
    
    if attempt > 1:
        base_prompt += "\n\nThis is a retry attempt. Be more thorough in your exploration.\n"
    
    return base_prompt


def parse_agent_output(output: str) -> Dict[str, Any]:
    """
    Parse the agent's output into structured inventory
    
    Args:
        output: Agent's text output
        
    Returns:
        Structured inventory dictionary
    """
    try:
        # Try to extract JSON from response
        if "```json" in output:
            json_start = output.find("```json") + 7
            json_end = output.find("```", json_start)
            json_text = output[json_start:json_end].strip()
        elif "{" in output:
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            json_text = output[json_start:json_end]
        else:
            raise ValueError("No JSON found in output")
        
        inventory = json.loads(json_text)
        
        # Ensure required keys exist
        required_keys = ["worksheets", "dashboards", "datasources", "calculations"]
        for key in required_keys:
            if key not in inventory:
                inventory[key] = []
        
        return inventory
        
    except Exception as e:
        # Return fallback structure
        return {
            "worksheets": [],
            "dashboards": [],
            "datasources": [],
            "calculations": [],
            "relationships": {},
            "summary": {},
            "agent_raw_output": output[:500],
            "parse_error": str(e)
        }


def print_inventory_summary(inventory: Dict[str, Any]) -> None:
    """Print a summary of the inventory"""
    summary = inventory.get("summary", {})
    
    print("\n📊 INVENTORY SUMMARY:")
    print(f"   📄 Worksheets:   {summary.get('total_worksheets', len(inventory.get('worksheets', [])))}")
    print(f"   📊 Dashboards:   {summary.get('total_dashboards', len(inventory.get('dashboards', [])))}")
    print(f"   🗄️  Datasources:  {summary.get('total_datasources', len(inventory.get('datasources', [])))}")
    print(f"   🔢 Calculations: {summary.get('total_calculations', len(inventory.get('calculations', [])))}")
    
    if "relationships" in inventory:
        print(f"   🔗 Relationships: Found")
