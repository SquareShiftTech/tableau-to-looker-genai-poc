# Tableau to Looker Migration Workflow

This directory contains the complete workflow for migrating Tableau workbooks to Looker using Gemini 2.5 Flash for DSL and LookML generation.

## Directory Structure

```
workflow/
├── __init__.py              # Package exports
├── config.py                # Configuration (paths, API keys, etc.)
├── gemini_client.py         # Gemini API client wrapper
├── phase1_dsl_generation.py # Phase 1: Generate DSL from chunks
├── phase2_lookml_generation.py # Phase 2: Generate LookML from DSL
├── phase3_mcp_deployment.py   # Phase 3: Deploy LookML via MCP
├── orchestrator.py          # Main workflow orchestrator
└── README.md                # This file
```

## Workflow Overview

The migration process consists of three phases:

### Phase 1: DSL Generation (Chunks → DSL)
- Reads Tableau metadata chunks (connection, fields, worksheets, dashboards)
- Uses Gemini 2.5 Flash to generate Compact DSL
- Outputs: `generated_dsl/*.dsl` files

### Phase 2: LookML Generation (DSL → LookML)
- Reads generated DSL files
- Uses Gemini 2.5 Flash to generate LookML
- Outputs: `generated_lookml/views/`, `models/`, `dashboards/`

### Phase 3: MCP Deployment (LookML → Looker)
- Deploys LookML files to Looker using MCP tools
- Updates model files with explore definitions
- Deploys dashboards

## Setup

1. **Install dependencies:**
   ```bash
   pip install google-genai>=0.2.0
   ```

2. **Set up Vertex AI:**
   
   a. **Enable Vertex AI API** in your Google Cloud project:
      - Go to: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
      - Click "Enable"
   
   b. **Create a Service Account** (if not already done):
      - Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
      - Click "+ CREATE SERVICE ACCOUNT"
      - Name: `gemini-workflow` (or your choice)
      - Grant role: "Vertex AI User" (`roles/aiplatform.user`)
      - Click "CREATE AND CONTINUE" → "DONE"
   
   c. **Create and download Service Account key:**
      - Click on the service account you created
      - Go to "KEYS" tab → "ADD KEY" → "Create new key"
      - Choose "JSON" → "CREATE"
      - Save the downloaded JSON file securely
   
   d. **Set authentication:**
      ```bash
      # Windows PowerShell
      $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account-key.json"
      
      # Windows CMD
      set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account-key.json
      
      # Linux/Mac
      export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
      ```
   
   e. **Set Google Cloud project ID:**
      ```bash
      # Windows PowerShell
      $env:GOOGLE_CLOUD_PROJECT="your-project-id"
      
      # Windows CMD
      set GOOGLE_CLOUD_PROJECT=your-project-id
      
      # Linux/Mac
      export GOOGLE_CLOUD_PROJECT="your-project-id"
      ```
      Or set it in `workflow/config.py`:
      ```python
      VERTEX_AI_PROJECT = "your-project-id"
      ```

3. **Configure Looker project ID** (in `workflow/config.py`):
   ```python
   LOOKER_PROJECT_ID = "your-project-id"
   ```

## Usage

### Run Complete Workflow

```bash
python -m workflow.orchestrator
```

This will:
1. Generate all DSL files from chunks
2. Generate all LookML files from DSL
3. Prompt for MCP deployment confirmation

### Run Individual Phases

```bash
# Phase 1: DSL Generation
python -m workflow.phase1_dsl_generation

# Phase 2: LookML Generation
python -m workflow.phase2_lookml_generation

# Phase 3: MCP Deployment
python -m workflow.phase3_mcp_deployment
```

### Programmatic Usage

```python
from workflow import DSLGenerator, LookMLGenerator, MCPDeployer
from workflow.gemini_client import GeminiClient

# Initialize clients
client = GeminiClient()
dsl_gen = DSLGenerator(client)
lookml_gen = LookMLGenerator(client)
deployer = MCPDeployer()

# Generate DSL
dsl = dsl_gen.generate_connection_dsl("chunk_*_connection.json")

# Generate LookML
lookml = lookml_gen.generate_model_lookml("connection.dsl")

# Deploy (requires MCP setup)
deployer.deploy_file("views/table.view.lkml", lookml_content)
```

## File Structure

### Input Files (from parsing)
All chunk files are stored in the `chunks/` directory:
- `chunks/chunk_*_connection.json` - Connection metadata chunks
- `chunks/chunk_*_fields_*.json` - Field metadata chunks
- `chunks/chunk_worksheet_batch_*.json` - Worksheet batch chunks
- `chunks/chunk_dashboard_batch_*.json` - Dashboard batch chunks

### Generated DSL Files
- `generated_dsl/*_connection.dsl` - Connection DSL
- `generated_dsl/*_fields.dsl` - Field DSL
- `generated_dsl/worksheets.dsl` - Worksheet DSL
- `generated_dsl/dashboards.dsl` - Dashboard DSL

### Generated LookML Files
- `generated_lookml/models/*.model.lkml` - Model files
- `generated_lookml/views/*.view.lkml` - View files
- `generated_lookml/explores.lkml` - Explore definitions
- `generated_lookml/dashboards/*.dashboard.lookml` - Dashboard files

## Configuration

Edit `workflow/config.py` to customize:
- Project paths
- Vertex AI project ID and location
- Gemini model version (default: `gemini-2.5-flash`)
- Looker project ID
- Output directories

## Notes

- **Vertex AI**: This workflow uses Vertex AI exclusively. No API keys needed - authentication is via service account.
- **Gemini Model**: Defaults to `gemini-2.5-flash`. Update in `config.py` if needed.
- **Location**: Default location is `global`. You can change to `us-central1`, `us-east1`, etc. in `config.py`.
- **MCP Integration**: Phase 3 requires MCP tools to be configured. Update `phase3_mcp_deployment.py` with your MCP setup.
- **Error Handling**: Each phase includes error handling and will report issues during execution.
- **File Parsing**: The LookML generators include parsers to extract multiple view/dashboard files from Gemini output.

## Troubleshooting

1. **Project ID Error**: Ensure `GOOGLE_CLOUD_PROJECT` is set in environment or `VERTEX_AI_PROJECT` in config
2. **Authentication Error**: Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to your service account JSON file
3. **Vertex AI API Not Enabled**: Enable Vertex AI API in Google Cloud Console
4. **File Not Found**: Check that chunk files exist in the project root
5. **MCP Errors**: Verify MCP tools are properly configured for Phase 3
6. **Parsing Issues**: If view/dashboard parsing fails, check the LookML output format

