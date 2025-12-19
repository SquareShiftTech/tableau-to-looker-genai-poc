# Tableau Analyzer - Conversational Multi-Agent System

An intelligent conversational agent-based system for analyzing Tableau workbooks using LangGraph and Vertex AI Gemini.

## Overview

This is a **TRUE AGENTIC** system that demonstrates a novel conversational architecture:

- **Agent 1 (Tableau Expert)**: Deeply understands Tableau files and can answer questions
- **Agent 2 (Complexity Analyzer)**: Asks Agent 1 questions to assess migration complexity
- **Agent 3 (Feature Extractor)**: Future - will query Agent 1 for specific features

### Key Innovation: Conversational Agents

Unlike traditional rule-based parsing, agents **converse** with each other:

```
Agent 2: "What calculated fields use LOD expressions?"
Agent 1: [Uses tools to explore] "Found 3 LOD calculations: Sales by Region (FIXED), ..."
Agent 2: [Analyzes answer] "High complexity detected"
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Tableau XML File                      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │   Agent 1: Tableau  │
            │   Domain Expert     │
            │                     │
            │  • Explores file    │
            │  • Gains deep       │
            │    understanding    │
            │  • Answers queries  │
            └─────────┬───────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │Agent 2 │  │Agent 3 │  │Future  │
    │Asks Q's│  │Asks Q's│  │Agents  │
    └────────┘  └────────┘  └────────┘
```

## Setup

### Prerequisites

1. **Python 3.10+**
2. **Google Cloud Project** with Vertex AI API enabled
3. **GCP Authentication** configured

### Installation

1. **Install dependencies** (from project root):
   ```bash
   cd c:\squareshift\tableau-looker-vibe\prompt\tableau-to-looker-genai-poc
   uv pip install -e .
   ```

   Or with pip:
   ```bash
   pip install -e .
   ```

2. **Configure GCP Authentication**:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Update Configuration**:
   
   Edit `tableau_analyzer/config/settings.py`:
   ```python
   PROJECT_ID = "your-gcp-project-id"  # Replace this
   LOCATION = "us-central1"             # Or your preferred region
   MODEL_NAME = "gemini-2.0-flash-exp"  # Or available Gemini model
   ```

   Or set environment variable:
   ```bash
   export GCP_PROJECT_ID="your-gcp-project-id"
   ```

4. **Prepare Test File**:
   
   Ensure a Tableau XML file exists at:
   ```
   input_files/tableau/sales_summary_final.xml
   ```

## Usage

### Run the Full Workflow

From the project root:

```bash
python -m tableau_analyzer.main
```

Or from within `tableau_analyzer/`:

```bash
cd tableau_analyzer
python main.py
```

### Run Individual Tests

**Test Agent 1 only** (exploration + query modes):
```bash
cd tableau_analyzer
python tests/test_agent_1.py
```

**Test full workflow** (all agents):
```bash
cd tableau_analyzer
python tests/test_workflow.py
```

## What Happens When You Run It

### Phase 1: Agent 1 Exploration
```
🤖 AGENT 1: TABLEAU DOMAIN EXPERT (EXPLORATION MODE)
======================================================================

STEP 1: FILE CONVERSION
----------------------------------------------------------------------
📖 Reading XML file: ../input_files/tableau/sales_summary_final.xml
✅ Loaded 45,327 characters
🔄 Converting XML to JSON...
✅ Conversion complete

STEP 2: CREATING AGENTIC TOOLS
----------------------------------------------------------------------
🔧 Initializing JsonSpec...
🔧 Creating JsonToolkit...
🔧 Initializing Vertex AI Gemini LLM...
🔧 Creating JSON Agent with tools...
✅ Agent created with JSON exploration tools

STEP 3: AGENT EXPLORATION & DEEP UNDERSTANDING
----------------------------------------------------------------------
🧠 Agent is now exploring the Tableau file...
    (This may take 30-60 seconds)
----------------------------------------------------------------------

> Entering new AgentExecutor chain...
[Agent uses json_spec_list_keys, json_spec_get_value to navigate structure]

----------------------------------------------------------------------
✅ Agent finished exploration

STEP 4: PARSING AGENT OUTPUT
----------------------------------------------------------------------
📋 Parsing agent output...
✅ Successfully parsed JSON inventory

📊 INVENTORY SUMMARY:
   📄 Worksheets:   5
   📊 Dashboards:   2
   🗄️  Datasources:  3
   🔢 Calculations: 12
   🔗 Relationships: Found

======================================================================
✅ AGENT 1: EXPLORATION COMPLETE - READY FOR QUERIES
======================================================================
```

