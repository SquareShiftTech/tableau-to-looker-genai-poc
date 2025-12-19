# Cursor Instructions: Build Agentic Tableau Analyzer

## Project Overview
Build an agentic system using LangGraph and Vertex AI Gemini to analyze Tableau workbooks. This is a TRUE AGENTIC solution where the LLM uses tools to explore and understand files, NOT rule-based parsing.

## Critical Requirements
- ✅ Use **Vertex AI Gemini** (NOT API key, use default GCP project authentication)
- ✅ Use **LangGraph** for multi-agent orchestration
- ✅ Use **JsonToolkit** to give agent tools to explore JSON
- ✅ **Layered architecture** (config, models, agents, tools, workflows)
- ✅ **TRUE AGENTIC**: Agent uses tools to explore, NOT hardcoded parsing
- ❌ **NO rule-based if-else parsing**
- ❌ **NO hardcoded XML tag checking**

---

## Folder Structure

Create this EXACT folder structure:

```
tableau_analyzer/
│
├── config/
│   ├── __init__.py
│   └── settings.py          # Vertex AI config
│
├── models/
│   ├── __init__.py
│   └── state.py              # State definitions
│
├── agents/
│   ├── __init__.py
│   ├── agent_1.py            # Tableau Domain Expert
│   ├── agent_2.py            # (future - placeholder)
│   └── agent_3.py            # (future - placeholder)
│
├── tools/
│   ├── __init__.py
│   └── file_tools.py         # XML/JSON conversion tools
│
├── workflows/
│   ├── __init__.py
│   └── tableau_workflow.py   # LangGraph workflow (future)
│
├── tests/
│   ├── __init__.py
│   └── test_agent_1.py       # Test Agent 1
│
├── data/
│   └── sample.xml            # Test Tableau file (user provides)
│
├── main.py                   # Entry point
├── requirements.txt          # Dependencies
└── README.md                 # Documentation
```

---

## Dependencies (requirements.txt)

```txt
langgraph
langchain
langchain-google-vertexai
beautifulsoup4
xmltodict
lxml
google-cloud-aiplatform
```

---

## File Contents

### 1. `config/__init__.py`
```python
# Empty file to make it a package
```

### 2. `config/settings.py`
```python
"""
Configuration for Vertex AI and project settings
"""
import os

# Vertex AI Configuration
PROJECT_ID = "YOUR_GCP_PROJECT_ID"  # REPLACE THIS
LOCATION = "us-central1"  # or your preferred region
MODEL_NAME = "gemini-2.0-flash-exp"

# File paths
DATA_DIR = "data"
SAMPLE_FILE = "sample.xml"

# Agent settings
AGENT_TEMPERATURE = 0
AGENT_VERBOSE = True
```

### 3. `models/__init__.py`
```python
from .state import AnalysisState

__all__ = ["AnalysisState"]
```

### 4. `models/state.py`
```python
"""
State definitions for the workflow
"""
from typing import TypedDict, Dict, Any, List

class AnalysisState(TypedDict):
    """
    State that flows through all agents in the workflow
    """
    
    # Input
    bi_tool_type: str           # "tableau", "cognos", etc.
    file_path: str              # Path to the file
    
    # Agent 1 outputs
    file_json: Dict[str, Any]   # Converted JSON
    inventory: Dict[str, Any]   # Component inventory
    
    # Agent 2 outputs (future)
    complexity_rules: Dict[str, Any]
    
    # Agent 3 outputs (future)
    extracted_features: Dict[str, List[Dict]]
    
    # Metadata
    errors: List[str]           # Track any errors
```

### 5. `tools/__init__.py`
```python
from .file_tools import convert_xml_to_json

__all__ = ["convert_xml_to_json"]
```

### 6. `tools/file_tools.py`
```python
"""
File processing tools
"""
import xmltodict
from bs4 import BeautifulSoup
from typing import Dict, Any

def convert_xml_to_json(file_path: str) -> Dict[str, Any]:
    """
    Convert XML file to JSON dictionary
    
    Args:
        file_path: Path to XML file
        
    Returns:
        Dictionary representation of XML
    """
    print(f"📖 Reading XML file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    print(f"✅ Loaded {len(xml_content)} characters")
    print("🔄 Converting XML to JSON...")
    
    # Parse with BeautifulSoup then xmltodict
    text_content = str(BeautifulSoup(xml_content, "lxml"))
    file_json = xmltodict.parse(text_content)
    
    print("✅ Conversion complete")
    
    return file_json
```

### 7. `agents/__init__.py`
```python
from .agent_1 import agent_1_tableau_expert

__all__ = ["agent_1_tableau_expert"]
```

