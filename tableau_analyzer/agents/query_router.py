"""
Query Router: Intelligent routing of queries to appropriate sub-agents or direct answers

Routes queries based on content analysis:
- Simple queries (counts, lists) → Answered from component index
- Component-specific queries → Routed to appropriate sub-agent
- Cross-component queries → Master coordinates multiple sub-agents
"""
from typing import Tuple, Optional, Dict, Any


def route_query(question: str, state: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """
    Route a query to appropriate handler
    
    Args:
        question: User question
        state: Analysis state with component_index and sub_agent_results
        
    Returns:
        Tuple of (target_agent_type, direct_answer_if_simple)
        target_agent_type: "worksheet", "dashboard", "datasource", "calculation", "master", or "index"
        direct_answer_if_simple: Answer string if question can be answered from index, None otherwise
    """
    question_lower = question.lower()
    component_index = state.get("component_index", {})
    
    # Check if it's a simple query that can be answered from index
    direct_answer = answer_from_index(question, component_index)
    if direct_answer:
        return ("index", direct_answer)
    
    # Analyze question keywords to determine target component
    # Worksheet keywords
    worksheet_keywords = ["worksheet", "sheet", "viz", "visualization", "chart", "graph"]
    if any(keyword in question_lower for keyword in worksheet_keywords):
        # Check if it's worksheet-specific
        if _is_component_specific(question_lower, "worksheet"):
            return ("worksheet", None)
    
    # Dashboard keywords
    dashboard_keywords = ["dashboard", "dashboard", "layout", "zone"]
    if any(keyword in question_lower for keyword in dashboard_keywords):
        if _is_component_specific(question_lower, "dashboard"):
            return ("dashboard", None)
    
    # Datasource keywords
    datasource_keywords = ["datasource", "data source", "connection", "table", "join", "sql"]
    if any(keyword in question_lower for keyword in datasource_keywords):
        if _is_component_specific(question_lower, "datasource"):
            return ("datasource", None)
    
    # Calculation keywords
    calculation_keywords = ["calculation", "calculated field", "formula", "calc", "computed"]
    if any(keyword in question_lower for keyword in calculation_keywords):
        if _is_component_specific(question_lower, "calculation"):
            return ("calculation", None)
    
    # Cross-component queries (need master coordination)
    cross_component_keywords = ["which", "relationship", "used in", "feeds", "connected"]
    if any(keyword in question_lower for keyword in cross_component_keywords):
        return ("master", None)
    
    # Default: route to master for complex queries
    return ("master", None)


def answer_from_index(question: str, component_index: Dict[str, Any]) -> Optional[str]:
    """
    Answer simple questions using component index (no agent call needed)
    
    Args:
        question: User question
        component_index: Component index from master agent
        
    Returns:
        Answer string if question can be answered from index, None otherwise
    """
    question_lower = question.lower()
    
    # Count questions
    if "how many" in question_lower:
        if "worksheet" in question_lower:
            count = component_index.get("worksheets", {}).get("count", 0)
            return f"There are {count} worksheet(s) in this Tableau file."
        
        if "dashboard" in question_lower:
            count = component_index.get("dashboards", {}).get("count", 0)
            return f"There are {count} dashboard(s) in this Tableau file."
        
        if "datasource" in question_lower or "data source" in question_lower:
            count = component_index.get("datasources", {}).get("count", 0)
            return f"There are {count} datasource(s) in this Tableau file."
        
        if "calculation" in question_lower or "calculated field" in question_lower:
            count = component_index.get("calculations", {}).get("count", 0)
            return f"There are {count} calculation(s) in this Tableau file."
    
    # List questions
    if "list" in question_lower or "what are" in question_lower or "names" in question_lower:
        if "worksheet" in question_lower:
            names = component_index.get("worksheets", {}).get("names", [])
            if names:
                return f"Worksheets: {', '.join(names)}"
            return "No worksheets found."
        
        if "dashboard" in question_lower:
            names = component_index.get("dashboards", {}).get("names", [])
            if names:
                return f"Dashboards: {', '.join(names)}"
            return "No dashboards found."
        
        if "datasource" in question_lower or "data source" in question_lower:
            names = component_index.get("datasources", {}).get("names", [])
            if names:
                return f"Datasources: {', '.join(names)}"
            return "No datasources found."
        
        if "calculation" in question_lower or "calculated field" in question_lower:
            names = component_index.get("calculations", {}).get("names", [])
            if names:
                return f"Calculations: {', '.join(names)}"
            return "No calculations found."
    
    # Existence questions
    if "are there" in question_lower or "does" in question_lower or "is there" in question_lower:
        if "worksheet" in question_lower:
            count = component_index.get("worksheets", {}).get("count", 0)
            return f"Yes, there are {count} worksheet(s)." if count > 0 else "No worksheets found."
        
        if "dashboard" in question_lower:
            count = component_index.get("dashboards", {}).get("count", 0)
            return f"Yes, there are {count} dashboard(s)." if count > 0 else "No dashboards found."
        
        if "datasource" in question_lower or "data source" in question_lower:
            count = component_index.get("datasources", {}).get("count", 0)
            return f"Yes, there are {count} datasource(s)." if count > 0 else "No datasources found."
        
        if "calculation" in question_lower or "calculated field" in question_lower:
            count = component_index.get("calculations", {}).get("count", 0)
            return f"Yes, there are {count} calculation(s)." if count > 0 else "No calculations found."
    
    return None


def _is_component_specific(question_lower: str, component_type: str) -> bool:
    """
    Check if question is specific to a component type
    
    Args:
        question_lower: Question in lowercase
        component_type: Component type to check
        
    Returns:
        True if question is specific to this component type
    """
    # If question mentions specific component name, it's specific
    # For now, assume all questions mentioning the component type are specific
    # This can be enhanced with more sophisticated NLP
    
    component_keywords = {
        "worksheet": ["worksheet", "sheet"],
        "dashboard": ["dashboard"],
        "datasource": ["datasource", "data source"],
        "calculation": ["calculation", "calculated field", "formula"]
    }
    
    keywords = component_keywords.get(component_type, [])
    return any(keyword in question_lower for keyword in keywords)


def get_sub_agent_for_query(target_agent_type: str, state: Dict[str, Any]) -> Optional[Any]:
    """
    Get the appropriate sub-agent instance for a query
    
    Args:
        target_agent_type: Type of agent needed ("worksheet", "dashboard", etc.)
        state: Analysis state
        
    Returns:
        Sub-agent instance or None
    """
    # Sub-agents are stored in state after creation
    sub_agents = state.get("sub_agents", {})
    return sub_agents.get(target_agent_type)
