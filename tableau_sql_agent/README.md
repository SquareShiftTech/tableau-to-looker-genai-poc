# Tableau Migration Accelerator

Automatically transform Tableau XML files into a queryable PostgreSQL relational database for migration assessment using LangGraph, SQL Agent, and Vertex AI Gemini.

## Features

- 🔄 Automatic XML to JSON conversion
- 📊 Depth-based JSON structure analysis
- 🤖 AI-powered schema design (Gemini 2.0 Flash)
- 🗄️ PostgreSQL native transformations using JSONB
- 🔧 SQL Agent for automated query execution
- 📈 Queryable relational model for migration assessment

## Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Google Cloud account with Vertex AI enabled
- Google Cloud CLI configured

## Setup

### 1. Google Cloud Setup

```bash
# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com
```

### 2. PostgreSQL Setup

```bash
# Install PostgreSQL (macOS)
brew install postgresql
brew services start postgresql

# Create database
createdb tableau_migration
```

### 3. Project Setup

```bash
# Navigate to project directory
cd tableau_sql_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 4. Environment Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
# Update: GOOGLE_CLOUD_PROJECT, DB_PASSWORD, etc.
```

## Usage

### Basic Usage

```bash
python main.py ../input_files/tableau/sales_summary_final.xml
```

### Programmatic Usage

```python
from main import convert_xml_to_json
from agents.workflow import create_workflow

# Convert XML to JSON
json_data = convert_xml_to_json("my_tableau_file.xml")

# Run workflow
workflow = create_workflow()
result = workflow.invoke({
    "file_name": "my_tableau_file.twb",
    "raw_json": json_data,
    "status": "started",
    "errors": []
})

print(f"Status: {result['status']}")
```

## Architecture

```
Tableau XML → JSON → PostgreSQL Raw Storage
                ↓
         JSON Analysis (depth-based)
                ↓
         Schema Design (AI Agent)
                ↓
         Table Creation (SQL Agent)
                ↓
         Data Transform (SQL Agent with JSONB queries)
                ↓
         Relational Model (queryable for assessment)
```

## Assessment Queries

After processing, query the relational tables:

```sql
-- Find all dashboards
SELECT * FROM dashboard;

-- Count calculated fields by type
SELECT calculation_type, COUNT(*) 
FROM calculated_field 
GROUP BY calculation_type;

-- Migration complexity by workbook
SELECT 
    w.workbook_name,
    COUNT(DISTINCT d.dashboard_id) as dashboard_count,
    COUNT(cf.field_id) as calc_field_count
FROM workbook w
LEFT JOIN dashboard d ON w.workbook_id = d.workbook_id
LEFT JOIN calculated_field cf ON w.workbook_id = cf.workbook_id
GROUP BY w.workbook_name;
```

## Development

### Run Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
ruff check .
```

## Troubleshooting

### Connection Issues

- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `.env`
- Test connection: `psql -U postgres -d tableau_migration`

### Google Cloud Authentication

```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config get-value project
```

### SQL Agent Errors

- Check PostgreSQL JSONB support (v9.4+)
- Verify table permissions
- Review SQL Agent verbose output

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
