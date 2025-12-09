"""LangGraph workflow for BI Assessment."""
from typing import Any
from langgraph.graph import StateGraph, END
from models.state import AssessmentState
from agents.file_analysis_agent import file_analysis_agent
from agents.exploration_agent import exploration_agent
from agents.parsing_agent import parsing_agent
from agents.calculation_agent import calculation_agent
from agents.visualization_agent import visualization_agent
from agents.dashboard_agent import dashboard_agent
from agents.datasource_agent import datasource_agent
from agents.strategy_agent import strategy_agent
from utils.logger import logger


def create_assessment_workflow() -> Any:
    """
    Create and return the LangGraph workflow for BI Assessment.
    
    Workflow structure:
    0. file_analysis_agent -> Analyze file structure and create splitting strategy
    1. exploration_agent -> Discover components
    2. parsing_agent -> Extract complexity details
    3. Parallel execution:
       - calculation_agent
       - visualization_agent
       - dashboard_agent
       - datasource_agent
    4. strategy_agent -> Generate recommendations
    
    Returns:
        Compiled LangGraph workflow
    """
    
    logger.info("Creating assessment workflow")
    
    # Create StateGraph
    workflow = StateGraph(AssessmentState)
    
    # Add nodes (agents)
    workflow.add_node("file_analysis", file_analysis_agent)
    workflow.add_node("exploration", exploration_agent)
    workflow.add_node("parsing", parsing_agent)
    workflow.add_node("calculation", calculation_agent)
    workflow.add_node("visualization", visualization_agent)
    workflow.add_node("dashboard", dashboard_agent)
    workflow.add_node("datasource", datasource_agent)
    workflow.add_node("strategy", strategy_agent)
    
    # Define edges (workflow)
    workflow.set_entry_point("file_analysis")
    workflow.add_edge("file_analysis", "exploration")
    workflow.add_edge("exploration", "parsing")  # Simple linear flow
    workflow.add_edge("parsing", "calculation")
    workflow.add_edge("parsing", "visualization")
    workflow.add_edge("parsing", "dashboard")
    workflow.add_edge("parsing", "datasource")
    
    # All specialized agents complete before strategy
    workflow.add_edge("calculation", "strategy")
    workflow.add_edge("visualization", "strategy")
    workflow.add_edge("dashboard", "strategy")
    workflow.add_edge("datasource", "strategy")
    
    workflow.add_edge("strategy", END)
    
    # Compile workflow
    app = workflow.compile()
    
    logger.info("Assessment workflow created successfully")
    return app


# For backward compatibility
def create_assessment_workflow_graph() -> Any:
    """Alias for create_assessment_workflow."""
    return create_assessment_workflow()

