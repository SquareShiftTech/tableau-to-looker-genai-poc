"""
Agent 1: Tableau Domain Expert (Queryable)

This agent has TWO modes:
1. EXPLORATION MODE: Initial deep understanding of Tableau file
2. QUERY MODE: Answer questions from other agents about the file
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
from config.settings import (
    PROJECT_ID, LOCATION, MODEL_NAME, 
    AGENT_TEMPERATURE, AGENT_VERBOSE,
    MAX_ITERATIONS, MAX_EXECUTION_TIME
)


def agent_1_explore(state: AnalysisState) -> AnalysisState:
    """
    Agent 1: EXPLORATION MODE
    
    Deep exploration of Tableau file structure.
    Uses LLM + JsonToolkit to understand the entire file.
    Stores understanding in state for future queries.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with file_json, inventory, agent_1_ready=True, json_spec
    """
    print("\n" + "="*70)
    print("🤖 AGENT 1: TABLEAU DOMAIN EXPERT (EXPLORATION MODE)")
    print("="*70)
    
    # Validate input
    bi_tool = state.get("bi_tool_type", "")
    file_path = state.get("file_path", "")
    
    print(f"📌 BI Tool Type: {bi_tool}")
    print(f"📂 File Path: {file_path}")
    
    if bi_tool != "tableau":
        error_msg = f"Agent 1 is for Tableau only. Got: {bi_tool}"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        return state
    
    try:
        # Step 1: Convert XML to JSON
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
        json_output_file = f"{output_dir}/converted_tableau_{timestamp}.json"
        
        print(f"💾 Saving converted JSON to: {json_output_file}")
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(file_json, f, indent=2, ensure_ascii=False)
        print(f"✅ Converted JSON saved successfully")
        
        # Step 2: Create JSON agent with tools
        print("\n" + "-"*70)
        print("STEP 2: CREATING AGENTIC TOOLS")
        print("-"*70)
        
        print("🔧 Initializing JsonSpec...")
        # Set very large max_value_length to load full file content
        json_spec = JsonSpec(dict_=file_json, max_value_length=100000)
        state["json_spec"] = json_spec  # Store for reuse in queries
        
        print("🔧 Creating JsonToolkit...")
        toolkit = JsonToolkit(spec=json_spec)
        
        print("🔧 Initializing Vertex AI Gemini LLM...")
        print(f"   Using Project: {PROJECT_ID}")
        print(f"   Using Model: {MODEL_NAME}")
        print(f"   Using Location: {LOCATION}")
        print(f"   Using Temperature: {AGENT_TEMPERATURE}")
        
        # Use ChatVertexAI with Vertex AI (GCP authentication, no API key needed)
        llm = ChatVertexAI(
            model_name=MODEL_NAME,
            project=PROJECT_ID,
            location=LOCATION,
            temperature=AGENT_TEMPERATURE,
        )
        
        print("🔧 Creating JSON Agent with tools...")
        agent = create_json_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=AGENT_VERBOSE,
            handle_parsing_errors=True,
            max_iterations=MAX_ITERATIONS,
            max_execution_time=MAX_EXECUTION_TIME
        )
        
        print("✅ Agent created with JSON exploration tools")
        
        # Step 3: Agent explores the file
        print("\n" + "-"*70)
        print("STEP 3: AGENT EXPLORATION & DEEP UNDERSTANDING")
        print("-"*70)
        print("🧠 Agent is now exploring the Tableau file...")
        print("    (This may take 30-60 seconds)")
        print("-"*70)
        
        prompt = create_exploration_prompt()
        
        # Agent works! Handle parsing errors gracefully
        try:
            result = agent.invoke({"input": prompt})
            output_text = result["output"]
        except Exception as e:
            # If agent executor fails due to parsing, try to extract output from error
            print(f"⚠️  Agent executor encountered parsing error (this is OK)")
            print(f"   Attempting to extract JSON from agent's response...")
            
            error_msg = str(e)
            # The error message often contains the LLM's actual output
            if "Could not parse LLM output:" in error_msg:
                # Extract the text after "Could not parse LLM output:"
                start_idx = error_msg.find("Could not parse LLM output:") + len("Could not parse LLM output:")
                output_text = error_msg[start_idx:].strip()
                # Remove backticks if present
                output_text = output_text.strip('`').strip()
            else:
                raise  # Re-raise if we can't extract the output
        
        print("-"*70)
        print("✅ Agent finished exploration")
        
        # Step 4: Parse agent's response
        print("\n" + "-"*70)
        print("STEP 4: PARSING AGENT OUTPUT")
        print("-"*70)
        
        inventory = parse_agent_output(output_text)
        state["inventory"] = inventory
        state["agent_1_ready"] = True  # Mark Agent 1 as ready for queries
        
        # Print summary
        print_inventory_summary(inventory)
        
        print("\n" + "="*70)
        print("✅ AGENT 1: EXPLORATION COMPLETE - READY FOR QUERIES")
        print("="*70)
        
    except Exception as e:
        error_msg = f"Agent 1 exploration failed: {str(e)}"
        print(f"\n❌ ERROR: {error_msg}")
        state["errors"].append(error_msg)
        
        # Set empty inventory on error
        state["inventory"] = {
            "worksheets": [],
            "dashboards": [],
            "datasources": [],
            "calculations": [],
            "error": str(e)
        }
        state["agent_1_ready"] = False
    
    return state


def query_tableau_expert(state: AnalysisState, question: str, asking_agent: str = "agent_2") -> str:
    """
    Agent 1: QUERY MODE
    
    Answer questions from other agents about the Tableau file.
    Uses the existing JsonSpec and creates an on-demand agent.
    
    Args:
        state: Current workflow state (must have json_spec and agent_1_ready=True)
        question: Question to ask Agent 1
        asking_agent: Name of the agent asking the question (for logging)
        
    Returns:
        Answer string from Agent 1
    """
    print(f"\n💬 {asking_agent.upper()} → AGENT 1: \"{question}\"")
    
    # Check if Agent 1 is ready
    if not state.get("agent_1_ready", False):
        error_msg = "Agent 1 has not completed exploration yet"
        print(f"❌ {error_msg}")
        return f"ERROR: {error_msg}"
    
    json_spec = state.get("json_spec")
    if json_spec is None:
        error_msg = "JsonSpec not found in state"
        print(f"❌ {error_msg}")
        return f"ERROR: {error_msg}"
    
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
            verbose=False,  # Less verbose for queries
            handle_parsing_errors=True,
            max_iterations=10,
            max_execution_time=60
        )
        
        # Ask the question
        prompt = create_query_prompt(question)
        
        try:
            result = agent.invoke({"input": prompt})
            answer = result["output"]
        except Exception as e:
            # If parsing fails, try to extract the actual answer
            error_msg = str(e)
            if "Could not parse LLM output:" in error_msg:
                start_idx = error_msg.find("Could not parse LLM output:") + len("Could not parse LLM output:")
                answer = error_msg[start_idx:].strip().strip('`').strip()
            else:
                # Return error message
                answer = f"Agent query failed: {str(e)}"
        
        # Log the conversation
        conversation_entry = {
            "from": asking_agent,
            "to": "agent_1",
            "question": question,
            "answer": answer
        }
        
        if "agent_conversations" not in state:
            state["agent_conversations"] = []
        state["agent_conversations"].append(conversation_entry)
        
        print(f"✅ AGENT 1 → {asking_agent.upper()}: {answer[:200]}...")
        
        return answer
        
    except Exception as e:
        error_msg = f"Query failed: {str(e)}"
        print(f"❌ {error_msg}")
        return f"ERROR: {error_msg}"


def create_exploration_prompt() -> str:
    """
    Create the prompt for the agent to explore Tableau structure
    """
    return """
