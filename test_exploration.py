"""Simple test script for Exploration Agent."""
import asyncio
import json
from agents.exploration_agent import exploration_agent
from models.state import AssessmentState
from utils.logger import logger


async def test_exploration():
    """Test the exploration agent with a Tableau XML file."""
    
    # Test with first file
    state = AssessmentState(
        job_id="test_exploration_001",
        source_files=[
            {"platform": "tableau", "file_path": "input_files/tableau/sales_summary_final.xml"},
        ],
        file_analysis_strategy=None,
        discovered_components=None,
        parsed_metrics=None,
        parsed_dashboards=None,
        parsed_visualizations=None,
        parsed_datasources=None,
        calculation_analysis=None,
        visualization_analysis=None,
        dashboard_analysis=None,
        datasource_analysis=None,
        final_report=None,
        status="initial",
        errors=[],
    )
    
    print("\n" + "="*80)
    print("TESTING EXPLORATION AGENT")
    print("="*80)
    print(f"File: {state['source_files'][0]['file_path']}")
    print(f"Platform: {state['source_files'][0]['platform']}")
    print("="*80 + "\n")
    
    try:
        result = await exploration_agent(state)
        
        print("\n" + "="*80)
        print("EXPLORATION RESULTS")
        print("="*80)
        
        discovered = result.get('discovered_components', {})
        
        print(f"\nDashboards: {len(discovered.get('dashboards', []))}")
        for dash in discovered.get('dashboards', []):
            print(f"  - {dash.get('name', 'N/A')} (id: {dash.get('id', 'N/A')})")
        
        print(f"\nMetrics: {len(discovered.get('metrics', []))}")
        for metric in discovered.get('metrics', []):
            print(f"  - {metric.get('name', 'N/A')} (id: {metric.get('id', 'N/A')})")
        
        print(f"\nVisualizations: {len(discovered.get('visualizations', []))}")
        for viz in discovered.get('visualizations', []):
            print(f"  - {viz.get('name', 'N/A')} ({viz.get('type', 'N/A')}) (id: {viz.get('id', 'N/A')})")
        
        print(f"\nData Sources: {len(discovered.get('datasources', []))}")
        for ds in discovered.get('datasources', []):
            print(f"  - {ds.get('name', 'N/A')} ({ds.get('type', 'N/A')}) (id: {ds.get('id', 'N/A')})")
        
        print("\n" + "="*80)
        print("FULL JSON OUTPUT:")
        print("="*80)
        print(json.dumps(discovered, indent=2))
        print("="*80)
        
        if result.get('errors'):
            print(f"\nErrors: {result['errors']}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test_exploration())

