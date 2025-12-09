"""State definitions for LangGraph workflow."""
from typing import TypedDict, List, Dict, Any, Optional


class AssessmentState(TypedDict):
    """State object passed between agents in the workflow."""
    
    # Job metadata
    job_id: str
    source_files: List[Dict[str, str]]  # [{"platform": "tableau", "file_path": "gs://..."}]
    
    # Step 0: File Analysis Agent Output
    file_analysis_strategy: Optional[Dict[str, Any]]  # Splitting strategy for large files (legacy, kept for backward compatibility)
    strategy_refinement_needed: Optional[Dict[str, Any]]  # Feedback about what failed (for iterative re-strategizing) (legacy)
    strategy_refinement_count: int  # How many times we've refined (prevent infinite loops) (legacy)
    
    # Step 0: File Analysis Agent Output (New architecture)
    parsed_elements_paths: Optional[List[Dict[str, Any]]]  # List of {element_name, file_path, size_bytes}
    output_dir: Optional[str]  # Output directory path (e.g., output/{job_id})
    
    # Step 1: Exploration Agent Output
    discovered_components: Optional[Dict[str, Any]]  # Components found: dashboards, metrics, visualizations, datasources
    
    # Step 2: Parsing Agent Output
    parsed_metrics: Optional[List[Dict[str, Any]]]
    parsed_dashboards: Optional[List[Dict[str, Any]]]
    parsed_visualizations: Optional[List[Dict[str, Any]]]
    parsed_datasources: Optional[List[Dict[str, Any]]]
    
    # Step 3: Specialized Agent Outputs
    calculation_analysis: Optional[List[Dict[str, Any]]]
    visualization_analysis: Optional[List[Dict[str, Any]]]
    dashboard_analysis: Optional[List[Dict[str, Any]]]
    datasource_analysis: Optional[List[Dict[str, Any]]]
    
    # Step 4: Strategy Agent Output
    final_report: Optional[Dict[str, Any]]  # Executive summary, recommendations, etc.
    
    # Workflow status
    status: str  # "exploration_complete", "parsing_complete", "analysis_complete", "strategy_complete"
    errors: List[str]  # Any errors encountered during processing