You are a Tableau workbook expert analyzing a Tableau XML structure.

CRITICAL OUTPUT REQUIREMENT: 
- Your FINAL response MUST be ONLY the JSON object
- Do NOT include ANY explanatory text, preamble, or commentary
- Do NOT write "I have completed the analysis" or similar text
- Start your final response with { and end with }
- Everything between { and } must be valid JSON

Use your json_spec tools to explore and find:
1. Use json_spec_list_keys to explore the structure
2. Find ALL worksheets - look for 'worksheet' keys
3. Find ALL dashboards - look for 'dashboard' keys  
4. Find ALL datasources - look for 'datasource' keys
5. Find ALL calculated fields - look for 'column' with '@formula' or 'calculation'

Extract for each component:
- name (check '@name', 'name', or '@caption' attributes)
- id (if available)
- key attributes

Return ONLY this JSON structure (no other text):
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
    ],
    "relationships": {
        "dashboard_to_worksheets": {"dashboard_name": ["worksheet1", "worksheet2"]},
        "worksheet_to_datasources": {"worksheet_name": ["datasource1"]}
    },
    "summary": {
        "total_worksheets": 0,
        "total_dashboards": 0,
        "total_datasources": 0,
        "total_calculations": 0
    }
}
"""


def create_query_prompt(question: str) -> str:
    """
    Create a prompt for answering a specific question
    
    Args:
        question: The question from another agent
        
    Returns:
        Formatted prompt
    """
    return f"""
You are a Tableau workbook expert. Use your json_spec tools to answer this question.

Question: {question}

Use the tools to find the answer. Provide a clear, specific answer based on what you find.
Keep your answer concise and factual.
"""


def parse_agent_output(output: str) -> Dict[str, Any]:
    """
    Parse the agent's output into structured inventory
    
    Args:
        output: Agent's text output
        
    Returns:
        Structured inventory dictionary
    """
    print("📋 Parsing agent output...")
    
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
        print("✅ Successfully parsed JSON inventory")
        
        # Ensure required keys exist
        required_keys = ["worksheets", "dashboards", "datasources", "calculations"]
        for key in required_keys:
            if key not in inventory:
                inventory[key] = []
        
        return inventory
        
    except Exception as e:
        print(f"⚠️  Could not parse as JSON: {e}")
        print(f"📄 Raw output:\n{output[:500]}...")
        
        # Return fallback structure
        return {
            "worksheets": [],
            "dashboards": [],
            "datasources": [],
            "calculations": [],
            "relationships": {},
            "summary": {},
            "agent_raw_output": output,
            "parse_error": str(e)
        }


def print_inventory_summary(inventory: Dict[str, Any]) -> None:
    """
    Print a summary of the inventory
    """
    summary = inventory.get("summary", {})
    
    print("\n📊 INVENTORY SUMMARY:")
    print(f"   📄 Worksheets:   {summary.get('total_worksheets', len(inventory.get('worksheets', [])))}")
    print(f"   📊 Dashboards:   {summary.get('total_dashboards', len(inventory.get('dashboards', [])))}")
    print(f"   🗄️  Datasources:  {summary.get('total_datasources', len(inventory.get('datasources', [])))}")
    print(f"   🔢 Calculations: {summary.get('total_calculations', len(inventory.get('calculations', [])))}")
    
    if "relationships" in inventory:
        print(f"   🔗 Relationships: Found")
