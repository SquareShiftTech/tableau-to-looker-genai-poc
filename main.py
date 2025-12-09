"""Entry point for BI Assessment Accelerator."""
import asyncio
from config.settings import load_settings
from workflows.assessment_workflow import create_assessment_workflow
from models.state import AssessmentState
from utils.logger import logger


async def main():
    """Main entry point for the application."""
    logger.info("Starting BI Assessment Accelerator")
    
    # Load settings
    settings = load_settings()
    logger.info(f"Loaded settings for project: {settings.gcp_project_id}")
    
    # Create workflow
    workflow = create_assessment_workflow()
    logger.info("Workflow created successfully")
    
    # Create initial state
    initial_state = AssessmentState(
        job_id="assessment_001",
        source_files=[
            {"platform": "tableau", "file_path": "input_files/tableau/sales_summary_final.xml"},
        ],
        # Legacy fields (kept for backward compatibility)
        file_analysis_strategy=None,
        strategy_refinement_needed=None,
        strategy_refinement_count=0,
        # New architecture fields
        parsed_elements_paths=None,
        output_dir=None,
        # Component discovery
        discovered_components=None,
        # Parsing outputs
        parsed_metrics=None,
        parsed_dashboards=None,
        parsed_visualizations=None,
        parsed_datasources=None,
        # Specialized agent outputs
        calculation_analysis=None,
        visualization_analysis=None,
        dashboard_analysis=None,
        datasource_analysis=None,
        # Final report
        final_report=None,
        # Status
        status="initial",
        errors=[],
    )
    
    logger.info(f"Starting workflow with job_id: {initial_state['job_id']}")
    
    # Run workflow
    try:
        result = await workflow.ainvoke(initial_state)
        
        logger.info("Workflow completed successfully")
        logger.info(f"Final status: {result['status']}")
        
        # Print final report
        if result.get('final_report'):
            report = result['final_report']
            print("\n" + "="*80)
            print("FINAL ASSESSMENT REPORT")
            print("="*80)
            print(f"\nExecutive Summary:\n{report.get('executive_summary', 'N/A')}")
            print(f"\nEstimated Total Effort: {report.get('final_estimated_effort_hours', 0)} hours")
            print(f"\nMigration Recommendations:")
            for i, rec in enumerate(report.get('migration_recommendations', []), 1):
                print(f"  {i}. {rec}")
            print("\n" + "="*80)
        else:
            logger.warning("No final report generated")
            
    except Exception as e:
        logger.error(f"Workflow failed with error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

