"""LLM prompt templates for complexity analysis."""
import json
from typing import Dict, Any, List


def build_visualization_prompt(
    mark_class: str,
    encoding: Dict[str, Any],
    worksheet_name: str,
    rules: Dict[str, Any]
) -> str:
    """Build prompt for LLM to assess visualization complexity."""
    
    return f"""Analyze this Tableau visualization for Looker migration complexity.

Visualization Details:
- Mark Class: {mark_class}
- Worksheet: {worksheet_name}
- Encoding: {json.dumps(encoding, indent=2) if encoding else "None"}

Complexity Rules (use these only - do not invent new rules):
{json.dumps(rules, indent=2)}

Task:
1. Determine complexity level: "low", "medium", or "high"
2. Match mark_class against the rules provided above
3. If dual-axis detected (multiple axes in encoding), increase to "medium" or "high"
4. If custom/complex encoding patterns, consider "high"

Return ONLY valid JSON (no markdown, no explanations):
{{
  "complexity": "low|medium|high",
  "reasoning": "Brief explanation matching the rules",
  "matched_rule": "Which rule category matched"
}}
"""


def build_calculated_field_prompt(
    field_name: str,
    formula: str,
    rules: Dict[str, Any]
) -> str:
    """Build prompt for LLM to assess calculated field complexity."""
    
    return f"""Analyze this Tableau calculated field for Looker migration complexity.

Calculated Field Details:
- Field Name: {field_name}
- Formula: {formula}

Complexity Rules (use these only - do not invent new rules):
{json.dumps(rules, indent=2)}

Task:
1. Check formula against regex patterns in rules
2. Look for patterns: basic_arithmetic, date_functions, string_operations, lod_expressions, window_functions
3. Determine complexity: "low", "medium", or "high"
4. Match against rule patterns provided above

Return ONLY valid JSON (no markdown, no explanations):
{{
  "complexity": "low|medium|high",
  "reasoning": "Which pattern matched (e.g., 'Contains LOD expression')",
  "matched_patterns": ["pattern1", "pattern2"]
}}
"""


def build_dashboard_prompt(
    dashboard_name: str,
    component_count: int,
    action_types: List[str],
    rules: Dict[str, Any]
) -> str:
    """Build prompt for LLM to assess dashboard complexity."""
    
    return f"""Analyze this Tableau dashboard for Looker migration complexity.

Dashboard Details:
- Dashboard Name: {dashboard_name}
- Component Count: {component_count}
- Action Types: {', '.join(action_types) if action_types else 'None'}

Complexity Rules (use these only - do not invent new rules):
{json.dumps(rules, indent=2)}

Task:
1. Check component_count against rules (low: ≤1, medium: 2-5, high: ≥6)
2. Check action_types against rules
3. Determine complexity: "low", "medium", or "high"
4. Match against rule thresholds provided above

Return ONLY valid JSON (no markdown, no explanations):
{{
  "complexity": "low|medium|high",
  "reasoning": "Which rule matched (e.g., '6 components = high complexity')",
  "matched_indicators": ["multi_tile", "cross_filtering"]
}}
"""


def build_generic_complexity_prompt(
    feature_type: str,
    feature_data: Dict[str, Any],
    rules: Dict[str, Any]
) -> str:
    """Build generic prompt for ambiguous cases."""
    
    return f"""Analyze this Tableau {feature_type} for Looker migration complexity.

Feature Data:
{json.dumps(feature_data, indent=2)}

Complexity Rules (use these only - do not invent new rules):
{json.dumps(rules, indent=2)}

Task:
1. Analyze the feature data against the rules
2. Determine complexity: "low", "medium", or "high"
3. Reference the rules provided - do not invent new complexity levels
4. If no clear match, choose the closest rule match

Return ONLY valid JSON (no markdown, no explanations):
{{
  "complexity": "low|medium|high",
  "reasoning": "Explanation based on rules",
  "confidence": "high|medium|low"
}}
"""