### Phase 2: Agent 2 Questions Agent 1
```
🔍 AGENT 2: COMPLEXITY ANALYZER
======================================================================
✅ Agent 1 is ready - beginning complexity analysis

----------------------------------------------------------------------
STEP 1: ASKING AGENT 1 TARGETED QUESTIONS
----------------------------------------------------------------------

Question 1/5
💬 AGENT_2 → AGENT 1: "What calculated fields use Level of Detail (LOD) expressions?"
✅ AGENT 1 → AGENT_2: Found 3 calculated fields using LOD expressions: [Sales by Region (FIXED), ...]

Question 2/5
💬 AGENT_2 → AGENT 1: "Which worksheets have the most complex filter combinations?"
✅ AGENT 1 → AGENT_2: The worksheet 'Sales Analysis' has 5 interactive filters...

----------------------------------------------------------------------
STEP 2: CALCULATING COMPLEXITY SCORE
----------------------------------------------------------------------

📊 COMPLEXITY ANALYSIS SUMMARY:
   🎯 Complexity Score: HIGH
   📋 Questions Asked: 5
   ⚠️  Complexity Factors: 4

   Factors Found:
      • LOD expressions detected
      • Complex filtering detected
      • Data blending/joins detected
      • Interactive dashboard elements

   🚨 Migration Risks:
      • LOD expressions require careful translation to Looker
      • Complex filters may need redesign in Looker
      • Data relationships need careful mapping to Looker
      • Dashboard interactivity needs recreation in Looker

======================================================================
✅ AGENT 2: COMPLEXITY ANALYSIS COMPLETE
======================================================================
```

### Phase 3: Conversation Log
```
💬 AGENT CONVERSATIONS: 5 exchanges
   Recent conversations:
   1. agent_2 → agent_1: What calculated fields use Level of Detail (LOD)...
   2. agent_2 → agent_1: Which worksheets have the most complex filter com...
   3. agent_2 → agent_1: Are there any nested calculations (calculations r...
```

## Key Features

### Agent 1: Queryable Expert

Agent 1 has **two modes**:

1. **Exploration Mode**: `agent_1_explore(state)`
   - Deeply explores Tableau file structure
   - Uses JsonToolkit to navigate JSON
   - Stores complete understanding
   - Sets `agent_1_ready = True`

2. **Query Mode**: `query_tableau_expert(state, question)`
   - Answers questions from other agents
   - Uses existing understanding
   - Logs all conversations
   - Returns specific answers

### Agent 2: Complexity Analyzer

Asks intelligent questions like:
- "What calculated fields use LOD expressions?"
- "Which worksheets have complex filters?"
- "Are there nested calculations?"
- "What data blending patterns are used?"
- "Which dashboards have interactive elements?"

Then analyzes answers to calculate:
- Complexity Score: LOW / MEDIUM / HIGH / CRITICAL
- Complexity Factors
- Migration Risks

### LangGraph Workflow

Orchestrates the conversation:

```python
START → Agent 1 (Explore) → Agent 2 (Analyze) → Agent 3 (Extract) → END
         ↑                        ↓
         └── Agent 2 queries Agent 1 ──┘
```

## Comparison with Traditional Parsing

| Aspect | Traditional Parsing | Conversational Agents |
|--------|---------------------|----------------------|
| Approach | Hardcoded rules | LLM reasoning |
| Flexibility | Fixed patterns | Adaptive queries |
| Understanding | Surface-level | Deep semantic |
| Extensibility | Rewrite code | Add questions |
| Intelligence | Rule-based | Conversational |

## File Structure

```
tableau_analyzer/
├── config/
│   ├── __init__.py
│   └── settings.py          # Vertex AI configuration
├── models/
│   ├── __init__.py
│   └── state.py             # AnalysisState TypedDict
├── agents/
│   ├── __init__.py
│   ├── agent_1.py           # Tableau Domain Expert (queryable)
│   ├── agent_2.py           # Complexity Analyzer
│   └── agent_3.py           # Feature Extractor (placeholder)
├── tools/
│   ├── __init__.py
│   └── file_tools.py        # XML to JSON conversion
├── workflows/
│   ├── __init__.py
│   └── tableau_workflow.py  # LangGraph orchestration
├── tests/
│   ├── __init__.py
│   ├── test_agent_1.py      # Test Agent 1
│   └── test_workflow.py     # Test full workflow
├── data/
│   └── .gitkeep
├── main.py                   # Main entry point
└── README.md                 # This file
```

## Troubleshooting

### GCP Authentication Issues

If you see authentication errors:

```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config get-value project

# Set project if needed
gcloud config set project YOUR_PROJECT_ID
```

### Model Not Available

If Gemini model is not available in your region:

1. Check available models:
   ```bash
   gcloud ai models list --region=us-central1
   ```

2. Update `MODEL_NAME` in `config/settings.py`:
   ```python
   MODEL_NAME = "gemini-pro"  # or another available model
   ```

### File Not Found

Ensure test file exists:
```bash
ls input_files/tableau/sales_summary_final.xml
```

Or update `SAMPLE_FILE` in `config/settings.py`

## Future Enhancements

1. **Agent 3 Implementation**: Extract specific migration features
2. **More Agents**: Add agents for security, performance, data quality analysis
3. **Caching**: Cache Agent 1 responses for repeated questions
4. **Batch Processing**: Analyze multiple Tableau files
5. **Looker Generation**: Generate Looker LookML from analysis

## Integration with Existing System

This system **coexists** with your existing agents:

- Separate namespace: `tableau_analyzer.*`
- Different state: `AnalysisState` vs `AssessmentState`
- Different approach: Conversational vs rule-based
- Can compare results side-by-side

## License

Part of the BI Assessment Accelerator project.

## Support

For issues or questions:
1. Check configuration in `config/settings.py`
2. Verify GCP authentication
3. Review error messages in output
4. Check conversation logs in `agent_conversations`