### 8. `agents/agent_1.py`

**CRITICAL: This is the main agentic component!**

```python
"""
Agent 1: Tableau Domain Expert
Uses LLM with JsonToolkit to understand Tableau structure
"""
import json
from typing import Dict, Any

from langchain_google_vertexai import ChatVertexAI
from langchain.agents import create_json_agent
from langchain.agents.agent_toolkits import JsonToolkit
from langchain.tools.json.tool import JsonSpec

from models.state import AnalysisState
from tools.file_tools import convert_xml_to_json
from config.settings import PROJECT_ID, LOCATION, MODEL_NAME, AGENT_TEMPERATURE, AGENT_VERBOSE


def agent_1_tableau_expert(state: AnalysisState) -> AnalysisState:
    """
    Agent 1: Tableau Domain Expert (AGENTIC)
    
    Uses LLM + JsonToolkit to:
    - Explore Tableau JSON structure
    - Understand component relationships
    - Extract comprehensive inventory
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with file_json and inventory
    """
    print("\n" + "="*70)
    print("🤖 AGENT 1: TABLEAU DOMAIN EXPERT (AGENTIC WITH TOOLS)")
    print("="*70)
    
    # Validate input
    bi_tool = state["bi_tool_type"]
    file_path = state["file_path"]
    
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
        
        # Step 2: Create JSON agent with tools
        print("\n" + "-"*70)
        print("STEP 2: CREATING AGENTIC TOOLS")
        print("-"*70)
        
        print("🔧 Initializing JsonSpec...")
        json_spec = JsonSpec(dict_=file_json, max_value_length=4000)
        
        print("🔧 Creating JsonToolkit...")
        toolkit = JsonToolkit(spec=json_spec)
        
        print("🔧 Initializing Vertex AI Gemini LLM...")
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
            max_iterations=15,
            max_execution_time=120
        )
        
        print("✅ Agent created with JSON exploration tools")
        
        # Step 3: Agent explores the file
        print("\n" + "-"*70)
        print("STEP 3: AGENT EXPLORATION & ANALYSIS")
        print("-"*70)
        print("🧠 Agent is now exploring the Tableau file...")
        print("    (This may take 30-60 seconds)")
        print("-"*70)
        
        prompt = create_exploration_prompt()
        
        # Agent works!
        result = agent.invoke({"input": prompt})
        
        print("-"*70)
        print("✅ Agent finished exploration")
        
        # Step 4: Parse agent's response
        print("\n" + "-"*70)
        print("STEP 4: PARSING AGENT OUTPUT")
        print("-"*70)
        
        inventory = parse_agent_output(result["output"])
        state["inventory"] = inventory
        
        # Print summary
        print_inventory_summary(inventory)
        
        print("\n" + "="*70)
        print("✅ AGENT 1: COMPLETE")
        print("="*70)
        
    except Exception as e:
        error_msg = f"Agent 1 failed: {str(e)}"
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
    
    return state


def create_exploration_prompt() -> str:
    """
    Create the prompt for the agent to explore Tableau structure
    """
    return """
You are a Tableau workbook expert. Your mission is to thoroughly analyze this Tableau XML structure.

IMPORTANT: Use your json_spec tools to navigate the JSON structure. Do not guess - explore!

Your tasks:
1. Use json_spec_list_keys to explore the structure
2. Find ALL worksheets - look for keys like 'worksheet', 'worksheets', or similar
3. Find ALL dashboards - look for keys like 'dashboard', 'dashboards'
4. Find ALL datasources - look for keys like 'datasource', 'datasources'
5. Find ALL calculated fields - look for 'column' with 'calculation' attribute or formula

For EACH component type, extract:
- name (check for 'name', '@name', or '@caption' attributes)
- id (if available)
- key attributes that define the component

Also identify relationships:
- Which worksheets are used in which dashboards
- Which datasources are used by which worksheets

Return your findings as a JSON object with this EXACT structure:
{
    "worksheets": [
        {"name": "worksheet_name", "id": "...", "attributes": {...}}
    ],
    "dashboards": [
        {"name": "dashboard_name", "id": "...", "attributes": {...}}
    ],
    "datasources": [
        {"name": "datasource_name", "connection_type": "...", "attributes": {...}}
    ],
    "calculations": [
        {"name": "calc_name", "formula": "...", "attributes": {...}}
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

BE THOROUGH! Explore the entire structure using your tools!
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
```

### 9. `tests/__init__.py`
```python
# Empty file
```

