"""
Calculation Sub-Agent: Specialized deep exploration of calculations

Explores calculations extracted from datasources.
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


def explore_calculations(calculations_json: Dict[str, Any], state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Deep exploration of calculations using focused JsonSpec
    
    Args:
        calculations_json: Focused JSON containing calculations section
        state: Optional state for context
        
    Returns:
        Detailed calculation inventory
    """
    print("\n" + "-"*70)
    print("🔢 CALCULATION SUB-AGENT: Deep Exploration")
    print("-"*70)
    
    try:
        # Create focused JsonSpec for calculations only
        json_spec = JsonSpec(dict_=calculations_json, max_value_length=100000)
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
        
        # Prompt for deep calculation exploration
        prompt = """
You are a Tableau calculation expert. Use your json_spec tools to explore ALL calculations in detail.

CRITICAL OUTPUT REQUIREMENT:
- Your FINAL response MUST be ONLY the JSON object
- Do NOT include ANY explanatory text
- Start your final response with { and end with }

Extract for EACH calculation:
1. Name (calculation field name)
2. Formula (full calculation formula)
3. Datasource (which datasource it belongs to)
4. Data type (string, number, date, etc.)
5. Aggregation (if any aggregation is applied)
6. Dependencies (other fields/calculations used in formula)
7. All other attributes

Return ONLY this JSON structure:
{
    "calculations": [
        {
            "name": "calculation_name",
            "formula": "full formula here",
            "datasource": "datasource_name",
            "data_type": "string",
            "aggregation": "...",
            "dependencies": [...],
            "attributes": {...all other attributes...}
        }
    ],
    "summary": {
        "total_calculations": 0
    }
}
"""
        
        result = agent.invoke({"input": prompt})
        output_text = result["output"]
        
        # Parse output
        inventory = _parse_agent_output(output_text)
        
        print(f"✅ Calculation exploration complete: {len(inventory.get('calculations', []))} calculations found")
        
        return inventory
        
    except Exception as e:
        error_msg = f"Calculation sub-agent failed: {str(e)}"
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
            "calculations": [],
            "summary": {"total_calculations": 0},
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
        if "calculations" not in inventory:
            inventory["calculations"] = []
        if "summary" not in inventory:
            inventory["summary"] = {"total_calculations": len(inventory.get("calculations", []))}
        
        return inventory
        
    except Exception as e:
        return {
            "calculations": [],
            "summary": {"total_calculations": 0},
            "parse_error": str(e),
            "raw_output": output[:500]
        }
