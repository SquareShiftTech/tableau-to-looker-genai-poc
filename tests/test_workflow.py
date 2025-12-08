"""Integration tests for workflow."""
import pytest
from models.state import AssessmentState
from workflows.assessment_workflow import create_assessment_workflow


@pytest.fixture
def initial_state() -> AssessmentState:
    """Create initial state for testing."""
    return AssessmentState(
        job_id="test_workflow_001",
        source_files=[
            {"platform": "tableau", "file_path": "gs://bucket/test.twb"},
        ],
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


@pytest.mark.asyncio
async def test_full_workflow(initial_state: AssessmentState):
    """Test complete workflow execution."""
    workflow = create_assessment_workflow()
    
    result = await workflow.ainvoke(initial_state)
    
    # Verify final state
    assert result['status'] == 'strategy_complete'
    assert result['discovered_components'] is not None
    assert result['parsed_metrics'] is not None
    assert result['calculation_analysis'] is not None
    assert result['visualization_analysis'] is not None
    assert result['dashboard_analysis'] is not None
    assert result['datasource_analysis'] is not None
    assert result['final_report'] is not None
    assert 'executive_summary' in result['final_report']
    assert 'migration_recommendations' in result['final_report']


@pytest.mark.asyncio
async def test_workflow_with_empty_source_files():
    """Test workflow with empty source files."""
    workflow = create_assessment_workflow()
    
    initial_state = AssessmentState(
        job_id="test_empty_001",
        source_files=[],
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
    
    result = await workflow.ainvoke(initial_state)
    
    # Workflow should complete even with empty files
    assert result['status'] == 'strategy_complete'

