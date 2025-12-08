"""Unit tests for agents."""
import pytest
from models.state import AssessmentState
from agents.exploration_agent import exploration_agent
from agents.parsing_agent import parsing_agent
from agents.calculation_agent import calculation_agent
from agents.visualization_agent import visualization_agent
from agents.dashboard_agent import dashboard_agent
from agents.datasource_agent import datasource_agent
from agents.strategy_agent import strategy_agent


@pytest.fixture
def initial_state() -> AssessmentState:
    """Create initial state for testing."""
    return AssessmentState(
        job_id="test_001",
        source_files=[
            {"platform": "tableau", "file_path": "gs://bucket/test.twb"},
            {"platform": "power_bi", "file_path": "gs://bucket/test.pbix"},
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
async def test_exploration_agent(initial_state: AssessmentState):
    """Test exploration agent."""
    result = await exploration_agent(initial_state)
    assert result['status'] == 'exploration_complete'
    assert result['discovered_components'] is not None
    assert 'dashboards' in result['discovered_components']
    assert 'metrics' in result['discovered_components']


@pytest.mark.asyncio
async def test_parsing_agent(initial_state: AssessmentState):
    """Test parsing agent."""
    # First run exploration to populate discovered_components
    state_after_exploration = await exploration_agent(initial_state)
    
    result = await parsing_agent(state_after_exploration)
    assert result['status'] == 'parsing_complete'
    assert result['parsed_metrics'] is not None
    assert result['parsed_dashboards'] is not None


@pytest.mark.asyncio
async def test_calculation_agent(initial_state: AssessmentState):
    """Test calculation agent."""
    # Run exploration and parsing first
    state_after_exploration = await exploration_agent(initial_state)
    state_after_parsing = await parsing_agent(state_after_exploration)
    
    result = await calculation_agent(state_after_parsing)
    assert result['status'] == 'analysis_complete'
    assert result['calculation_analysis'] is not None
    assert len(result['calculation_analysis']) > 0


@pytest.mark.asyncio
async def test_visualization_agent(initial_state: AssessmentState):
    """Test visualization agent."""
    # Run exploration and parsing first
    state_after_exploration = await exploration_agent(initial_state)
    state_after_parsing = await parsing_agent(state_after_exploration)
    
    result = await visualization_agent(state_after_parsing)
    assert result['status'] == 'analysis_complete'
    assert result['visualization_analysis'] is not None


@pytest.mark.asyncio
async def test_dashboard_agent(initial_state: AssessmentState):
    """Test dashboard agent."""
    # Run exploration and parsing first
    state_after_exploration = await exploration_agent(initial_state)
    state_after_parsing = await parsing_agent(state_after_exploration)
    
    result = await dashboard_agent(state_after_parsing)
    assert result['status'] == 'analysis_complete'
    assert result['dashboard_analysis'] is not None


@pytest.mark.asyncio
async def test_datasource_agent(initial_state: AssessmentState):
    """Test datasource agent."""
    # Run exploration and parsing first
    state_after_exploration = await exploration_agent(initial_state)
    state_after_parsing = await parsing_agent(state_after_exploration)
    
    result = await datasource_agent(state_after_parsing)
    assert result['status'] == 'analysis_complete'
    assert result['datasource_analysis'] is not None


@pytest.mark.asyncio
async def test_strategy_agent(initial_state: AssessmentState):
    """Test strategy agent."""
    # Run full pipeline first
    state_after_exploration = await exploration_agent(initial_state)
    state_after_parsing = await parsing_agent(state_after_exploration)
    state_after_calc = await calculation_agent(state_after_parsing)
    state_after_viz = await visualization_agent(state_after_calc)
    state_after_dash = await dashboard_agent(state_after_viz)
    state_after_ds = await datasource_agent(state_after_dash)
    
    result = await strategy_agent(state_after_ds)
    assert result['status'] == 'strategy_complete'
    assert result['final_report'] is not None
    assert 'executive_summary' in result['final_report']
    assert 'migration_recommendations' in result['final_report']

