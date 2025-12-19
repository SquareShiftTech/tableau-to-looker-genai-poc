"""
Dashboard Sub-Agent: Specialized deep exploration of dashboards

Explores dashboards with focused JsonSpec containing only dashboard data.
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
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.settings import (
    PROJECT_ID, LOCATION, MODEL_NAME,
    AGENT_TEMPERATURE, AGENT_VERBOSE,
    MAX_ITERATIONS, MAX_EXECUTION_TIME
)


def explore_dashboards(dashboards_json: Dict[str, Any], state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Deep exploration of dashboards using focused JsonSpec
    
    Args:
        dashboards_json: Focused JSON containing only dashboards section
        state: Optional state for context
        
    Returns:
        Detailed dashboard inventory
    """
    print("\n" + "-"*70)
    print("📊 DASHBOARD SUB-AGENT: Deep Exploration")
    print("-"*70)
    
    try:
        # Create focused JsonSpec for dashboards only
        json_spec = JsonSpec(dict_=dashboards_json, max_value_length=100000)
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
            verbose=AGENT_VERBOSE,
            handle_parsing_errors=True,
            max_iterations=MAX_ITERATIONS,
            max_execution_time=MAX_EXECUTION_TIME
        )
        
        # Prompt for deep dashboard exploration
        prompt = """
You are a Tableau dashboard expert. Use your json_spec tools to explore ALL dashboards in detail.

CRITICAL OUTPUT REQUIREMENT:
- Your FINAL response MUST be ONLY the JSON object
- Do NOT include ANY explanatory text
- Start your final response with { and end with }

Extract for EACH dashboard:
1. Name (from @name, name, or @caption)
2. ID (if available)
3. Worksheets used (list of worksheet names/IDs)
4. Layout information (zones, sizes, positions)
5. Filters (dashboard-level filters)
6. Actions (dashboard actions)
7. Parameters (parameters used in dashboard)
8. All other attributes

Return ONLY this JSON structure:
{
    "dashboards": [
        {
            "name": "dashboard_name",
            "id": "...",
            "worksheets_used": ["worksheet1", "worksheet2"],
            "layout": {...},
            "filters": [...],
            "actions": [...],
            "parameters": [...],
            "attributes": {...all other attributes...}
        }
    ],
    "summary": {
        "total_dashboards": 0
    }
}
"""
        
        result = agent.invoke({"input": prompt})
        output_text = result["output"]
        
        # Parse output
        inventory = _parse_agent_output(output_text)
        
        print(f"✅ Dashboard exploration complete: {len(inventory.get('dashboards', []))} dashboards found")
        
        return inventory
        
    except Exception as e:
        error_msg = f"Dashboard sub-agent failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Try to extract JSON from error
        error_str = str(e)
        if "Could not parse LLM output:" in error_str:
            start_idx = error_str.find("Could not parse LLM output:") + len("Could not parse LLM output:")
            output_text = error_str[start_idx:].strip().strip('`').strip()
            try:
                inventory = _parse_agent_output(output_text)
                return inventory
            except:
                pass
        
        # Return empty structure on error
        return {
            "dashboards": [],
            "summary": {"total_dashboards": 0},
            "error": error_msg
        }


def _parse_agent_output(output: str) -> Dict[str, Any]:
    """Parse agent output into structured inventory"""
    try:
        # Extract JSON from response
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
        
        # Ensure required keys
        if "dashboards" not in inventory:
            inventory["dashboards"] = []
        if "summary" not in inventory:
            inventory["summary"] = {"total_dashboards": len(inventory.get("dashboards", []))}
        
        return inventory
        
    except Exception as e:
        return {
            "dashboards": [],
            "summary": {"total_dashboards": 0},
            "parse_error": str(e),
            "raw_output": output[:500]
        }
