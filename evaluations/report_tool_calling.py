"""
Tableau to Looker Migration Complexity Analysis - Using Function Calling Approach

This version uses structured tools (function calling) instead of prompt-based pattern matching.
The LLM can call predefined functions to classify fields, making the process more deterministic.

BENEFITS:
1. More deterministic - functions are called explicitly
2. Better control - we define exact logic for classification
3. Easier debugging - can see which functions were called
4. Structured output - guaranteed valid JSON via Pydantic models
5. Hybrid approach - combines regex pattern matching with LLM reasoning
"""

import json
import re
from typing import TypedDict, Dict, Any, List, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from pydantic import BaseModel, Field

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

# ============================================================================
# 1. CONFIGURATION
# ============================================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tableau_migration",
    "user": "roobar",
    "password": "postgres",
}
password = quote_plus(DB_CONFIG["password"])
DATABASE_URI = (
    f"postgresql://{DB_CONFIG['user']}:{password}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

engine = create_engine(DATABASE_URI)

# LLM (for agents that don't use tools)
llm = ChatVertexAI(model="gemini-2.0-flash-001", temperature=0)

# LLM with function calling enabled (for field agent with tools)
llm_with_tools = None  # Will be set after tools are defined

# ============================================================================
# 2. PYDANTIC MODELS FOR STRUCTURED OUTPUT
# ============================================================================

class FieldClassification(BaseModel):
    """Structured output for field classification"""
    field_id: str = Field(description="The ID of the field being classified")
    complexity_driver: str = Field(
        description="One of: LOD, Table Calculation, Date Function, Aggregation, Arithmetic / Logic, Simple, None"
    )
    score: int = Field(description="Complexity score: LOD=10, Table Calculation=5, Date Function=2, Aggregation=1, Arithmetic/Logic=1, Simple=0, None=0")
    confidence: float = Field(description="Confidence level 0.0-1.0", ge=0.0, le=1.0)
    reasoning: str = Field(description="Brief explanation of why this classification was chosen")


class DatasourceResult(BaseModel):
    """Structured output for datasource with fields"""
    datasource_id: str
    name: Optional[str] = None
    caption: Optional[str] = None
    complexity_score: int = Field(description="Sum of all field scores in this datasource")
    fields: List[FieldClassification]


class ParameterResult(BaseModel):
    """Structured output for parameter"""
    parameter_id: str
    name: str
    data_type: Optional[str] = None
    default_value: Optional[str] = None
    score: int = Field(default=5, description="Parameters always score 5 for migration complexity")


class FieldAnalysisResult(BaseModel):
    """Complete field analysis result"""
    datasources: List[DatasourceResult]
    parameters: List[ParameterResult]


# ============================================================================
# 3. DETERMINISTIC PATTERN MATCHING FUNCTIONS (TOOLS)
# ============================================================================

@tool
def detect_lod_expression(formula: str) -> Dict[str, Any]:
    """
    Detect if a Tableau formula contains LOD (Level of Detail) expressions.
    
    LOD expressions in Tableau use curly braces: { FIXED, { INCLUDE, { EXCLUDE
    
    Args:
        formula: The Tableau formula to analyze
        
    Returns:
        Dictionary with 'is_lod' (bool), 'lod_type' (str), and 'confidence' (float)
    """
    if not formula:
        return {"is_lod": False, "lod_type": None, "confidence": 1.0}
    
    formula_upper = formula.upper()
    
    # Check for LOD patterns
    patterns = {
        "FIXED": r'\{[^}]*FIXED',
        "INCLUDE": r'\{[^}]*INCLUDE',
        "EXCLUDE": r'\{[^}]*EXCLUDE'
    }
    
    for lod_type, pattern in patterns.items():
        if re.search(pattern, formula_upper, re.IGNORECASE):
            return {
                "is_lod": True,
                "lod_type": lod_type,
                "confidence": 0.95
            }
    
    return {"is_lod": False, "lod_type": None, "confidence": 1.0}


@tool
def detect_table_calculation(formula: str) -> Dict[str, Any]:
    """
    Detect if a Tableau formula contains table calculation functions.
    
    Table calculations include: LOOKUP, WINDOW_, RUNNING_, INDEX, RANK, etc.
    
    Args:
        formula: The Tableau formula to analyze
        
    Returns:
        Dictionary with 'is_table_calc' (bool), 'function_type' (str), and 'confidence' (float)
    """
    if not formula:
        return {"is_table_calc": False, "function_type": None, "confidence": 1.0}
    
    formula_upper = formula.upper()
    
    # Table calculation patterns
    patterns = {
        "LOOKUP": r'\bLOOKUP\s*\(',
        "WINDOW": r'\bWINDOW_\w+',
        "RUNNING": r'\bRUNNING_\w+',
        "INDEX": r'\bINDEX\s*\(',
        "RANK": r'\bRANK\s*\(',
        "FIRST": r'\bFIRST\s*\(',
        "LAST": r'\bLAST\s*\(',
        "PREVIOUS_VALUE": r'\bPREVIOUS_VALUE\s*\(',
    }
    
    for func_type, pattern in patterns.items():
        if re.search(pattern, formula_upper):
            return {
                "is_table_calc": True,
                "function_type": func_type,
                "confidence": 0.9
            }
    
    return {"is_table_calc": False, "function_type": None, "confidence": 1.0}


@tool
def detect_date_function(formula: str) -> Dict[str, Any]:
    """
    Detect if a Tableau formula contains date functions.
    
    Date functions include: DATEADD, DATEPART, DATETRUNC, DATE, YEAR, MONTH, etc.
    
    Args:
        formula: The Tableau formula to analyze
        
    Returns:
        Dictionary with 'is_date_func' (bool), 'function_type' (str), and 'confidence' (float)
    """
    if not formula:
        return {"is_date_func": False, "function_type": None, "confidence": 1.0}
    
    formula_upper = formula.upper()
    
    # Date function patterns
    patterns = {
        "DATEADD": r'\bDATEADD\s*\(',
        "DATEPART": r'\bDATEPART\s*\(',
        "DATETRUNC": r'\bDATETRUNC\s*\(',
        "DATE": r'\bDATE\s*\(',
        "YEAR": r'\bYEAR\s*\(',
        "MONTH": r'\bMONTH\s*\(',
        "DAY": r'\bDAY\s*\(',
        "WEEK": r'\bWEEK\s*\(',
        "QUARTER": r'\bQUARTER\s*\(',
    }
    
    for func_type, pattern in patterns.items():
        if re.search(pattern, formula_upper):
            return {
                "is_date_func": True,
                "function_type": func_type,
                "confidence": 0.85
            }
    
    return {"is_date_func": False, "function_type": None, "confidence": 1.0}


@tool
def detect_aggregation(formula: str) -> Dict[str, Any]:
    """
    Detect if a Tableau formula contains aggregation functions.
    
    Aggregations include: SUM, AVG, COUNT, MIN, MAX, etc.
    
    Args:
        formula: The Tableau formula to analyze
        
    Returns:
        Dictionary with 'is_aggregation' (bool), 'function_type' (str), and 'confidence' (float)
    """
    if not formula:
        return {"is_aggregation": False, "function_type": None, "confidence": 1.0}
    
    formula_upper = formula.upper()
    
    # Aggregation patterns
    patterns = {
        "SUM": r'\bSUM\s*\(',
        "AVG": r'\bAVG\s*\(',
        "AVERAGE": r'\bAVERAGE\s*\(',
        "COUNT": r'\bCOUNT\s*\(',
        "COUNTD": r'\bCOUNTD\s*\(',
        "MIN": r'\bMIN\s*\(',
        "MAX": r'\bMAX\s*\(',
        "STDEV": r'\bSTDEV\s*\(',
        "VAR": r'\bVAR\s*\(',
    }
    
    for func_type, pattern in patterns.items():
        if re.search(pattern, formula_upper):
            return {
                "is_aggregation": True,
                "function_type": func_type,
                "confidence": 0.8
            }
    
    return {"is_aggregation": False, "function_type": None, "confidence": 1.0}


@tool
def detect_arithmetic_logic(formula: str) -> Dict[str, Any]:
    """
    Detect if a Tableau formula contains arithmetic or logic operations.
    
    Includes: IF, CASE, AND, OR, +, -, *, /, etc.
    
    Args:
        formula: The Tableau formula to analyze
        
    Returns:
        Dictionary with 'is_arithmetic_logic' (bool), 'operation_type' (str), and 'confidence' (float)
    """
    if not formula:
        return {"is_arithmetic_logic": False, "operation_type": None, "confidence": 1.0}
    
    formula_upper = formula.upper()
    
    # Logic patterns (higher priority)
    logic_patterns = {
        "IF": r'\bIF\s+',
        "CASE": r'\bCASE\s+',
        "THEN": r'\bTHEN\s+',
        "ELSE": r'\bELSE\s+',
        "END": r'\bEND\b',
        "AND": r'\bAND\b',
        "OR": r'\bOR\b',
        "NOT": r'\bNOT\b',
    }
    
    for op_type, pattern in logic_patterns.items():
        if re.search(pattern, formula_upper):
            return {
                "is_arithmetic_logic": True,
                "operation_type": op_type,
                "confidence": 0.85
            }
    
    # Arithmetic patterns (lower priority, only if no logic found)
    arithmetic_patterns = {
        "DIVISION": r'[^/]/[^/]',  # Division but not // (comment)
        "MULTIPLICATION": r'\*',
        "ADDITION": r'\+',
        "SUBTRACTION": r'[^-]-\d',  # Subtraction but not negative number
    }
    
    for op_type, pattern in arithmetic_patterns.items():
        if re.search(pattern, formula):
            return {
                "is_arithmetic_logic": True,
                "operation_type": op_type,
                "confidence": 0.7
            }
    
    return {"is_arithmetic_logic": False, "operation_type": None, "confidence": 1.0}


@tool
def classify_field_complexity(
    field_id: str,
    formula: Optional[str],
    is_calculated: bool
) -> Dict[str, Any]:
    """
    Classify a field's complexity by calling all detection functions in priority order.
    
    Priority order (highest to lowest):
    1. LOD (score 10)
    2. Table Calculation (score 5)
    3. Date Function (score 2)
    4. Aggregation (score 1)
    5. Arithmetic/Logic (score 1)
    6. Simple (score 0) - has formula but no patterns matched
    7. None (score 0) - no formula and not calculated
    
    Args:
        field_id: The ID of the field
        formula: The Tableau formula (can be None)
        is_calculated: Whether the field is calculated
        
    Returns:
        Dictionary with classification results
    """
    # If no formula and not calculated, it's "None"
    if not formula and not is_calculated:
        return {
            "field_id": field_id,
            "complexity_driver": "None",
            "score": 0,
            "confidence": 1.0,
            "reasoning": "Field has no formula and is not calculated"
        }
    
    # If no formula but is calculated, something is wrong - default to Simple
    if not formula:
        return {
            "field_id": field_id,
            "complexity_driver": "Simple",
            "score": 0,
            "confidence": 0.5,
            "reasoning": "Field is marked as calculated but has no formula"
        }
    
    # Check in priority order
    lod_result = detect_lod_expression.invoke({"formula": formula})
    if lod_result["is_lod"]:
        return {
            "field_id": field_id,
            "complexity_driver": "LOD",
            "score": 10,
            "confidence": lod_result["confidence"],
            "reasoning": f"Contains LOD expression: {lod_result['lod_type']}"
        }
    
    table_calc_result = detect_table_calculation.invoke({"formula": formula})
    if table_calc_result["is_table_calc"]:
        return {
            "field_id": field_id,
            "complexity_driver": "Table Calculation",
            "score": 5,
            "confidence": table_calc_result["confidence"],
            "reasoning": f"Contains table calculation: {table_calc_result['function_type']}"
        }
    
    date_func_result = detect_date_function.invoke({"formula": formula})
    if date_func_result["is_date_func"]:
        return {
            "field_id": field_id,
            "complexity_driver": "Date Function",
            "score": 2,
            "confidence": date_func_result["confidence"],
            "reasoning": f"Contains date function: {date_func_result['function_type']}"
        }
    
    agg_result = detect_aggregation.invoke({"formula": formula})
    if agg_result["is_aggregation"]:
        return {
            "field_id": field_id,
            "complexity_driver": "Aggregation",
            "score": 1,
            "confidence": agg_result["confidence"],
            "reasoning": f"Contains aggregation: {agg_result['function_type']}"
        }
    
    arithmetic_result = detect_arithmetic_logic.invoke({"formula": formula})
    if arithmetic_result["is_arithmetic_logic"]:
        return {
            "field_id": field_id,
            "complexity_driver": "Arithmetic / Logic",
            "score": 1,
            "confidence": arithmetic_result["confidence"],
            "reasoning": f"Contains arithmetic/logic: {arithmetic_result['operation_type']}"
        }
    
    # Has formula but no patterns matched
    return {
        "field_id": field_id,
        "complexity_driver": "Simple",
        "score": 0,
        "confidence": 0.8,
        "reasoning": "Formula exists but no complex patterns detected"
    }


# Create list of tools for the LLM
tools = [
    detect_lod_expression,
    detect_table_calculation,
    detect_date_function,
    detect_aggregation,
    detect_arithmetic_logic,
    classify_field_complexity,
]

# Bind tools to LLM (create a new instance for tool calling)
llm_for_tools = ChatVertexAI(model="gemini-2.0-flash-001", temperature=0)
llm_with_tools = llm_for_tools.bind_tools(tools)

# ============================================================================
# 4. STATE DEFINITION
# ============================================================================

class MigrationState(TypedDict):
    workbook_name: str
    workbook_id: str
    
    # Partial Results
    field_data: Dict[str, Any]
    viz_data: Dict[str, Any]
    layout_data: Dict[str, Any]
    
    # Validation Results
    field_validation: Dict[str, Any]
    viz_validation: Dict[str, Any]
    layout_validation: Dict[str, Any]
    
    # Final Output
    final_report: Dict[str, Any]
    html_report: str


# ============================================================================
# 5. HELPERS
# ============================================================================

def convert_uuids(obj):
    """Recursively convert UUID objects to strings."""
    if isinstance(obj, dict):
        return {k: convert_uuids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_uuids(i) for i in obj]
    if hasattr(obj, "__class__") and obj.__class__.__name__ == "UUID":
        return str(obj)
    return obj


def run_query(sql: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Run SQL, return list of dicts with UUID already stringified."""
    params = params or {}
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = [convert_uuids(dict(row._mapping)) for row in result]
    return rows


def extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM output."""
    # Try <JSON>...</JSON> block
    try:
        m = re.search(r"<JSON>(.*?)</JSON>", text, re.DOTALL | re.IGNORECASE)
        if m:
            block = m.group(1).strip()
            return json.loads(block)
    except Exception:
        pass
    
    # Fallback: first {...}
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    
    return {}


def extract_html(text: str) -> str:
    """Extract HTML from LLM output."""
    text = re.sub(r"```html\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text, re.MULTILINE)
    
    html_match = re.search(r"(<!DOCTYPE.*?</html>)", text, re.DOTALL | re.IGNORECASE)
    if html_match:
        return html_match.group(1)
    
    if "<html" in text.lower() or "<!doctype" in text.lower():
        return text.strip()
    
    return text.strip()


# ============================================================================
# 6. FIELD AGENT WITH HYBRID APPROACH (LLM Agent + Tool Calling)
# ============================================================================

def field_agent_node_hybrid(state: MigrationState):
    """
    Hybrid Field Agent: Combines LLM reasoning with deterministic tool calling.
    
    Strategy:
    1. For simple/clear cases: Use tools directly (fast, deterministic)
    2. For complex/ambiguous cases: Let LLM agent use tools (reasoning + tools)
    3. Best of both worlds: Speed + Intelligence
    """
    print("🤖 Running Field Logic Agent (Hybrid: LLM Agent + Tool Calling)...")
    wb_id = state["workbook_id"]
    if not wb_id:
        return {"field_data": {}}
    
    # Get data from database
    datasources = run_query(
        """
        SELECT id, name, caption, connection_type, db_name, db_schema, is_extract
        FROM datasources
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    fields = run_query(
        """
        SELECT f.id,
               f.datasource_id,
               f.caption,
               f.internal_name,
               f.formula,
               f.data_type,
               f.role,
               f.is_calculated
        FROM fields f
        JOIN datasources d ON d.id = f.datasource_id
        WHERE d.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    try:
        parameters = run_query(
            """
            SELECT id, workbook_id, name, data_type, default_value
            FROM parameters
            WHERE workbook_id = :wb;
            """,
            {"wb": wb_id},
        )
    except Exception:
        parameters = []
    
    # HYBRID APPROACH: Smart routing between direct tools and LLM agent
    print("   📊 Classifying fields using hybrid approach (tools + LLM agent)...")
    
    classified_fields = {}
    complex_fields = []  # Fields that need LLM reasoning
    
    # Step 1: Try direct tool classification for all fields
    for field in fields:
        field_id = str(field["id"])
        formula = field.get("formula")
        is_calculated = field.get("is_calculated", False)
        
        # Quick classification using tools
        classification = classify_field_complexity.invoke({
            "field_id": field_id,
            "formula": formula,
            "is_calculated": is_calculated
        })
        
        # If confidence is high, use it directly
        if classification["confidence"] >= 0.85:
            classified_fields[field_id] = classification
        else:
            # Low confidence or complex case - mark for LLM agent
            complex_fields.append({
                "field": field,
                "initial_classification": classification
            })
    
    print(f"   ✅ Direct tool classification: {len(classified_fields)} fields")
    print(f"   🤔 Complex cases requiring LLM: {len(complex_fields)} fields")
    
    # Step 2: Use LLM agent with tools for complex cases
    if complex_fields:
        print("   🧠 Using LLM agent with tools for complex cases...")
        
        system_prompt = """You are a Tableau field complexity analyzer for Tableau to Looker migration assessment.

Your task: Classify field complexity using the provided tools.

AVAILABLE TOOLS:
- detect_lod_expression: Detects LOD expressions ({ FIXED, { INCLUDE, { EXCLUDE)
- detect_table_calculation: Detects table calculations (RUNNING_, WINDOW_, LOOKUP, etc.)
- detect_date_function: Detects date functions (DATEADD, DATEPART, etc.)
- detect_aggregation: Detects aggregations (SUM, AVG, COUNT, etc.)
- detect_arithmetic_logic: Detects arithmetic/logic (IF, CASE, +, -, *, /)
- classify_field_complexity: Master classification function (calls all above in priority order)

CLASSIFICATION PRIORITY (highest to lowest):
1. LOD (score 10) - Most complex for Looker migration
2. Table Calculation (score 5)
3. Date Function (score 2)
4. Aggregation (score 1)
5. Arithmetic / Logic (score 1)
6. Simple (score 0) - Has formula but no complex patterns
7. None (score 0) - No formula and not calculated

INSTRUCTIONS:
- For each field, use the classify_field_complexity tool
- If the tool result seems incorrect or ambiguous, you can call individual detection tools to investigate
- Provide reasoning for your final classification
- Consider the context: This is for Tableau to Looker migration complexity assessment

Return the classification in this format:
{
    "field_id": "...",
    "complexity_driver": "LOD | Table Calculation | Date Function | Aggregation | Arithmetic / Logic | Simple | None",
    "score": number,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}
"""
        
        # Process complex fields with LLM agent
        for item in complex_fields:
            field = item["field"]
            field_id = str(field["id"])
            initial_classification = item["initial_classification"]
            
            prompt = f"""Classify this Tableau field for migration complexity assessment:

Field ID: {field_id}
Name: {field.get('caption') or field.get('internal_name')}
Formula: {field.get('formula') or 'None'}
Is Calculated: {field.get('is_calculated', False)}
Data Type: {field.get('data_type')}
Role: {field.get('role')}

Initial tool classification (low confidence):
- Driver: {initial_classification['complexity_driver']}
- Score: {initial_classification['score']}
- Confidence: {initial_classification['confidence']:.2f}
- Reasoning: {initial_classification['reasoning']}

Please use the classify_field_complexity tool to get a proper classification.
If needed, you can also call individual detection tools to investigate specific patterns.
Provide your final classification with reasoning."""
            
            try:
                # LLM agent with tools - use agent executor pattern
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt)
                ]
                
                # Agent loop: LLM can call tools multiple times
                max_iterations = 3
                final_classification = None
                
                for iteration in range(max_iterations):
                    # Get LLM response
                    response = llm_with_tools.invoke(messages)
                    messages.append(response)
                    
                    # Check if LLM wants to call a tool
                    if hasattr(response, 'tool_calls') and response.tool_calls and len(response.tool_calls) > 0:
                        # Execute tool calls
                        tool_messages = []
                        for tool_call in response.tool_calls:
                            tool_name = tool_call.get('name', '')
                            tool_args = tool_call.get('args', {})
                            
                            # Find and execute the tool
                            tool_to_call = None
                            for t in tools:
                                if t.name == tool_name:
                                    tool_to_call = t
                                    break
                            
                            if tool_to_call:
                                try:
                                    tool_result = tool_to_call.invoke(tool_args)
                                    # Create ToolMessage for the response
                                    tool_messages.append(
                                        ToolMessage(
                                            content=json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result),
                                            tool_call_id=tool_call.get('id', '')
                                        )
                                    )
                                    
                                    # If this is the classify_field_complexity tool, use its result
                                    if tool_name == 'classify_field_complexity':
                                        final_classification = tool_result
                                        print(f"      ✅ Field {field_id}: {tool_result.get('complexity_driver', 'Unknown')} (LLM Agent + Tool)")
                                except Exception as tool_error:
                                    tool_messages.append(
                                        ToolMessage(
                                            content=f"Error: {str(tool_error)}",
                                            tool_call_id=tool_call.get('id', '')
                                        )
                                    )
                        
                        # Add tool results to messages for next iteration
                        messages.extend(tool_messages)
                    else:
                        # LLM provided final answer (no more tool calls)
                        # Try to extract classification from response content
                        response_text = response.content if hasattr(response, 'content') else str(response)
                        
                        # Try to parse JSON from response
                        try:
                            extracted = extract_json(response_text)
                            if extracted and 'complexity_driver' in extracted:
                                final_classification = extracted
                                print(f"      ✅ Field {field_id}: {extracted.get('complexity_driver')} (LLM Agent reasoning)")
                            else:
                                # Use initial classification
                                final_classification = initial_classification
                                print(f"      ⚠️  Field {field_id}: LLM response unclear, using initial classification")
                        except:
                            # Use initial classification
                            final_classification = initial_classification
                            print(f"      ⚠️  Field {field_id}: Could not parse LLM response, using initial classification")
                        
                        break  # Exit loop
                
                # Use final classification or fallback to initial
                if final_classification:
                    classified_fields[field_id] = final_classification
                else:
                    classified_fields[field_id] = initial_classification
                    print(f"      ⚠️  Field {field_id}: No final classification, using initial")
                    
            except Exception as e:
                print(f"      ❌ Error with LLM agent for field {field_id}: {e}")
                # Fallback to initial classification
                classified_fields[field_id] = initial_classification
    
    
    # Step 3: Build final result structure
    # Group fields by datasource
    datasource_results = []
    for ds in datasources:
        ds_id = str(ds["id"])
        ds_fields = [
            f for f in fields 
            if str(f.get("datasource_id")) == ds_id
        ]
        
        field_classifications = []
        ds_complexity_score = 0
        
        for field in ds_fields:
            field_id = str(field["id"])
            if field_id in classified_fields:
                classification = classified_fields[field_id]
                field_classifications.append(FieldClassification(
                    field_id=field_id,
                    complexity_driver=classification["complexity_driver"],
                    score=classification["score"],
                    confidence=classification["confidence"],
                    reasoning=classification["reasoning"]
                ))
                ds_complexity_score += classification["score"]
        
        datasource_results.append(DatasourceResult(
            datasource_id=ds_id,
            name=ds.get("name"),
            caption=ds.get("caption"),
            complexity_score=ds_complexity_score,
            fields=field_classifications
        ))
    
    # Process parameters
    parameter_results = []
    for param in parameters:
        parameter_results.append(ParameterResult(
            parameter_id=str(param["id"]),
            name=param.get("name", ""),
            data_type=param.get("data_type"),
            default_value=param.get("default_value"),
            score=5
        ))
    
    # Convert to dict for state
    result = FieldAnalysisResult(
        datasources=datasource_results,
        parameters=parameter_results
    )
    
    # Convert Pydantic model to dict
    result_dict = result.model_dump()
    
    # Convert datasources and fields to match expected format
    for ds in result_dict["datasources"]:
        # Convert datasource_id to id
        if "datasource_id" in ds:
            ds["id"] = ds.pop("datasource_id")
        
        for field in ds["fields"]:
            # Add additional field metadata from original field data
            original_field = next(
                (f for f in fields if str(f["id"]) == field.get("field_id") or str(f["id"]) == field.get("id")),
                None
            )
            if original_field:
                field["name"] = original_field.get("caption") or original_field.get("internal_name")
                field["data_type"] = original_field.get("data_type")
                field["role"] = original_field.get("role")
                field["is_calculated"] = original_field.get("is_calculated")
                field["formula"] = original_field.get("formula")
                # Ensure id is set (not field_id)
                if "field_id" in field:
                    field["id"] = field.pop("field_id")
                elif "id" not in field:
                    field["id"] = str(original_field["id"])
                # Convert complexity_driver to complexity_drivers (expected format)
                if "complexity_driver" in field and "complexity_drivers" not in field:
                    field["complexity_drivers"] = field.pop("complexity_driver")
    
    # Convert parameter_id to id for parameters
    for param in result_dict.get("parameters", []):
        if "parameter_id" in param:
            param["id"] = param.pop("parameter_id")
    
    print(f"   ✅ Total classified: {len(classified_fields)} fields")
    print(f"      - Direct tools: {len(classified_fields) - len(complex_fields)}")
    print(f"      - LLM + Tools: {len(complex_fields)}")
    return {"field_data": convert_uuids(result_dict)}


# ============================================================================
# 7. MAIN FIELD AGENT (Hybrid Approach)
# ============================================================================

def field_agent_node(state: MigrationState):
    """
    Main field agent - uses hybrid approach (LLM agent + tool calling).
    Combines deterministic pattern matching with LLM reasoning for best results.
    """
    return field_agent_node_hybrid(state)


# ============================================================================
# 8. PROMPTS FOR OTHER AGENTS (Viz, Layout, HTML)
# ============================================================================

VIZ_AGENT_PROMPT = """
You are a strict **Tableau Visualization Analyzer** for **Tableau to Looker Migration Assessment**.  
Output JSON only. No markdown. No explanation.

---------------------------------------------------------------------
### CONTEXT: TABLEAU TO LOOKER MIGRATION

You are analyzing Tableau visualizations to assess migration complexity to Looker (Google Cloud's BI platform).
The complexity scores reflect how difficult it will be to recreate each visualization type in Looker.

**Why visualization types matter for Looker migration:**
- **Complex visualizations** (heatmap, gantt, path, polygon) are harder to recreate in Looker and may require custom visualizations or workarounds
- **Maps** require different geographic data handling in Looker
- **Simple charts** (bar, line, pie) are straightforward to migrate
- **Dual-axis charts** add complexity as Looker handles multiple measures differently
- **Field complexity** (LOD, table calculations) compounds visualization complexity

Your scoring should reflect the **migration effort** required to recreate the visualization in Looker, not just generic complexity.

---------------------------------------------------------------------
### INPUT
{
  "worksheets": [...],
  "worksheet_elements": [...],
  "fields": [...]  // Fields from datasources used by worksheets
}

Each worksheet_element has:
- worksheet_id
- mark_class (string)
- pane_id
- element_type
- encoding
- style

Each field has:
- id
- datasource_id
- name/caption
- formula
- complexity_drivers (LOD, Table Calculation, Date Function, etc.)
- score (from field analysis)

---------------------------------------------------------------------
### SCORING RULES

**Step 1: Calculate Visualization Score (viz_score) for Tableau to Looker Migration**

Base score by viz type (reflecting migration difficulty to Looker):

| Viz Type   | Score | Migration Challenge to Looker |
|------------|--------|------------------------------|
| bar        | 1     | Easy - standard chart type in Looker |
| line       | 1     | Easy - standard chart type in Looker |
| area       | 1     | Easy - standard chart type in Looker |
| pie        | 1     | Easy - standard chart type in Looker |
| text       | 1     | Easy - text tiles in Looker |
| scatter    | 1     | Easy - scatter plot in Looker |
| map        | 3     | Moderate - requires geographic data setup in Looker |
| polygon    | 8     | Complex - may require custom visualization or workaround |
| heatmap    | 10    | Complex - difficult to recreate exactly in Looker |
| gantt      | 10    | Complex - may require custom visualization in Looker |
| path       | 10    | Complex - difficult to recreate in Looker's standard charts |
| none       | 0     | No visualization complexity |

PRIMARY viz type = the mark_class with HIGHEST score.

Dual-axis = true IF:
- Any mark_class in {bar, line, area} appears MORE THAN ONCE inside same worksheet.

viz_score = base_chart_score + 3 IF dual-axis = true

**Step 2: Calculate Field Score (field_score)**

For each worksheet:
1. Find all fields from the worksheet's datasource_id
2. Sum the field scores: field_score = SUM(all field scores for that datasource)

**Step 3: Calculate Combined Complexity Score**

complexity_score = viz_score + field_score

This represents the TOTAL complexity of the worksheet (both visualization type AND the complexity of fields used).

---------------------------------------------------------------------
### OUTPUT JSON SCHEMA (STRICT)

You MUST return:

<JSON>
{
  "worksheets": [
    {
      "id": "string",
      "name": "string",
      "datasource_id": "string or null",
      "viz_type": "string",
      "mark_classes": ["string"],
      "dual_axis": boolean,
      "viz_score": number,
      "field_score": number,
      "complexity_score": number,
      "fields": [
        {
          "id": "string",
          "name": "string",
          "formula": "string or null",
          "complexity_drivers": "string or null",
          "score": number
        }
      ]
    }
  ]
}
</JSON>

Rules:
- Never omit keys.
- mark_classes must be a deduped list.
- viz_type must be lowercase.
- fields array should contain all fields from the worksheet's datasource.
- complexity_score = viz_score + field_score
- If no elements exist → viz_type="none", dual_axis=false, viz_score=0.
- If no fields found → field_score=0, fields=[].
"""

LAYOUT_AGENT_PROMPT = """
You are a strict **Tableau Dashboard Layout Analyzer** for **Tableau to Looker Migration Assessment**.  
Output JSON ONLY between <JSON> and </JSON>.

---------------------------------------------------------------------
### CONTEXT: TABLEAU TO LOOKER MIGRATION

You are analyzing Tableau dashboard layouts to assess migration complexity to Looker (Google Cloud's BI platform).
The complexity scores reflect how difficult it will be to recreate the dashboard layout and structure in Looker.

**Why dashboard layout matters for Looker migration:**
- **Floating objects** in Tableau are difficult to replicate in Looker's grid-based layout system
- **Tiled layouts** are easier to migrate as Looker uses a similar grid system
- **High component counts** require more manual work to recreate in Looker dashboards
- **Complex zone structures** may need restructuring for Looker's layout constraints

Your scoring should reflect the **migration effort** required to recreate the dashboard layout in Looker, not just generic complexity.

---------------------------------------------------------------------
### INPUT
{
  "dashboards": [...]
}

Each dashboard:
- id
- name
- width
- height
- zones (null OR JSON array or string containing JSON)

Each zone may include:
- floating or is_floating (boolean)
- worksheet OR worksheet_id (sheet reference)
- type

---------------------------------------------------------------------
### SCORING RULES FOR TABLEAU TO LOOKER MIGRATION

Start with:
layout_score = 0 if zones = null or empty  
layout_score = 1 if zones exist AND count ≥ 1

Then (reflecting migration difficulty to Looker):
- If ANY zone has floating=true → add +8  
  * **Why**: Floating objects are very difficult to replicate in Looker's grid-based layout system
- If number_of_zones > 15 → add +5
  * **Why**: High component counts require significant manual work to recreate in Looker dashboards  

You MUST compute:
- is_floating
- floating_count
- component_count
- contained_sheet_ids = list of worksheet IDs referenced

---------------------------------------------------------------------
### OUTPUT JSON SCHEMA

<JSON>
{
  "dashboards": [
    {
      "id": "string",
      "name": "string",
      "width": number or null,
      "height": number or null,
      "is_floating": boolean,
      "floating_count": number,
      "component_count": number,
      "contained_sheet_ids": ["string"],
      "layout_score": number
    }
  ]
}
</JSON>

Rules:
- Never omit keys.
- If no zones → contained_sheet_ids=[], component_count=0.
- Never wrap in markdown.
"""

HTML_AGENT_PROMPT = """
You are a **Professional HTML Report Generator** for **Tableau to Looker Migration Assessment**.

Your task is to convert a JSON complexity analysis report into a beautiful, professional HTML report that matches the exact style of the reference design.

**CONTEXT**: This report assesses the complexity of migrating Tableau workbooks to Looker (Google Cloud's BI platform). 
All complexity scores reflect the effort and difficulty required for this specific migration, not generic complexity.

---------------------------------------------------------------------
### INPUT JSON STRUCTURE

{
  "workbook": {
    "name": "string",
    "id": "string",
    "summary": {
      "total_complexity_score": number,
      "worksheet_score": number,
      "worksheet_viz_score": number,
      "worksheet_field_score": number,
      "datasource_field_score": number,
      "layout_score": number,
      "parameter_score": number,
      "migration_category": "Low | Medium | High"
    },
    "datasources": [...],
    "parameters": [...],
    "worksheets": [...],
    "dashboards": [...],
    "validation": {
      "field_agent": {
        "valid": boolean,
        "error_count": number,
        "warning_count": number
      },
      "viz_agent": {
        "valid": boolean,
        "error_count": number,
        "warning_count": number
      },
      "layout_agent": {
        "valid": boolean,
        "error_count": number,
        "warning_count": number
      }
    }
  }
}

---------------------------------------------------------------------
### HTML REQUIREMENTS - EXACT STYLE MATCH

1. **CSS Styling** (MUST match reference exactly):
   - Use 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif font family
   - Background: #f4f4f4 for body, #fff for container
   - Header h1 color: #007bff
   - Section h2 color: #007bff with border-bottom
   - Table headers: #f8f9fa background
   - Alternating row colors: #f8f9fa for even rows
   - Hover effect on table rows: #e9ecef background

2. **Summary Cards**:
   - Display as flex cards with border, padding, border-radius
   - Width: 250px each
   - Show: Total Complexity Score, Worksheet Score, Datasource Field Score, Migration Category
   - Migration Category badge: .badge.low (green), .badge.medium (orange), .badge.high (red)

3. **VALIDATION STATUS SECTION** (CRITICAL - Add this after summary):
   - Create a section with class "validation"
   - Display validation results in a clean table or cards
   - Show for each agent: field_agent, viz_agent, layout_agent
   - Display: Status (✅ PASSED / ❌ FAILED), Error Count, Warning Count
   - Use green badge for "valid: true", red badge for "valid: false"
   - Style it consistently with the rest of the report

4. **Datasources Table** (EXACT format):
   - Columns: Name, Caption, Complexity Score, Complexity Drivers
   - NO nested tables, NO field details
   - Complexity Drivers: Show as badge with class "complexity-driver" + type
   - Badge classes: .complexity-driver.lod (red), .complexity-driver.table-calculation (yellow), .complexity-driver.aggregation (blue), .complexity-driver.arithmetic (gray), .complexity-driver.none (green)
   - For each datasource, determine primary complexity driver from its fields (highest priority)

5. **Worksheets Table** (EXACT format):
   - Columns: Name, Viz Type, Complexity Score, Field, Formula, Complexity Drivers
   - Show the PRIMARY field used in the worksheet (first field or most complex)
   - Formula: Show the formula or "-" if null
   - **Complexity Drivers (CRITICAL LOGIC - MUST FOLLOW EXACTLY)**:
     * The complexity_score = viz_score + field_score
     * **NEVER show "None" if complexity_score > 0**
     * Determine the PRIMARY complexity driver using this priority:
     
     **Priority 1: If field_score > 0 AND field has complexity_drivers:**
       - Use the field's complexity_drivers (LOD, Table Calculation, Aggregation, Arithmetic / Logic, etc.)
       - This takes priority because field complexity is more specific
     
     **Priority 2: If viz_score > 0 AND field_score = 0:**
       - The complexity comes from the visualization type itself
       - Show the viz_type name capitalized as the complexity driver
       - Use badge class "complexity-driver viz-complex" (gray background #6c757d)
       - Examples:
         * heatmap → Show "Heatmap" with class "complexity-driver viz-complex"
         * gantt → Show "Gantt" with class "complexity-driver viz-complex"
         * polygon → Show "Polygon" with class "complexity-driver viz-complex"
         * map → Show "Map" with class "complexity-driver viz-complex"
         * bar, line, area, pie, text, scatter → If field_score=0, show viz_type name with "viz-complex" class
     
     **Priority 3: If both viz_score > 0 AND field_score > 0:**
       - Use the field's complexity_drivers (field complexity is more specific and actionable)
     
     **Priority 4: If both are 0:**
       - Show "None"
     
     **EXAMPLES:**
     * Worksheet with viz_score=10, field_score=0, complexity_score=10 → Show "Heatmap" or "Complex Viz" (NOT "None")
     * Worksheet with viz_score=1, field_score=1, complexity_score=2 → Show field's driver (e.g., "Aggregation")
     * Worksheet with viz_score=10, field_score=10, complexity_score=20 → Show field's driver (e.g., "LOD")
   - NO nested tables for fields

6. **Dashboards Table** (EXACT format):
   - Columns: Name, Component Count, Layout Score
   - Simple, clean table format

7. **Complexity Driver Badge Colors**:
   - LOD: #dc3545 (red) - class "complexity-driver lod"
   - Table Calculation: #ffc107 (yellow/orange) - class "complexity-driver table-calculation"
   - Date Function: #17a2b8 (blue) - class "complexity-driver date-function"
   - Aggregation: #007bff (blue) - class "complexity-driver aggregation"
   - Arithmetic / Logic: #6c757d (gray) - class "complexity-driver arithmetic"
   - None: #28a745 (green) - class "complexity-driver none"

8. **Footer**:
   - Simple centered footer with generation timestamp

---------------------------------------------------------------------
### CRITICAL RULES

1. **Datasources**: Show ONLY Name, Caption, Complexity Score, Complexity Drivers (as badge)
2. **Worksheets**: Show Name, Viz Type, Complexity Score, Field (single field name), Formula (or "-"), Complexity Drivers (as badge)
3. **Dashboards**: Show Name, Component Count, Layout Score
4. **Validation**: Show status for each agent with badges
5. **NO nested tables** in Datasources or Worksheets sections
6. **Match the exact CSS styling** from the reference

---------------------------------------------------------------------
Generate the complete HTML report now. Return ONLY the HTML, nothing else.
"""


# ============================================================================
# 9. SETUP AND VALIDATION NODES
# ============================================================================

def setup_node(state: MigrationState):
    """Resolve workbook_id from workbooks table."""
    print(f"🔍 Resolving ID for: {state['workbook_name']}")
    rows = run_query(
        "SELECT id FROM workbooks WHERE name = :name LIMIT 1;",
        {"name": state["workbook_name"]},
    )
    wb_id = rows[0]["id"] if rows else None
    print(f"✅ Found ID: {wb_id}")
    return {"workbook_id": wb_id}


def validate_field_agent_node(state: MigrationState):
    """
    Validator agent that verifies field_agent output against database.
    Checks for hallucinations and data accuracy.
    """
    print("🔍 Validating Field Agent Output...")
    wb_id = state["workbook_id"]
    field_data = state.get("field_data", {}) or {}
    
    if not wb_id or not field_data:
        return {"field_validation": {"valid": False, "errors": ["Missing workbook_id or field_data"]}}
    
    validation_errors = []
    validation_warnings = []
    corrected_data = {"datasources": [], "parameters": []}
    
    # Get actual data from database for comparison
    db_datasources = run_query(
        """
        SELECT id, name, caption, connection_type, db_name, db_schema, is_extract
        FROM datasources
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    db_fields = run_query(
        """
        SELECT f.id,
               f.datasource_id,
               f.caption,
               f.internal_name,
               f.formula,
               f.data_type,
               f.role,
               f.is_calculated
        FROM fields f
        JOIN datasources d ON d.id = f.datasource_id
        WHERE d.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    try:
        db_parameters = run_query(
            """
            SELECT id, workbook_id, name, data_type, default_value
            FROM parameters
            WHERE workbook_id = :wb;
            """,
            {"wb": wb_id},
        )
    except Exception:
        db_parameters = []
    
    # Create lookup maps from database
    db_datasource_map = {str(ds["id"]): ds for ds in db_datasources}
    db_field_map = {str(f["id"]): f for f in db_fields}
    db_parameter_map = {str(p["id"]): p for p in db_parameters}
    
    # Validate datasources
    agent_datasources = field_data.get("datasources", [])
    for agent_ds in agent_datasources:
        ds_id = str(agent_ds.get("id", ""))
        
        if ds_id not in db_datasource_map:
            validation_errors.append(f"❌ HALLUCINATION: Datasource ID {ds_id} does not exist in database")
            continue
        
        db_ds = db_datasource_map[ds_id]
        validated_ds = {
            "id": ds_id,
            "name": db_ds.get("name"),
            "caption": db_ds.get("caption"),
            "complexity_score": agent_ds.get("complexity_score", 0),
            "fields": []
        }
        
        # Validate fields within this datasource
        agent_fields = agent_ds.get("fields", [])
        for agent_field in agent_fields:
            field_id = str(agent_field.get("id", ""))
            
            if field_id not in db_field_map:
                validation_errors.append(f"❌ HALLUCINATION: Field ID {field_id} does not exist in database")
                continue
            
            db_field = db_field_map[field_id]
            
            # Verify field belongs to this datasource
            if str(db_field.get("datasource_id")) != ds_id:
                validation_warnings.append(f"⚠️  Field {field_id} belongs to different datasource in DB")
                continue
            
            # Verify formula matches exactly
            agent_formula = agent_field.get("formula")
            db_formula = db_field.get("formula")
            
            if agent_formula != db_formula:
                validation_errors.append(
                    f"❌ FORMULA MISMATCH: Field {field_id} - Agent: '{agent_formula}' vs DB: '{db_formula}'"
                )
                agent_field["formula"] = db_formula
            
            # Verify name/caption matches
            agent_name = agent_field.get("name")
            db_caption = db_field.get("caption")
            if agent_name != db_caption:
                validation_warnings.append(
                    f"⚠️  Field {field_id} name mismatch - Agent: '{agent_name}' vs DB: '{db_caption}'"
                )
                agent_field["name"] = db_caption
            
            # Keep agent's complexity analysis but use DB data for facts
            validated_field = {
                "id": field_id,
                "name": db_caption,
                "data_type": db_field.get("data_type"),
                "role": db_field.get("role"),
                "is_calculated": db_field.get("is_calculated"),
                "formula": db_formula,
                "complexity_drivers": agent_field.get("complexity_drivers"),
                "score": agent_field.get("score", 0)
            }
            validated_ds["fields"].append(validated_field)
        
        corrected_data["datasources"].append(validated_ds)
    
    # Validate parameters
    agent_parameters = field_data.get("parameters", [])
    for agent_param in agent_parameters:
        param_id = str(agent_param.get("id", ""))
        
        if param_id not in db_parameter_map:
            validation_errors.append(f"❌ HALLUCINATION: Parameter ID {param_id} does not exist in database")
            continue
        
        db_param = db_parameter_map[param_id]
        
        # Verify name matches
        agent_name = agent_param.get("name")
        db_name = db_param.get("name")
        if agent_name != db_name:
            validation_warnings.append(
                f"⚠️  Parameter {param_id} name mismatch - Agent: '{agent_name}' vs DB: '{db_name}'"
            )
        
        validated_param = {
            "id": param_id,
            "name": db_name,
            "data_type": db_param.get("data_type"),
            "default_value": db_param.get("default_value"),
            "score": agent_param.get("score", 5)
        }
        corrected_data["parameters"].append(validated_param)
    
    # Check for missing datasources/fields/parameters
    agent_ds_ids = {str(ds.get("id")) for ds in agent_datasources}
    db_ds_ids = set(db_datasource_map.keys())
    missing_ds = db_ds_ids - agent_ds_ids
    if missing_ds:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_ds)} datasource(s): {missing_ds}")
    
    agent_field_ids = set()
    for ds in agent_datasources:
        agent_field_ids.update(str(f.get("id")) for f in ds.get("fields", []))
    db_field_ids = set(db_field_map.keys())
    missing_fields = db_field_ids - agent_field_ids
    if missing_fields:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_fields)} field(s)")
    
    agent_param_ids = {str(p.get("id")) for p in agent_parameters}
    db_param_ids = set(db_parameter_map.keys())
    missing_params = db_param_ids - agent_param_ids
    if missing_params:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_params)} parameter(s)")
    
    is_valid = len(validation_errors) == 0
    
    validation_result = {
        "valid": is_valid,
        "errors": validation_errors,
        "warnings": validation_warnings,
        "corrected_data": corrected_data if validation_errors else None
    }
    
    if validation_errors:
        print(f"❌ Validation FAILED: {len(validation_errors)} error(s), {len(validation_warnings)} warning(s)")
        for err in validation_errors[:5]:
            print(f"   {err}")
    else:
        print(f"✅ Validation PASSED: {len(validation_warnings)} warning(s)")
        if validation_warnings:
            for warn in validation_warnings[:3]:
                print(f"   {warn}")
    
    # Replace field_data with corrected data if there were errors
    if validation_errors and corrected_data:
        return {
            "field_validation": validation_result,
            "field_data": corrected_data
        }
    
    return {"field_validation": validation_result}


