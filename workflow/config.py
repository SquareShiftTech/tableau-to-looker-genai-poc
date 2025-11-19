"""Configuration for Tableau to Looker migration workflow."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CHUNKS_DIR = PROJECT_ROOT / "chunks"
GENERATED_DSL_DIR = PROJECT_ROOT / "generated_dsl"
GENERATED_LOOKML_DIR = PROJECT_ROOT / "generated_lookml"

# Create directories if they don't exist
CHUNKS_DIR.mkdir(exist_ok=True)
GENERATED_DSL_DIR.mkdir(exist_ok=True)
GENERATED_LOOKML_DIR.mkdir(exist_ok=True)
(GENERATED_LOOKML_DIR / "views").mkdir(exist_ok=True)
(GENERATED_LOOKML_DIR / "models").mkdir(exist_ok=True)
(GENERATED_LOOKML_DIR / "dashboards").mkdir(exist_ok=True)

# Vertex AI configuration
VERTEX_AI_PROJECT = "tableau-to-looker-migration"  # Set via environment variable GOOGLE_CLOUD_PROJECT or here
VERTEX_AI_LOCATION = "global"  # or "us-central1", "us-east1", etc.
GEMINI_MODEL = "gemini-2.5-flash"  # Vertex AI model name

# Looker MCP configuration
LOOKER_PROJECT_ID = "tableau_looker_team_test"  # Update as needed

# Prompt paths
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DSL_PROMPTS_DIR = PROMPTS_DIR / "dsl_generation"
LOOKML_PROMPTS_DIR = PROMPTS_DIR / "lookml_generation"

