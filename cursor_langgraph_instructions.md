# LangGraph BI Assessment Accelerator - Cursor Code Generation Instructions

## Project Overview
Build a multi-agent system using LangGraph that processes BI metadata from multiple platforms (Tableau, Power BI, MicroStrategy, Cognos) and generates assessment reports with consolidation recommendations.

## Architecture: Layered Structure

```
project_root/
├── config/
│   ├── __init__.py
│   └── settings.py                 # Environment, BigQuery config, API keys
│
├── models/
│   ├── __init__.py
│   └── state.py                    # TypedDict definitions (AssessmentState, etc.)
│
├── services/
│   ├── __init__.py
│   ├── llm_service.py             # Claude API calls (to be implemented)
│   ├── bigquery_service.py        # BigQuery write operations
│   └── gcs_service.py             # GCS file reading operations
│
├── agents/
│   ├── __init__.py
│   ├── exploration_agent.py       # Step 1: Discover components
│   ├── parsing_agent.py           # Step 2: Extract details
│   ├── calculation_agent.py       # Step 3a: Analyze metrics
│   ├── visualization_agent.py     # Step 3b: Analyze visualizations
│   ├── dashboard_agent.py         # Step 3c: Analyze dashboards
│   ├── datasource_agent.py        # Step 3d: Analyze data sources
│   └── strategy_agent.py          # Step 4: Make recommendations
│
├── workflows/
│   ├── __init__.py
│   └── assessment_workflow.py     # LangGraph graph definition
│
├── dummy_data/
│   ├── __init__.py
│   └── sample_data.py             # Dummy data for all agents
│
├── utils/
│   ├── __init__.py
│   └── logger.py                  # Logging utilities
│
├── tests/
│   ├── __init__.py
│   ├── test_agents.py             # Unit tests for agents
│   └── test_workflow.py           # Integration tests
│
├── main.py                        # Entry point
├── requirements.txt               # Dependencies
└── README.md                      # Project documentation
```

## Layer Descriptions

### 1. Config Layer (`config/`)
- **Purpose**: Centralized configuration
- **Files**:
  - `settings.py`: Environment variables, GCP project IDs, BigQuery dataset names, LLM model names
- **Responsibility**: Load and validate all configuration at startup

### 2. Models Layer (`models/`)
- **Purpose**: Define data structures
- **Files**:
  - `state.py`: TypedDict for AssessmentState with all fields
- **Responsibility**: Type definitions, validation schemas

### 3. Services Layer (`services/`)
- **Purpose**: Abstract external integrations
- **Files**:
  - `llm_service.py`: Wrapper around Claude API (currently returns dummy data, will call real LLM later)
  - `bigquery_service.py`: Wrapper for BigQuery insert operations
  - `gcs_service.py`: Read metadata files from GCS
- **Responsibility**: Handle all API calls, error handling, retries

### 4. Agents Layer (`agents/`)
- **Purpose**: Individual agent logic
- **Files**: One agent per file
  - Each agent calls services (LLM, BigQuery, GCS)
  - Each agent receives state, processes it, returns updated state
  - Currently uses dummy data from services (swappable later)
- **Responsibility**: Agent-specific business logic, complexity calculations

### 5. Workflows Layer (`workflows/`)
- **Purpose**: LangGraph orchestration
- **Files**:
  - `assessment_workflow.py`: Define graph structure, edges, routing
- **Responsibility**: Control flow, parallel execution, error handling

### 6. Dummy Data Layer (`dummy_data/`)
- **Purpose**: Test data for development
- **Files**:
  - `sample_data.py`: All dummy responses structured per agent
- **Responsibility**: Provide realistic dummy data for each agent

### 7. Utils Layer (`utils/`)
- **Purpose**: Shared utilities
- **Files**:
  - `logger.py`: Structured logging
- **Responsibility**: Cross-cutting concerns

### 8. Tests Layer (`tests/`)
- **Purpose**: Unit and integration tests
- **Files**:
  - `test_agents.py`: Test each agent independently
  - `test_workflow.py`: Test complete workflow