# ============================================================================
# 10. VIZ AGENT AND VALIDATOR
# ============================================================================

def viz_agent_node(state: MigrationState):
    """LLM agent that scores visualization complexity by mark_class and includes fields."""
    print("🤖 Running Visualization Agent...")
    wb_id = state["workbook_id"]
    if not wb_id:
        return {"viz_data": {}}

    # Get worksheets
    worksheets = run_query(
        """
        SELECT id, workbook_id, name, datasource_id, columns_used, rows_used
        FROM worksheets
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    # Get worksheet elements
    elements = run_query(
        """
        SELECT we.id,
               we.worksheet_id,
               we.pane_id,
               we.mark_class,
               we.element_type,
               we.encoding,
               we.style
        FROM worksheet_elements we
        JOIN worksheets w ON w.id = we.worksheet_id
        WHERE w.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    # Get all fields from datasources used by worksheets
    fields = run_query(
        """
        SELECT f.id,
               f.datasource_id,
               f.caption as name,
               f.internal_name,
               f.formula,
               f.data_type,
               f.role,
               f.is_calculated
        FROM fields f
        JOIN datasources d ON d.id = f.datasource_id
        JOIN worksheets w ON w.datasource_id = d.id
        WHERE w.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    # Get field analysis results from field_data to include scores
    field_data = state.get("field_data", {}) or {}
    field_scores_map = {}
    
    for ds in field_data.get("datasources", []):
        for field in ds.get("fields", []):
            field_scores_map[field.get("id")] = {
                "complexity_drivers": field.get("complexity_drivers"),
                "score": field.get("score", 0)
            }
    
    # Enrich fields with scores from field_agent analysis
    enriched_fields = []
    for field in fields:
        field_id = field.get("id")
        field_info = field_scores_map.get(field_id, {"complexity_drivers": None, "score": 0})
        enriched_fields.append({
            **field,
            "complexity_drivers": field_info.get("complexity_drivers"),
            "score": field_info.get("score", 0)
        })

    payload = {
        "worksheets": worksheets,
        "worksheet_elements": elements,
        "fields": enriched_fields,
    }

    prompt = (
        VIZ_AGENT_PROMPT
        + "\n\nRAW_DATA_JSON:\n"
        + json.dumps(payload, indent=2)
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    data = extract_json(response.content)
    return {"viz_data": convert_uuids(data)}


def validate_viz_agent_node(state: MigrationState):
    """Validator agent that verifies viz_agent output against database."""
    print("🔍 Validating Visualization Agent Output...")
    wb_id = state["workbook_id"]
    viz_data = state.get("viz_data", {}) or {}
    
    if not wb_id or not viz_data:
        return {"viz_validation": {"valid": False, "errors": ["Missing workbook_id or viz_data"]}}
    
    validation_errors = []
    validation_warnings = []
    corrected_data = {"worksheets": []}
    
    # Get actual data from database
    db_worksheets = run_query(
        """
        SELECT id, workbook_id, name, datasource_id, columns_used, rows_used
        FROM worksheets
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    db_elements = run_query(
        """
        SELECT we.id,
               we.worksheet_id,
               we.pane_id,
               we.mark_class,
               we.element_type,
               we.encoding,
               we.style
        FROM worksheet_elements we
        JOIN worksheets w ON w.id = we.worksheet_id
        WHERE w.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    # Create lookup maps
    db_worksheet_map = {str(ws["id"]): ws for ws in db_worksheets}
    db_elements_by_worksheet = {}
    for elem in db_elements:
        ws_id = str(elem.get("worksheet_id"))
        if ws_id not in db_elements_by_worksheet:
            db_elements_by_worksheet[ws_id] = []
        db_elements_by_worksheet[ws_id].append(elem)
    
    # Validate worksheets
    agent_worksheets = viz_data.get("worksheets", [])
    for agent_ws in agent_worksheets:
        ws_id = str(agent_ws.get("id", ""))
        
        if ws_id not in db_worksheet_map:
            validation_errors.append(f"❌ HALLUCINATION: Worksheet ID {ws_id} does not exist in database")
            continue
        
        db_ws = db_worksheet_map[ws_id]
        
        # Verify name matches
        agent_name = agent_ws.get("name")
        db_name = db_ws.get("name")
        if agent_name != db_name:
            validation_warnings.append(
                f"⚠️  Worksheet {ws_id} name mismatch - Agent: '{agent_name}' vs DB: '{db_name}'"
            )
        
        # Verify datasource_id matches
        agent_ds_id = str(agent_ws.get("datasource_id", "")) if agent_ws.get("datasource_id") else None
        db_ds_id = str(db_ws.get("datasource_id", "")) if db_ws.get("datasource_id") else None
        if agent_ds_id != db_ds_id:
            validation_errors.append(
                f"❌ DATASOURCE MISMATCH: Worksheet {ws_id} - Agent: '{agent_ds_id}' vs DB: '{db_ds_id}'"
            )
            agent_ws["datasource_id"] = db_ds_id
        
        # Validate mark_classes against actual elements
        db_elements_for_ws = db_elements_by_worksheet.get(ws_id, [])
        db_mark_classes = [str(elem.get("mark_class", "")).lower() for elem in db_elements_for_ws if elem.get("mark_class")]
        agent_mark_classes = [str(mc).lower() for mc in agent_ws.get("mark_classes", [])]
        
        for agent_mc in agent_mark_classes:
            if agent_mc not in db_mark_classes:
                validation_warnings.append(
                    f"⚠️  Worksheet {ws_id}: mark_class '{agent_mc}' not found in database elements"
                )
        
        # Validate field references
        agent_fields = agent_ws.get("fields", [])
        for agent_field in agent_fields:
            field_id = str(agent_field.get("id", ""))
            field_data = state.get("field_data", {}) or {}
            field_exists = False
            for ds in field_data.get("datasources", []):
                for f in ds.get("fields", []):
                    if str(f.get("id")) == field_id:
                        field_exists = True
                        break
                if field_exists:
                    break
            
            if not field_exists:
                validation_warnings.append(
                    f"⚠️  Worksheet {ws_id}: Field {field_id} referenced but not found in field_data"
                )
        
        # Keep agent's analysis but use DB data for facts
        validated_ws = {
            "id": ws_id,
            "name": db_name,
            "datasource_id": db_ds_id,
            "viz_type": agent_ws.get("viz_type"),
            "mark_classes": list(set(db_mark_classes)) if db_mark_classes else agent_ws.get("mark_classes", []),
            "dual_axis": agent_ws.get("dual_axis", False),
            "viz_score": agent_ws.get("viz_score", 0),
            "field_score": agent_ws.get("field_score", 0),
            "complexity_score": agent_ws.get("complexity_score", 0),
            "fields": agent_ws.get("fields", [])
        }
        corrected_data["worksheets"].append(validated_ws)
    
    # Check for missing worksheets
    agent_ws_ids = {str(ws.get("id")) for ws in agent_worksheets}
    db_ws_ids = set(db_worksheet_map.keys())
    missing_ws = db_ws_ids - agent_ws_ids
    if missing_ws:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_ws)} worksheet(s): {missing_ws}")
    
    is_valid = len(validation_errors) == 0
    
    validation_result = {
        "valid": is_valid,
        "errors": validation_errors,
        "warnings": validation_warnings,
        "corrected_data": corrected_data if validation_errors else None
    }
    
    if validation_errors:
        print(f"❌ Validation FAILED: {len(validation_errors)} error(s), {len(validation_warnings)} warning(s)")
        for err in validation_errors[:5]:
            print(f"   {err}")
    else:
        print(f"✅ Validation PASSED: {len(validation_warnings)} warning(s)")
        if validation_warnings:
            for warn in validation_warnings[:3]:
                print(f"   {warn}")
    
    if validation_errors and corrected_data:
        return {
            "viz_validation": validation_result,
            "viz_data": corrected_data
        }
    
    return {"viz_validation": validation_result}


# ============================================================================
# 11. LAYOUT AGENT AND VALIDATOR
# ============================================================================

def layout_agent_node(state: MigrationState):
    """LLM agent that scores dashboard layout complexity."""
    print("🤖 Running Dashboard Layout Agent...")
    wb_id = state["workbook_id"]
    if not wb_id:
        return {"layout_data": {}}

    dashboards = run_query(
        """
        SELECT id, workbook_id, name, width, height, zones
        FROM dashboards
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    payload = {
        "dashboards": dashboards,
    }

    prompt = (
        LAYOUT_AGENT_PROMPT
        + "\n\nRAW_DATA_JSON:\n"
        + json.dumps(payload, indent=2)
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    data = extract_json(response.content)
    return {"layout_data": convert_uuids(data)}


def validate_layout_agent_node(state: MigrationState):
    """Validator agent that verifies layout_agent output against database."""
    print("🔍 Validating Layout Agent Output...")
    wb_id = state["workbook_id"]
    layout_data = state.get("layout_data", {}) or {}
    
    if not wb_id or not layout_data:
        return {"layout_validation": {"valid": False, "errors": ["Missing workbook_id or layout_data"]}}
    
    validation_errors = []
    validation_warnings = []
    corrected_data = {"dashboards": []}
    
    # Get actual data from database
    db_dashboards = run_query(
        """
        SELECT id, workbook_id, name, width, height, zones
        FROM dashboards
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    db_dashboard_map = {str(db["id"]): db for db in db_dashboards}
    
    # Validate dashboards
    agent_dashboards = layout_data.get("dashboards", [])
    for agent_db in agent_dashboards:
        db_id = str(agent_db.get("id", ""))
        
        if db_id not in db_dashboard_map:
            validation_errors.append(f"❌ HALLUCINATION: Dashboard ID {db_id} does not exist in database")
            continue
        
        db_dashboard = db_dashboard_map[db_id]
        
        # Verify name matches
        agent_name = agent_db.get("name")
        db_name = db_dashboard.get("name")
        if agent_name != db_name:
            validation_warnings.append(
                f"⚠️  Dashboard {db_id} name mismatch - Agent: '{agent_name}' vs DB: '{db_name}'"
            )
        
        # Verify dimensions match
        agent_width = agent_db.get("width")
        agent_height = agent_db.get("height")
        db_width = db_dashboard.get("width")
        db_height = db_dashboard.get("height")
        
        if agent_width != db_width or agent_height != db_height:
            validation_warnings.append(
                f"⚠️  Dashboard {db_id} dimensions mismatch - Agent: {agent_width}x{agent_height} vs DB: {db_width}x{db_height}"
            )
        
        # Keep agent's analysis but use DB data for facts
        validated_db = {
            "id": db_id,
            "name": db_name,
            "width": db_width,
            "height": db_height,
            "is_floating": agent_db.get("is_floating", False),
            "floating_count": agent_db.get("floating_count", 0),
            "component_count": agent_db.get("component_count", 0),
            "contained_sheet_ids": agent_db.get("contained_sheet_ids", []),
            "layout_score": agent_db.get("layout_score", 0)
        }
        corrected_data["dashboards"].append(validated_db)
    
    # Check for missing dashboards
    agent_db_ids = {str(db.get("id")) for db in agent_dashboards}
    db_db_ids = set(db_dashboard_map.keys())
    missing_dbs = db_db_ids - agent_db_ids
    if missing_dbs:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_dbs)} dashboard(s): {missing_dbs}")
    
    is_valid = len(validation_errors) == 0
    
    validation_result = {
        "valid": is_valid,
        "errors": validation_errors,
        "warnings": validation_warnings,
        "corrected_data": corrected_data if validation_errors else None
    }
    
    if validation_errors:
        print(f"❌ Validation FAILED: {len(validation_errors)} error(s), {len(validation_warnings)} warning(s)")
        for err in validation_errors[:5]:
            print(f"   {err}")
    else:
        print(f"✅ Validation PASSED: {len(validation_warnings)} warning(s)")
        if validation_warnings:
            for warn in validation_warnings[:3]:
                print(f"   {warn}")
    
    if validation_errors and corrected_data:
        return {
            "layout_validation": validation_result,
            "layout_data": corrected_data
        }
    
    return {"layout_validation": validation_result}


# ============================================================================
# 12. AGGREGATOR AND HTML AGENT
# ============================================================================

def aggregator_node(state: MigrationState):
    """Aggregate field/viz/layout scores into final workbook report."""
    print("🔗 Aggregating Results...")

    field_data = state.get("field_data", {}) or {}
    viz_data = state.get("viz_data", {}) or {}
    layout_data = state.get("layout_data", {}) or {}

    datasources = field_data.get("datasources", []) or []
    parameters = field_data.get("parameters", []) or []
    worksheets = viz_data.get("worksheets", []) or []
    dashboards = layout_data.get("dashboards", []) or []

    # Calculate scores
    total_worksheet_score = sum(ws.get("complexity_score", 0) for ws in worksheets)
    total_viz_score = sum(ws.get("viz_score", ws.get("complexity_score", 0)) for ws in worksheets)
    total_worksheet_field_score = sum(ws.get("field_score", 0) for ws in worksheets)
    total_datasource_field_score = sum(ds.get("complexity_score", 0) for ds in datasources)
    total_layout_score = sum(db.get("layout_score", 0) for db in dashboards)
    total_param_score = sum(p.get("score", 0) for p in parameters)

    # Total complexity score
    total_score = total_worksheet_score + total_layout_score + total_param_score

    migration_category = "Low"
    if total_score > 60:
        migration_category = "High"
    elif total_score > 20:
        migration_category = "Medium"

    # Include validation results in final report
    field_validation = state.get("field_validation", {})
    viz_validation = state.get("viz_validation", {})
    layout_validation = state.get("layout_validation", {})

    final_report = {
        "workbook": {
            "name": state["workbook_name"],
            "id": state["workbook_id"],
            "summary": {
                "total_complexity_score": total_score,
                "worksheet_score": total_worksheet_score,
                "worksheet_viz_score": total_viz_score,
                "worksheet_field_score": total_worksheet_field_score,
                "datasource_field_score": total_datasource_field_score,
                "layout_score": total_layout_score,
                "parameter_score": total_param_score,
                "migration_category": migration_category,
            },
            "datasources": datasources,
            "parameters": parameters,
            "worksheets": worksheets,
            "dashboards": dashboards,
            "validation": {
                "field_agent": {
                    "valid": field_validation.get("valid", True),
                    "error_count": len(field_validation.get("errors", [])),
                    "warning_count": len(field_validation.get("warnings", []))
                },
                "viz_agent": {
                    "valid": viz_validation.get("valid", True),
                    "error_count": len(viz_validation.get("errors", [])),
                    "warning_count": len(viz_validation.get("warnings", []))
                },
                "layout_agent": {
                    "valid": layout_validation.get("valid", True),
                    "error_count": len(layout_validation.get("errors", [])),
                    "warning_count": len(layout_validation.get("warnings", []))
                }
            }
        }
    }

    return {"final_report": convert_uuids(final_report)}


def html_agent_node(state: MigrationState):
    """LLM agent that generates HTML report from JSON."""
    print("🎨 Running HTML Generation Agent...")
    
    final_report = state.get("final_report", {})
    if not final_report:
        return {"html_report": "<html><body><h1>No data available</h1></body></html>"}
    
    # Prepare the prompt with the JSON report
    prompt = (
        HTML_AGENT_PROMPT
        + "\n\nJSON_REPORT_DATA:\n"
        + json.dumps(final_report, indent=2)
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    html_content = extract_html(response.content)
    
    print("✅ HTML report generated")
    return {"html_report": html_content}


# ============================================================================
# 13. BUILD GRAPH
# ============================================================================

workflow = StateGraph(MigrationState)

workflow.add_node("setup", setup_node)
workflow.add_node("field_agent", field_agent_node)
workflow.add_node("validate_field", validate_field_agent_node)
workflow.add_node("viz_agent", viz_agent_node)
workflow.add_node("validate_viz", validate_viz_agent_node)
workflow.add_node("layout_agent", layout_agent_node)
workflow.add_node("validate_layout", validate_layout_agent_node)
workflow.add_node("aggregator", aggregator_node)
workflow.add_node("html_agent", html_agent_node)

workflow.set_entry_point("setup")
workflow.add_edge("setup", "field_agent")
workflow.add_edge("field_agent", "validate_field")
workflow.add_edge("validate_field", "viz_agent")
workflow.add_edge("viz_agent", "validate_viz")
workflow.add_edge("validate_viz", "layout_agent")
workflow.add_edge("layout_agent", "validate_layout")
workflow.add_edge("validate_layout", "aggregator")
workflow.add_edge("aggregator", "html_agent")
workflow.add_edge("html_agent", END)

app = workflow.compile()


# ============================================================================
# 14. EXECUTION (JSON + HTML)
# ============================================================================

def analyze_workbook_hierarchical(workbook_name: str):
    print(f"🚀 Starting Multi-Agent Analysis with Tool Calling for: {workbook_name}")

    initial_state: MigrationState = {
        "workbook_name": workbook_name,
        "workbook_id": "",
        "field_data": {},
        "viz_data": {},
        "layout_data": {},
        "field_validation": {},
        "viz_validation": {},
        "layout_validation": {},
        "final_report": {},
        "html_report": "",
    }

    result = app.invoke(initial_state)
    report = result.get("final_report", {})
    html_report = result.get("html_report", "")
    
    report = convert_uuids(report)

    print("\n" + "=" * 60)
    print("📊 FINAL HIERARCHICAL REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))

    # Save JSON with validated report naming
    safe_name = workbook_name.replace(" ", "_").replace("/", "_")
    json_filename = f"{safe_name}_validated_complexity_reports.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Save HTML with validated report naming
    html_filename = f"{safe_name}_validated_complexity_reports.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_report)

    print(f"\n💾 Saved VALIDATED JSON report to {json_filename}")
    print(f"💾 Saved VALIDATED HTML report to {html_filename}")
    print(f"   📋 Both reports include validation results against the database")
    
    # Print validation summary
    validation = report.get("workbook", {}).get("validation", {})
    print("\n" + "=" * 60)
    print("🔍 VALIDATION SUMMARY")
    print("=" * 60)
    for agent_name, val_result in validation.items():
        status = "✅ PASSED" if val_result.get("valid") else "❌ FAILED"
        print(f"{agent_name}: {status} ({val_result.get('error_count', 0)} errors, {val_result.get('warning_count', 0)} warnings)")


def list_available_workbooks():
    """Helper function to list all workbooks in the database."""
    try:
        query = "SELECT id, name FROM workbooks ORDER BY name LIMIT 20"
        result = run_query(query)
        print("\n" + "=" * 60)
        print("📚 AVAILABLE WORKBOOKS IN DATABASE")
        print("=" * 60)
        for row in result:
            print(f"  - {row.get('name')} (ID: {row.get('id')})")
        print("=" * 60 + "\n")
        return result
    except Exception as e:
        print(f"❌ Error listing workbooks: {e}")
        return None


if __name__ == "__main__":
    import sys
    
    # If --list flag, show available workbooks
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_available_workbooks()
        sys.exit(0)
    
    # Get workbook name from command line or use default
    workbook_name = sys.argv[1] if len(sys.argv) > 1 else "SalesSummary_BIGTEST_20x"
    
    print(f"\n💡 Tip: Use --list flag to see available workbooks")
    print(f"💡 Using workbook name: '{workbook_name}'\n")
    
    analyze_workbook_hierarchical(workbook_name)
