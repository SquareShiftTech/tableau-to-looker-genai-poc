"""Simple test script for File Analysis Agent."""
import asyncio
import json
from agents.file_analysis_agent import file_analysis_agent
from models.state import AssessmentState
from utils.logger import logger


async def test_file_analysis():
    """Test the file analysis agent with a Tableau XML file."""
    
    # Test with first file
    state = AssessmentState(
        job_id="test_file_analysis_001",
        source_files=[
            {"platform": "tableau", "file_path": "input_files/tableau/sales_summary_final.xml"},
        ],
        file_analysis_strategy=None,
        strategy_refinement_needed=None,
        strategy_refinement_count=0,
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
    print("TESTING FILE ANALYSIS AGENT")
    print("="*80)
    print(f"File: {state['source_files'][0]['file_path']}")
    print(f"Platform: {state['source_files'][0]['platform']}")
    print("="*80 + "\n")
    
    try:
        result = await file_analysis_agent(state)
        
        print("\n" + "="*80)
        print("FILE ANALYSIS RESULTS")
        print("="*80)
        
        strategy = result.get('file_analysis_strategy')
        
        if strategy:
            print(f"\nStrategy Method: {strategy.get('split_method', 'N/A')}")
            print(f"Number of Chunks: {len(strategy.get('chunks', []))}")
            
            print(f"\nProcessing Order: {strategy.get('processing_order', [])}")
            
            print(f"\nChunks Details:")
            for i, chunk in enumerate(strategy.get('chunks', []), 1):
                print(f"\n  Chunk {i} ({chunk.get('chunk_id', 'N/A')}):")
                print(f"    - Target Elements: {chunk.get('target_elements', [])}")
                print(f"    - Priority: {chunk.get('priority', 'N/A')}")
                print(f"    - Max Size: {chunk.get('max_size_bytes', 0):,} bytes")
                print(f"    - Context Needed: {chunk.get('context_needed', [])}")
                if chunk.get('split_by'):
                    print(f"    - Split By: {chunk.get('split_by')}")
            
            context_preservation = strategy.get('context_preservation', {})
            if context_preservation:
                print(f"\nContext Preservation:")
                print(f"  - Global Context: {context_preservation.get('global_context', [])}")
                dependencies = context_preservation.get('chunk_dependencies', {})
                if dependencies:
                    print(f"  - Chunk Dependencies:")
                    for chunk_id, deps in dependencies.items():
                        print(f"    - {chunk_id} depends on: {deps}")
        else:
            print("\nNo strategy created (strategy is None)")
        
        print("\n" + "="*80)
        print("FULL STRATEGY JSON OUTPUT:")
        print("="*80)
        print(json.dumps(strategy, indent=2) if strategy else "null")
        print("="*80)
        
        print(f"\nStatus: {result.get('status', 'N/A')}")
        
        if result.get('errors'):
            print(f"\nErrors: {result['errors']}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test_file_analysis())

