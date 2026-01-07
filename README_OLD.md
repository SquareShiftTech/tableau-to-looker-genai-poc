# BI Assessment Accelerator

A multi-agent system using LangGraph that processes BI metadata from multiple platforms (Tableau, Power BI, MicroStrategy, Cognos) and generates assessment reports with consolidation recommendations.

## Architecture

The project follows a layered architecture:

```
project_root/
├── config/          # Configuration and settings
├── models/          # Data models and state definitions
├── services/        # External service integrations (LLM, BigQuery, GCS)
├── agents/          # Individual agent implementations
├── workflows/       # LangGraph workflow orchestration
├── dummy_data/      # Sample data for testing
├── utils/           # Shared utilities (logging, etc.)
├── tests/           # Unit and integration tests
└── main.py          # Entry point
```

## Agents

The system consists of 7 specialized agents:

1. **Exploration Agent**: Discovers components from metadata files
2. **Parsing Agent**: Extracts complexity-relevant details
3. **Calculation Agent**: Analyzes metric complexity
4. **Visualization Agent**: Analyzes visualization complexity
5. **Dashboard Agent**: Analyzes dashboard structure
6. **Data Source Agent**: Analyzes data source compatibility
7. **Strategy Agent**: Generates migration recommendations

## Workflow

The workflow follows a 4-step process:

1. **Exploration**: Discover all components from source files
2. **Parsing**: Extract complexity details from discovered components
3. **Parallel Analysis**: Specialized agents analyze different component types
4. **Strategy**: Generate final recommendations and migration plan

## Installation

1. Install dependencies:

```bash
pip install -e .
```

Or with dev dependencies:

```bash
pip install -e ".[dev]"
```

2. Set up environment variables (create `.env` file):

```env
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=bi_assessment
GCS_BUCKET=your-bucket-name
ANTHROPIC_API_KEY=your-api-key
LLM_MODEL=claude-3-5-sonnet-20241022
LOG_LEVEL=INFO
```

## Usage

### Running the Application

```bash
python main.py
```

### Running Tests

```bash
pytest tests/
```

## Development Phases

### Phase 1: Dummy Data (Current)
- All agents work with dummy data
- LangGraph workflow orchestrates correctly
- Tests pass with dummy data

### Phase 2: LLM Integration
- Replace dummy data in services
- Implement real Claude API calls
- Validate LLM responses

### Phase 3: BigQuery Integration
- Implement BigQuery writes
- Strategy agent reads from BigQuery
- Full end-to-end workflow

### Phase 4: Error Handling & Monitoring
- Retry logic for API calls
- Enhanced logging and tracing
- Performance monitoring

## Project Structure

- **config/**: Centralized configuration management
- **models/**: TypedDict definitions for type safety
- **services/**: Abstract external integrations (LLM, BigQuery, GCS)
- **agents/**: Individual agent business logic
- **workflows/**: LangGraph orchestration
- **dummy_data/**: Test data for development
- **utils/**: Shared utilities (logging)
- **tests/**: Unit and integration tests

## Key Design Principles

1. **Separation of Concerns**: Services handle APIs, agents handle business logic, workflows handle orchestration
2. **Dummy Data First**: All agents work with dummy data initially, ready for LLM integration
3. **Async Ready**: All functions are async for concurrent execution
4. **Type Safety**: TypedDict for state, type hints everywhere
5. **Comprehensive Logging**: Every agent logs entry/exit with key metrics

## License

MIT