## Functional Flow (4-Step Process)

### Step 1: Exploration Agent
```
Input: source_files (list of metadata file paths from GCS)
Process:
  - Call LLM service with: "Parse these metadata files, discover all components"
  - LLM returns: discovered_components (dashboards, metrics, visualizations, datasources)
Output: AssessmentState with discovered_components populated
```

### Step 2: Parsing Agent
```
Input: discovered_components from state
Process:
  - For each component, call LLM service: "Extract complexity-relevant details"
  - Parse results: formulas, structure, dependencies
Output: AssessmentState with parsed_metrics, parsed_dashboards, parsed_visualizations, parsed_datasources
```

### Step 3: Parallel Specialized Agents
```
3a. Calculation Agent
  Input: parsed_metrics
  Process: Analyze formula complexity, functions, dependencies
  Output: Write to BigQuery table "calculations_analysis"
  State: calculation_analysis populated

3b. Visualization Agent
  Input: parsed_visualizations
  Process: Analyze chart type, data complexity
  Output: Write to BigQuery table "visualizations_analysis"
  State: visualization_analysis populated

3c. Dashboard Agent
  Input: parsed_dashboards
  Process: Analyze dashboard structure, filters, interactions
  Output: Write to BigQuery table "dashboards_analysis"
  State: dashboard_analysis populated

3d. Data Source Agent
  Input: parsed_datasources
  Process: Analyze compatibility, join complexity
  Output: Write to BigQuery table "datasources_analysis"
  State: datasource_analysis populated
```

### Step 4: Strategy Agent
```
Input: All analyses from Step 3 (read from BigQuery or state)
Process:
  - Aggregate complexity scores
  - Identify consolidation opportunities
  - Estimate migration effort
  - Generate recommendations
Output: final_report with:
  - Executive summary
  - Complexity breakdown
  - Consolidation opportunities
  - Migration recommendations
```

## Agent Structure Template

Each agent file should follow this pattern:

```python
from models.state import AssessmentState
from services.llm_service import LLMService
from services.bigquery_service import BigQueryService
from dummy_data.sample_data import DUMMY_[AGENT_NAME]

async def [agent_name]_agent(state: AssessmentState) -> AssessmentState:
    """
    [AGENT_NAME] Agent - [Description]
    
    INPUT: state with [input_fields]
    OUTPUT: state with [output_fields]
    WRITES: BigQuery table [table_name] (if applicable)
    
    FUTURE LLM IMPLEMENTATION:
    Currently uses dummy data. To implement with real LLM:
    1. Remove DUMMY_[AGENT_NAME] usage
    2. Call llm_service.analyze_[aspect](state[input])
    3. Parse LLM response into structured format
    """
    
    logger.info(f"Starting {agent_name} agent")
    
    # Step 1: Get data (from state or call LLM service)
    data = DUMMY_[AGENT_NAME]  # Replace with: llm_service.analyze_[aspect](...)
    
    # Step 2: Process data (agent-specific logic)
    analysis = process_analysis(data)
    
    # Step 3: Write to BigQuery (if applicable)
    bigquery_service.insert_rows("[table_name]", analysis)
    
    # Step 4: Update state
    state['[output_field]'] = analysis
    state['status'] = '[step]_complete'
    
    logger.info(f"Completed {agent_name} agent")
    return state
```

## Key Design Principles

1. **Separation of Concerns**: 
   - Services handle external APIs
   - Agents handle business logic
   - Workflows handle orchestration

2. **Dummy Data First**: 
   - All agents work with dummy data initially
   - Services return dummy responses
   - Later: Replace services to call real LLMs

3. **Async Ready**: 
   - Use `async` functions for agents (prepare for concurrent execution)
   - LangGraph supports async nodes

4. **Logging**: 
   - Every agent logs entry and exit
   - Log complexity scores, decisions made
   - Enables debugging and auditing

5. **Type Safety**: 
   - Use TypedDict for AssessmentState
   - Type hints on all functions
   - mypy compatible

