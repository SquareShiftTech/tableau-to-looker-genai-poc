"""
Agent 2: Complexity Analyzer

This agent asks Agent 1 intelligent questions to assess migration complexity.
It demonstrates the conversational multi-agent architecture.
"""
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1 import query_tableau_expert


def agent_2_complexity_analyzer(state: AnalysisState) -> AnalysisState:
    """
    Agent 2: Complexity Analyzer
    
    Analyzes complexity for migration assessment by asking Agent 1 questions.
    
    Args:
        state: Current workflow state (Agent 1 must be ready)
        
    Returns:
        Updated state with complexity_analysis and agent_2_questions
    """
    print("\n" + "="*70)
    print("🔍 AGENT 2: COMPLEXITY ANALYZER")
    print("="*70)
    
    # Check if Agent 1 is ready
    if not state.get("agent_1_ready", False):
        error_msg = "Agent 1 not ready - cannot perform complexity analysis"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        return state
    
    print("✅ Agent 1 is ready - beginning complexity analysis")
    print("\n" + "-"*70)
    print("STEP 1: ASKING AGENT 1 TARGETED QUESTIONS")
    print("-"*70)
    
    # Define questions to ask Agent 1
    questions = [
        "What calculated fields use Level of Detail (LOD) expressions like FIXED, INCLUDE, or EXCLUDE?",
        "Which worksheets have the most complex filter combinations or parameters?",
        "Are there any nested calculations (calculations that reference other calculations)?",
        "What data blending, joins, or relationship patterns are used in the datasources?",
        "Which dashboards have the most interactive elements like parameters, actions, or filters?"
    ]
    
    analysis = {
        "questions_asked": [],
        "answers": {},
        "complexity_factors": [],
        "complexity_score": "UNKNOWN",
        "migration_risks": []
    }
    
    # Ask each question to Agent 1
    for i, question in enumerate(questions, 1):
        print(f"\nQuestion {i}/{len(questions)}")
        answer = query_tableau_expert(state, question, asking_agent="agent_2")
        
        analysis["questions_asked"].append(question)
        analysis["answers"][question] = answer
        
        # Analyze the answer for complexity indicators
        analyze_complexity_from_answer(question, answer, analysis)
    
    # Calculate overall complexity score
    print("\n" + "-"*70)
    print("STEP 2: CALCULATING COMPLEXITY SCORE")
    print("-"*70)
    
    analysis["complexity_score"] = calculate_complexity_score(analysis)
    
    # Store in state
    state["complexity_analysis"] = analysis
    state["agent_2_questions"] = questions
    
    # Print summary
    print_complexity_summary(analysis)
    
    print("\n" + "="*70)
    print("✅ AGENT 2: COMPLEXITY ANALYSIS COMPLETE")
    print("="*70)
    
    return state


def analyze_complexity_from_answer(question: str, answer: str, analysis: Dict[str, Any]) -> None:
    """
    Analyze an answer for complexity indicators
    
    Args:
        question: The question that was asked
        answer: Agent 1's answer
        analysis: Analysis dict to update
    """
    answer_lower = answer.lower()
    
    # LOD expressions detection
    if "lod" in question.lower():
        if any(keyword in answer_lower for keyword in ["fixed", "include", "exclude", "found", "yes"]):
            if "no" not in answer_lower or "not found" not in answer_lower:
                analysis["complexity_factors"].append("LOD expressions detected")
                analysis["migration_risks"].append("LOD expressions require careful translation to Looker")
    
    # Nested calculations detection
    if "nested" in question.lower():
        if any(keyword in answer_lower for keyword in ["yes", "found", "reference", "nested"]):
            if "no" not in answer_lower:
                analysis["complexity_factors"].append("Nested calculations found")
                analysis["migration_risks"].append("Nested calculations increase migration complexity")
    
    # Filter complexity detection
    if "filter" in question.lower():
        if any(keyword in answer_lower for keyword in ["complex", "multiple", "many", "several"]):
            analysis["complexity_factors"].append("Complex filtering detected")
            analysis["migration_risks"].append("Complex filters may need redesign in Looker")
    
    # Data blending detection
    if "blend" in question.lower() or "join" in question.lower():
        if any(keyword in answer_lower for keyword in ["blend", "join", "relationship", "multiple"]):
            analysis["complexity_factors"].append("Data blending/joins detected")
            analysis["migration_risks"].append("Data relationships need careful mapping to Looker")
    
    # Interactive elements detection
    if "interactive" in question.lower() or "dashboard" in question.lower():
        if any(keyword in answer_lower for keyword in ["parameter", "action", "filter", "multiple"]):
            analysis["complexity_factors"].append("Interactive dashboard elements")
            analysis["migration_risks"].append("Dashboard interactivity needs recreation in Looker")


def calculate_complexity_score(analysis: Dict[str, Any]) -> str:
    """
    Calculate overall complexity score based on factors found
    
    Args:
        analysis: Analysis dict with complexity factors
        
    Returns:
        Complexity score: LOW, MEDIUM, HIGH, or CRITICAL
    """
    num_factors = len(analysis["complexity_factors"])
    
    if num_factors == 0:
        return "LOW"
    elif num_factors <= 2:
        return "MEDIUM"
    elif num_factors <= 4:
        return "HIGH"
    else:
        return "CRITICAL"


def print_complexity_summary(analysis: Dict[str, Any]) -> None:
    """
    Print a summary of the complexity analysis
    """
    print("\n📊 COMPLEXITY ANALYSIS SUMMARY:")
    print(f"   🎯 Complexity Score: {analysis['complexity_score']}")
    print(f"   📋 Questions Asked: {len(analysis['questions_asked'])}")
    print(f"   ⚠️  Complexity Factors: {len(analysis['complexity_factors'])}")
    
    if analysis['complexity_factors']:
        print("\n   Factors Found:")
        for factor in analysis['complexity_factors']:
            print(f"      • {factor}")
    
    if analysis['migration_risks']:
        print("\n   🚨 Migration Risks:")
        for risk in analysis['migration_risks']:
            print(f"      • {risk}")
