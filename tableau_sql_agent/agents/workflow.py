"""LangGraph workflow with SQL Agent"""
from langgraph.graph import StateGraph, END
from langchain_google_vertexai import ChatVertexAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from typing import TypedDict, Dict, Any, List, Optional
import json
import re
import time
from pathlib import Path
from datetime import datetime

from tools.json_analyzer import analyze_json_hierarchy
from database.db_manager import DatabaseManager
from agents.prompts import SCHEMA_DESIGN_PROMPT, TRANSFORMATION_SQL_PROMPT
from config import (
    LLM_MODEL, 
    LLM_TEMPERATURE, 
    GOOGLE_CLOUD_PROJECT, 
    GOOGLE_CLOUD_LOCATION, 
    DB_CONFIG
)


def extract_json_from_response(content: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    Robustly extract JSON from LLM response, handling various formats and truncation.
    
    Args:
        content: The raw response content from LLM
        max_retries: Maximum number of parsing attempts
    
    Returns:
        Parsed JSON dict or None if all attempts fail
    """
    # Method 1: Try extracting from code blocks
    if "```json" in content:
        try:
            json_str = content.split("```json")[1].split("```")[0].strip()
            # Check if JSON appears truncated (ends with incomplete string)
            if json_str and not json_str.rstrip().endswith('}'):
                # Try to fix truncated JSON
                json_str = _fix_truncated_json(json_str)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Try to fix and retry
            try:
                json_str = content.split("```json")[1].split("```")[0].strip()
                fixed_json = _fix_truncated_json(json_str)
                return json.loads(fixed_json)
            except:
                pass
        except:
            pass
    
    if "```" in content:
        try:
            json_str = content.split("```")[1].split("```")[0].strip()
            # Remove json marker if present
            if json_str.startswith("json"):
                json_str = json_str[4:].strip()
            # Check if truncated
            if json_str and not json_str.rstrip().endswith('}'):
                json_str = _fix_truncated_json(json_str)
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                json_str = content.split("```")[1].split("```")[0].strip()
                if json_str.startswith("json"):
                    json_str = json_str[4:].strip()
                fixed_json = _fix_truncated_json(json_str)
                return json.loads(fixed_json)
            except:
                pass
        except:
            pass
    
    # Method 2: Find JSON object boundaries using regex
    # Look for { ... } pattern
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.finditer(json_pattern, content, re.DOTALL)
    
    for match in matches:
        try:
            json_str = match.group(0)
            return json.loads(json_str)
        except:
            continue
    
    # Method 3: Try to find and extract JSON from the content
    # Look for first { and try to find matching }
    start_idx = content.find('{')
    if start_idx != -1:
        # Try to find the matching closing brace
        brace_count = 0
        for i in range(start_idx, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    try:
                        json_str = content[start_idx:i+1]
                        return json.loads(json_str)
                    except:
                        break
    
    # Method 4: Try to fix truncated JSON by adding closing braces
    if start_idx != -1:
        try:
            # Count open vs close braces
            open_braces = content.count('{')
            close_braces = content.count('}')
            missing_braces = open_braces - close_braces
            
            if missing_braces > 0:
                # Try to fix by adding closing braces and brackets
                fixed_content = content
                # Close any open arrays
                open_brackets = fixed_content.count('[') - fixed_content.count(']')
                fixed_content += ']' * open_brackets
                # Close any open strings (remove trailing incomplete strings)
                fixed_content = re.sub(r'"[^"]*$', '', fixed_content)
                # Add missing closing braces
                fixed_content += '}' * missing_braces
                
                # Try to extract JSON again
                start_idx = fixed_content.find('{')
                if start_idx != -1:
                    brace_count = 0
                    for i in range(start_idx, len(fixed_content)):
                        if fixed_content[i] == '{':
                            brace_count += 1
                        elif fixed_content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                try:
                                    json_str = fixed_content[start_idx:i+1]
                                    return json.loads(json_str)
                                except:
                                    break
        except:
            pass
    
    # Method 5: Try parsing the entire content as JSON
    try:
        return json.loads(content.strip())
    except:
        pass
    
    return None


def _fix_truncated_json(json_str: str) -> str:
    """
    Attempt to fix truncated JSON by closing incomplete strings and structures.
    
    Args:
        json_str: Potentially truncated JSON string
    
    Returns:
        Fixed JSON string
    """
    if not json_str:
        return json_str
    
    # Remove trailing incomplete string (common truncation pattern)
    # Pattern: ends with "ddl": "CREATE TABLE... (incomplete)
    json_str = re.sub(r'("ddl":\s*"[^"]*)$', r'\1"', json_str)
    
    # If still ends with incomplete string, close it
    if json_str.rstrip().endswith('"') and not json_str.rstrip().endswith('\\"'):
        # Check if it's in the middle of a string
        last_quote_idx = json_str.rfind('"')
        if last_quote_idx > 0:
            # Check if it's an unclosed string (odd number of quotes before)
            quotes_before = json_str[:last_quote_idx].count('"')
            if quotes_before % 2 == 0:  # String is open
                # Try to close the string and structure
                json_str = json_str.rstrip().rstrip('"')
    
    # Count braces and brackets to close structures
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')
    
    # Close incomplete array items first
    if open_brackets > close_brackets:
        # Find the last incomplete array item
        last_bracket = json_str.rfind('[')
        if last_bracket != -1:
            # Check if we're in the middle of an object in the array
            after_bracket = json_str[last_bracket:]
            if '{' in after_bracket and after_bracket.count('{') > after_bracket.count('}'):
                # Close the object
                json_str += '}'
            # Close the array
            json_str += ']' * (open_brackets - close_brackets)
    
    # Close incomplete objects
    if open_braces > close_braces:
        # Close any incomplete string in the last object
        json_str = re.sub(r'("ddl":\s*"[^"]*)$', r'\1"', json_str)
        # Add closing braces
        json_str += '}' * (open_braces - close_braces)
    
    return json_str


class WorkflowState(TypedDict):
    """State for the workflow"""
    file_name: str
    raw_json: Dict[str, Any]
    file_id: int
    json_analysis: Dict[str, Any]
    relational_schema: Dict[str, Any]
    transformation_sql: Dict[str, Any]
    status: str
    errors: List[str]


def create_workflow():
    """Create the LangGraph workflow with SQL Agent"""
    
    # Initialize LLM
    llm = ChatVertexAI(
        model_name=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION
    )
    
    # Initialize SQL Database connection
    db_uri = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    sql_db = SQLDatabase.from_uri(db_uri)
    
    # Create SQL Agent
    sql_agent = create_sql_agent(
        llm=llm,
        db=sql_db,
        agent_type="openai-tools",
        verbose=True
    )
    
    db_manager = DatabaseManager()
    
    # Node 1: Store raw JSON
    def store_raw_node(state: WorkflowState) -> WorkflowState:
        print(f"\n📥 Storing raw JSON for: {state['file_name']}")
        try:
            file_id = db_manager.store_raw_json(state['file_name'], state['raw_json'])
            state['file_id'] = file_id
            state['status'] = 'raw_stored'
            print(f"✅ Stored with ID: {file_id}")
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Storage failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Node 2: Analyze JSON structure
    def analyze_structure_node(state: WorkflowState) -> WorkflowState:
        print(f"\n🔍 Analyzing JSON structure...")
        try:
            # Ensure raw_json is a dict, not a string
            raw_json = state['raw_json']
            if isinstance(raw_json, str):
                raw_json = json.loads(raw_json)
                state['raw_json'] = raw_json
            
            # Verify it's a dict before passing to tool
            if not isinstance(raw_json, dict):
                raise ValueError(f"raw_json must be a dict, got {type(raw_json)}")
            
            analysis = analyze_json_hierarchy.invoke({"json_data": raw_json})
            state['json_analysis'] = analysis
            state['status'] = 'analyzed'
            print(f"✅ Found {analysis['total_entities']} entities, max depth: {analysis['max_depth']}")
            
            # Save analysis to file
            try:
                # Create output directory if it doesn't exist
                output_dir = Path("output/tableau_sql_agent")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate filename with timestamp
                file_name = state['file_name'].replace('.twb', '').replace('.xml', '')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = output_dir / f"json_analysis_{file_name}_{timestamp}.json"
                
                # Save analysis as pretty-printed JSON
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Analysis saved to: {output_file}")
            except Exception as save_error:
                print(f"⚠️  Warning: Could not save analysis to file: {save_error}")
            
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Analysis failed: {str(e)}"]
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        return state
    
    # Node 3: Design schema (Agent)
    def design_schema_node(state: WorkflowState) -> WorkflowState:
        print(f"\n🏗️  Designing relational schema...")
        max_retries = 2
        for attempt in range(max_retries):
            try:
                prompt = SCHEMA_DESIGN_PROMPT.format(
                    hierarchy=json.dumps(state['json_analysis'], indent=2)
                )
                
                # On retry, ask for shorter response
                if attempt > 0:
                    prompt += "\n\nCRITICAL: Your previous response was truncated. Please return a SHORTER response focusing ONLY on the top 50 most important tables. Prioritize: workbook, datasource, worksheet, dashboard, and their immediate children. Ensure the JSON is COMPLETE and properly closed."
                
                response = llm.invoke(prompt)
                
                # Extract JSON using robust method
                schema = extract_json_from_response(response.content)
                
                if schema is None:
                    # Debug: save response for inspection
                    print(f"⚠️  Could not extract JSON. Response length: {len(response.content)}")
                    print(f"Response preview (first 500 chars): {response.content[:500]}")
                    print(f"Response preview (last 500 chars): {response.content[-500:]}")
                    raise ValueError("Could not extract valid JSON from response")
                
                # Validate schema structure
                if 'tables' not in schema:
                    print(f"⚠️  Extracted schema keys: {list(schema.keys()) if schema else 'None'}")
                    print(f"Schema type: {type(schema)}")
                    raise ValueError(f"Schema missing 'tables' key. Found keys: {list(schema.keys()) if isinstance(schema, dict) else 'Not a dict'}")
                
                state['relational_schema'] = schema
                state['status'] = 'schema_designed'
                print(f"✅ Designed {len(schema['tables'])} tables")
                return state
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Attempt {attempt + 1} failed, retrying... Error: {str(e)[:200]}")
                    continue
                else:
                    state['status'] = 'error'
                    error_msg = f"Schema design failed after {max_retries} attempts: {str(e)}"
                    state['errors'] = [error_msg]
                    print(f"❌ Error: {error_msg}")
                    # Print first 500 chars of response for debugging
                    if 'response' in locals():
                        print(f"Response preview: {response.content[:500]}...")
        return state
    
    # Node 4: Create tables using SQL Agent
    def create_tables_node(state: WorkflowState) -> WorkflowState:
        print(f"\n🔨 Creating database tables using SQL Agent...")
        try:
            schema = state['relational_schema']
            
            # Combine all DDL statements
            all_ddl = []
            for table in schema['tables']:
                all_ddl.append(table['ddl'])
            all_ddl.extend(schema.get('indexes', []))
            
            # Rate limiting: Execute in smaller batches to avoid quota limits
            batch_size = 10  # Execute 10 statements per batch
            delay_between_batches = 2  # Wait 2 seconds between batches
            delay_between_agent_calls = 1  # Wait 1 second between agent invocations
            
            print(f"Executing {len(all_ddl)} DDL statements via SQL Agent in batches of {batch_size}...")
            
            # Split into batches
            batches = [all_ddl[i:i + batch_size] for i in range(0, len(all_ddl), batch_size)]
            
            for batch_num, batch in enumerate(batches, 1):
                print(f"Processing batch {batch_num}/{len(batches)} ({len(batch)} statements)...")
                
                # Create instruction for this batch
                ddl_statements_text = "\n\n".join([f"Statement {i+1}:\n{ddl}" for i, ddl in enumerate(batch)])
                
                agent_instruction = f"""Execute the following SQL DDL statements to create database tables and indexes.

CRITICAL: You must execute each statement using the sql_db_query tool. Execute them one by one.

Here are the statements to execute:

{ddl_statements_text}

Execute all statements in this batch."""
                
                # Add delay before agent call to respect rate limits
                if batch_num > 1:
                    print(f"Waiting {delay_between_batches} seconds to respect rate limits...")
                    time.sleep(delay_between_batches)
                
                result = sql_agent.invoke({"input": agent_instruction})
                print(f"Batch {batch_num} completed: {result['output'][:200]}...")
                
                # Small delay between batches
                if batch_num < len(batches):
                    time.sleep(delay_between_agent_calls)
            
            # Verify creation by asking the agent to list tables
            print("Verifying table creation...")
            time.sleep(delay_between_agent_calls)  # Delay before verification
            
            verify_instruction = "Execute this SQL query to list all tables: SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;"
            verify_result = sql_agent.invoke({"input": verify_instruction})
            
            print(f"✅ Table creation process completed")
            print(f"Verification result: {verify_result['output']}")
            
            state['status'] = 'tables_created'
            
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Table creation failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Node 5: Generate transformation SQL (Agent)
    def generate_transform_sql_node(state: WorkflowState) -> WorkflowState:
        print(f"\n⚙️  Generating SQL transformation queries...")
        max_retries = 2
        for attempt in range(max_retries):
            try:
                prompt = TRANSFORMATION_SQL_PROMPT.format(
                    schema=json.dumps(state['relational_schema'], indent=2),
                    hierarchy=json.dumps(state['json_analysis'], indent=2)
                )
                
                # On retry, ask for shorter response
                if attempt > 0:
                    prompt += "\n\nIMPORTANT: If the response is too long, focus on the most important transformations first. Ensure all JSON strings are properly closed."
                
                response = llm.invoke(prompt)
                
                # Extract JSON using robust method
                transform_sql = extract_json_from_response(response.content)
                
                if transform_sql is None:
                    raise ValueError("Could not extract valid JSON from response")
                
                # Validate structure
                if 'transformations' not in transform_sql:
                    raise ValueError("Transform SQL missing 'transformations' key")
                
                state['transformation_sql'] = transform_sql
                state['status'] = 'transform_sql_ready'
                print(f"✅ Generated SQL for {len(transform_sql['transformations'])} tables")
                return state
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Attempt {attempt + 1} failed, retrying... Error: {str(e)[:200]}")
                    continue
                else:
                    state['status'] = 'error'
                    error_msg = f"Transform SQL generation failed after {max_retries} attempts: {str(e)}"
                    state['errors'] = [error_msg]
                    print(f"❌ Error: {error_msg}")
                    # Print first 500 chars of response for debugging
                    if 'response' in locals():
                        print(f"Response preview: {response.content[:500]}...")
        return state
    
    # Node 6: Execute transformations using SQL Agent
    def load_data_node(state: WorkflowState) -> WorkflowState:
        print(f"\n📊 Loading data using SQL Agent...")
        try:
            transformations = state['transformation_sql']['transformations']
            file_id = state['file_id']
            
            # Sort by order
            transformations.sort(key=lambda x: x.get('order', 999))
            
            # Rate limiting: Process in batches
            batch_size = 5  # Execute 5 transformations per batch
            delay_between_batches = 2  # Wait 2 seconds between batches
            
            print(f"Loading data for {len(transformations)} tables in batches of {batch_size}...")
            
            # Split into batches
            batches = [transformations[i:i + batch_size] for i in range(0, len(transformations), batch_size)]
            
            for batch_num, batch in enumerate(batches, 1):
                print(f"Processing data loading batch {batch_num}/{len(batches)} ({len(batch)} tables)...")
                
                # Build instruction for this batch
                sql_instructions = f"""Execute these SQL transformation queries in order to load data from raw_tableau_files (id={file_id}) into relational tables.

IMPORTANT: 
1. Execute queries in the exact order given
2. Replace :file_id with {file_id}
3. For queries with RETURNING clause, capture the returned ID and use it in subsequent queries
4. Track parent IDs: After each INSERT with RETURNING, store the ID to use in child table inserts

Here are the transformation queries for this batch:

"""
                
                for i, transform in enumerate(batch, 1):
                    global_idx = (batch_num - 1) * batch_size + i
                    sql_instructions += f"\n--- Query {global_idx}: Load {transform['table_name']} ---\n"
                    sql_instructions += f"{transform['sql']}\n"
                
                sql_instructions += f"""

Execute all queries in this batch and report:
1. How many rows were inserted into each table
2. Any errors encountered
"""
                
                # Add delay before agent call to respect rate limits
                if batch_num > 1:
                    print(f"Waiting {delay_between_batches} seconds to respect rate limits...")
                    time.sleep(delay_between_batches)
                
                result = sql_agent.invoke({"input": sql_instructions})
                print(f"Batch {batch_num} completed: {result['output'][:200]}...")
            
            print(f"✅ Data loading completed for all {len(transformations)} tables")
            
            db_manager.mark_as_processed(file_id)
            state['status'] = 'completed'
            
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Data loading failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Build workflow graph
    workflow = StateGraph(WorkflowState)
    
    workflow.add_node("store_raw", store_raw_node)
    workflow.add_node("analyze", analyze_structure_node)
    workflow.add_node("design_schema", design_schema_node)
    workflow.add_node("create_tables", create_tables_node)
    workflow.add_node("generate_transform_sql", generate_transform_sql_node)
    workflow.add_node("load_data", load_data_node)
    
    workflow.set_entry_point("store_raw")
    workflow.add_edge("store_raw", "analyze")
    workflow.add_edge("analyze", "design_schema")
    workflow.add_edge("design_schema", "create_tables")
    workflow.add_edge("create_tables", "generate_transform_sql")
    workflow.add_edge("generate_transform_sql", "load_data")
    workflow.add_edge("load_data", END)
    
    return workflow.compile()