### 10. `tests/test_agent_1.py`
```python
"""
Test Agent 1: Tableau Domain Expert
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1 import agent_1_tableau_expert
from config.settings import DATA_DIR, SAMPLE_FILE


def test_agent_1():
    """Test Agent 1 with sample Tableau file"""
    
    print("🧪 TESTING AGENT 1: TABLEAU DOMAIN EXPERT")
    print("="*70)
    
    # Initial state
    initial_state: AnalysisState = {
        "bi_tool_type": "tableau",
        "file_path": f"{DATA_DIR}/{SAMPLE_FILE}",
        "file_json": {},
        "inventory": {},
        "complexity_rules": {},
        "extracted_features": {},
        "errors": []
    }
    
    print(f"📂 Testing with file: {initial_state['file_path']}")
    print("="*70)
    
    # Run Agent 1
    result_state = agent_1_tableau_expert(initial_state)
    
    # Display results
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    
    if result_state["errors"]:
        print("\n❌ ERRORS:")
        for error in result_state["errors"]:
            print(f"   - {error}")
    else:
        print("\n✅ NO ERRORS")
    
    print("\n🗂️  INVENTORY:")
    print(json.dumps(result_state["inventory"], indent=2))
    
    return result_state


if __name__ == "__main__":
    test_agent_1()
```

### 11. `main.py`
```python
"""
Main entry point for Tableau Analyzer
"""
from tests.test_agent_1 import test_agent_1

if __name__ == "__main__":
    print("🚀 Tableau Analyzer - Agentic System")
    print("="*70)
    
    # Run Agent 1 test
    test_agent_1()
```

### 12. `README.md`
```markdown
# Tableau Analyzer - Agentic System

An intelligent agent-based system for analyzing Tableau workbooks using LangGraph and Vertex AI Gemini.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure GCP authentication:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. Update `config/settings.py` with your GCP project ID

4. Place test Tableau XML file in `data/sample.xml`

## Run

```bash
python main.py
```

## Architecture

- **Layered design**: config, models, agents, tools, workflows
- **Agentic approach**: LLM uses tools to explore, not hardcoded rules
- **LangGraph**: Multi-agent orchestration (future phases)
- **Vertex AI Gemini**: LLM for reasoning and exploration
```

---

## Instructions for User

### Before running, you must:

1. **Update `config/settings.py`**:
   - Replace `YOUR_GCP_PROJECT_ID` with your actual GCP project ID

2. **Authenticate with GCP**:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Place a test Tableau XML file** in `data/sample.xml`

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Run the system:

```bash
python main.py
```

Or test Agent 1 directly:
```bash
python tests/test_agent_1.py
```

---

## What Cursor Should Do

1. Create the EXACT folder structure shown above
2. Create ALL files with the code provided
3. Make sure all `__init__.py` files are created (even if empty)
4. Ensure proper imports between modules
5. DO NOT add any rule-based parsing logic
6. DO NOT modify the agentic approach in agent_1.py
7. Keep the layered architecture intact

---

## Expected Output

When running successfully, you should see:

```
🤖 AGENT 1: TABLEAU DOMAIN EXPERT (AGENTIC WITH TOOLS)
======================================================================

STEP 1: FILE CONVERSION
----------------------------------------------------------------------
📖 Reading XML file: data/sample.xml
✅ Loaded XXXXX characters
🔄 Converting XML to JSON...
✅ Conversion complete

STEP 2: CREATING AGENTIC TOOLS
----------------------------------------------------------------------
🔧 Initializing JsonSpec...
🔧 Creating JsonToolkit...
🔧 Initializing Vertex AI Gemini LLM...
🔧 Creating JSON Agent with tools...
✅ Agent created with JSON exploration tools

STEP 3: AGENT EXPLORATION & ANALYSIS
----------------------------------------------------------------------
🧠 Agent is now exploring the Tableau file...
    (This may take 30-60 seconds)
----------------------------------------------------------------------

> Entering new AgentExecutor chain...
[Agent uses tools to explore JSON structure]

----------------------------------------------------------------------
✅ Agent finished exploration

STEP 4: PARSING AGENT OUTPUT
----------------------------------------------------------------------
📋 Parsing agent output...
✅ Successfully parsed JSON inventory

📊 INVENTORY SUMMARY:
   📄 Worksheets:   X
   📊 Dashboards:   X
   🗄️  Datasources:  X
   🔢 Calculations: X
   🔗 Relationships: Found

======================================================================
✅ AGENT 1: COMPLETE
======================================================================
```

---

## Key Principles

✅ **Agentic = LLM + Tools**
✅ **Agent explores using JsonToolkit**
✅ **NO hardcoded if-else parsing**
✅ **Layered, modular architecture**
✅ **Vertex AI with default GCP auth**
✅ **Extensible for future agents**