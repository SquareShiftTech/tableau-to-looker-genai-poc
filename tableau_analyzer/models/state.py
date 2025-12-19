"""
State definitions for the conversational multi-agent workflow
"""
from typing import TypedDict, Dict, Any, List, Optional


class AnalysisState(TypedDict):
    """
    State that flows through all agents in the conversational workflow.
    Agent 1 deeply understands the Tableau file, and other agents query it.
    """
    
    # Input
    bi_tool_type: str           # "tableau", "cognos", etc.
    file_path: str              # Path to the file
    
    # Agent 1 outputs
    file_json: Dict[str, Any]   # Full JSON representation of XML
    inventory: Dict[str, Any]   # Initial exploration results
    agent_1_ready: bool         # Flag indicating Agent 1 finished understanding
    json_spec: Optional[Any]    # JsonSpec object for queries (stored for reuse)
    
    # Master-Worker Architecture (optional, for new architecture)
    component_index: Optional[Dict[str, Any]]  # Component discovery index (counts, names, locations)
    sub_agent_results: Optional[Dict[str, Dict[str, Any]]]  # Results from each sub-agent
    master_ready: Optional[bool]  # Master agent completion flag
    sub_agents_ready: Optional[Dict[str, bool]]  # Individual sub-agent ready flags
    sub_agent_specs: Optional[Dict[str, Any]]  # JsonSpecs for each sub-agent (for query routing)
    
    # Agent 2 outputs
    complexity_analysis: Dict[str, Any]     # Complexity patterns, risks, migration difficulty
    agent_2_questions: List[str]            # Questions Agent 2 asked Agent 1
    
    # Agent 3 outputs (future)
    extracted_features: Dict[str, List[Dict]]   # Specific features for migration
    
    # Conversation tracking
    agent_conversations: List[Dict[str, str]]   # All Q&A between agents
    # Format: [{"from": "agent_2", "to": "agent_1", "question": "...", "answer": "..."}]
    
    # Metadata
    errors: List[str]           # Track any errors