## Dependencies (pyproject.toml)

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "bi-assessment-accelerator"
version = "0.1.0"
description = "Multi-agent BI assessment system using LangGraph"
requires-python = ">=3.10"
dependencies = [
    "langgraph>=0.0.x",
    "anthropic>=0.x.x",
    "google-cloud-bigquery>=3.x.x",
    "google-cloud-storage>=2.x.x",
    "pydantic>=2.x.x",
    "python-dotenv>=1.x.x",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.x.x",
    "pytest-asyncio>=0.x.x",
    "mypy>=1.x.x",
    "black>=23.x.x",
    "ruff>=0.x.x",
]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

## Entry Point (main.py)

```python
import asyncio
from config.settings import load_settings
from workflows.assessment_workflow import create_assessment_workflow
from models.state import AssessmentState

async def main():
    settings = load_settings()
    workflow = create_assessment_workflow()
    
    initial_state = AssessmentState(
        job_id="assessment_001",
        source_files=[
            {"platform": "tableau", "file_path": "gs://bucket/tableau.json"},
            {"platform": "power_bi", "file_path": "gs://bucket/powerbi.json"},
        ],
        # ... other fields
    )
    
    result = await workflow.ainvoke(initial_state)
    print(result['final_report'])

if __name__ == "__main__":
    asyncio.run(main())
```

## Development Workflow

1. **Phase 1**: Generate all code with dummy data
   - All agents work and produce dummy outputs
   - LangGraph workflow orchestrates correctly
   - Tests pass with dummy data

2. **Phase 2**: Implement LLM calls
   - Replace dummy data in services
   - Each agent now calls Claude for real
   - Validate LLM responses

3. **Phase 3**: Implement BigQuery writes
   - Agents write real analysis to BigQuery
   - Strategy agent reads from BigQuery
   - Full end-to-end workflow works

4. **Phase 4**: Add error handling and monitoring
   - Retry logic for API calls
   - Better logging and tracing
   - Performance monitoring

## Cursor Prompt (Use This)

```
Generate a complete Python project for a LangGraph-based BI Assessment multi-agent system.

Architecture:
- Layered structure: config → models → services → agents → workflows → dummy_data → utils → tests
- Follow the folder structure provided above
- Each layer has clear responsibilities

Agents (implement all 7):
1. exploration_agent: Discover components from metadata
2. parsing_agent: Extract complexity details
3. calculation_agent: Analyze metrics
4. visualization_agent: Analyze visualizations
5. dashboard_agent: Analyze dashboards
6. datasource_agent: Analyze data sources
7. strategy_agent: Make recommendations

Requirements:
- Use LangGraph StateGraph for orchestration
- Use TypedDict for type safety
- All agents accept AssessmentState and return updated AssessmentState
- Use dummy data from dummy_data/sample_data.py
- Include comprehensive logging
- Every agent logs entry/exit with key metrics
- Services layer provides abstraction for LLM, BigQuery, GCS
- Ready for Phase 2: Replace dummy data with real LLM calls

Structure:
- config/settings.py: Load environment config
- models/state.py: AssessmentState TypedDict with all fields
- services/: Abstract LLM (Claude), BigQuery, GCS
- agents/: 7 agent files, each ~50-100 lines
- workflows/assessment_workflow.py: LangGraph graph definition
- dummy_data/sample_data.py: Realistic dummy data for all agents
- utils/logger.py: Structured logging
- tests/: Unit and integration tests
- main.py: Entry point
- requirements.txt: Dependencies
- README.md: Project documentation

Code Style:
- Use async functions (prepare for concurrent execution)
- Clear function docstrings
- Type hints everywhere
- Comments explaining "FUTURE LLM IMPLEMENTATION"
- Logging at key decision points
```

This structure allows you to:
1. Generate complete working code with Cursor
2. All agents work immediately with dummy data
3. Tests pass
4. Later phases: Just swap services layer to call real LLMs
5. Everything is modular and maintainable
