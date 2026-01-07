# Tableau to Looker Migration - Local Setup

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure GCP Project

Set `tableau-to-looker-migration` as your default GCP project:

```bash
gcloud config set project tableau-to-looker-migration
gcloud auth application-default login
```

Or set environment variable:
```bash
export GOOGLE_CLOUD_PROJECT=tableau-to-looker-migration
```

### 3. Setup PostgreSQL

**Install PostgreSQL** (if not installed):
- Windows: Download from https://www.postgresql.org/download/windows/
- macOS: `brew install postgresql@15`
- Linux: `sudo apt install postgresql`

**Create Database:**
```bash
psql -U postgres
CREATE DATABASE tableau_migration;
\q
```

**Configure Credentials:**

Edit `evaluations/xml_to_dict_agent.py` (lines 32-38) and `evaluations/complexity_analysis_agent.py` (lines 36-42):

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tableau_migration",
    "user": "postgres",
    "password": "your_password"  # Update this
}
```

### 4. Run Workflow

Place Tableau XML files in `input_files/tableau/`, then:

```bash
python evaluations/unified_tableau_workflow.py
```

**Options:**
- `--no-fresh` - Skip truncating tables
- `--skip-ingestion` - Skip ingestion step
- `--complexity-only` - Run only complexity analysis

## Output

Results saved to: `evaluations/complexity_analysis_results.json`

