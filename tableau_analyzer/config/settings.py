"""
Configuration for Vertex AI and project settings
"""
import os
import subprocess

# Vertex AI Configuration
# Priority: Environment variable > Default value
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tableau-to-looker-migration")
LOCATION = "us-central1"  # or your preferred region
MODEL_NAME = "gemini-2.5-pro"  # Using stable model instead of experimental

# File paths
INPUT_FILES_DIR = "../input_files/tableau"
DATA_DIR = "data"
SAMPLE_FILE = "sales_summary_final.xml"

# Agent settings
AGENT_TEMPERATURE = 0
AGENT_VERBOSE = True
MAX_ITERATIONS = 15
MAX_EXECUTION_TIME = 120

# Retry settings for agents (backward compatibility)
MAX_RETRIES_AGENT_2 = 3  # Max retries for Agent 2 complexity analyzer
RETRY_DELAY_SECONDS = 2  # Delay between retries (in seconds)
MAX_RETRIES_AGENT_3_PER_FEATURE = 2  # Max retries per feature for Agent 3 extractor
MIN_FEATURES_EXTRACTED_PERCENT = 0.7  # Minimum percentage of features to extract (70%)
