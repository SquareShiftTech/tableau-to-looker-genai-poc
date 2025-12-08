"""Sample dummy data for all agents."""
from typing import Dict, List, Any

# Exploration Agent Dummy Data
DUMMY_EXPLORATION = {
    "dashboards": [
        {"id": "dashboard_1", "name": "Sales Overview", "platform": "tableau"},
        {"id": "dashboard_2", "name": "Product Analysis", "platform": "tableau"},
        {"id": "dashboard_3", "name": "Executive Summary", "platform": "power_bi"},
    ],
    "metrics": [
        {"id": "metric_1", "name": "Total Sales", "platform": "tableau"},
        {"id": "metric_2", "name": "Profit Margin", "platform": "tableau"},
        {"id": "metric_3", "name": "Revenue Growth", "platform": "power_bi"},
        {"id": "metric_4", "name": "Customer Count", "platform": "microstrategy"},
    ],
    "visualizations": [
        {"id": "viz_1", "name": "Sales by Region", "type": "bar_chart", "platform": "tableau"},
        {"id": "viz_2", "name": "Revenue Trend", "type": "line_chart", "platform": "tableau"},
        {"id": "viz_3", "name": "Product Mix", "type": "pie_chart", "platform": "power_bi"},
    ],
    "datasources": [
        {"id": "ds_1", "name": "Sales Database", "type": "sql_server", "platform": "tableau"},
        {"id": "ds_2", "name": "Customer Data", "type": "postgresql", "platform": "power_bi"},
    ],
}

# Parsing Agent Dummy Data
DUMMY_PARSING = {
    "metrics": [
        {
            "id": "metric_1",
            "name": "Total Sales",
            "formula": "SUM([Sales])",
            "complexity": "low",
            "functions": ["SUM"],
            "dependencies": ["Sales"],
        },
        {
            "id": "metric_2",
            "name": "Profit Margin",
            "formula": "[Profit] / [Sales] * 100",
            "complexity": "medium",
            "functions": [],
            "dependencies": ["Profit", "Sales"],
        },
        {
            "id": "metric_3",
            "name": "Revenue Growth",
            "formula": "([Current Revenue] - [Previous Revenue]) / [Previous Revenue]",
            "complexity": "high",
            "functions": [],
            "dependencies": ["Current Revenue", "Previous Revenue"],
        },
    ],
    "dashboards": [
        {
            "id": "dashboard_1",
            "name": "Sales Overview",
            "worksheets": ["viz_1", "viz_2"],
            "filters": ["Region Filter", "Date Filter"],
            "interactions": ["drill_down", "filter_cross"],
        },
    ],
    "visualizations": [
        {
            "id": "viz_1",
            "name": "Sales by Region",
            "type": "bar_chart",
            "metrics": ["Total Sales"],
            "dimensions": ["Region"],
            "filters": ["Region Filter"],
        },
    ],
    "datasources": [
        {
            "id": "ds_1",
            "name": "Sales Database",
            "type": "sql_server",
            "tables": ["sales", "customers", "products"],
            "joins": [{"left": "sales", "right": "customers", "type": "inner"}],
        },
    ],
}

# Calculation Agent Dummy Data
DUMMY_CALCULATION = [
    {
        "job_id": "assessment_001",
        "metric_id": "metric_1",
        "metric_name": "Total Sales",
        "complexity_score": 2,
        "complexity_level": "low",
        "formula": "SUM([Sales])",
        "functions_used": ["SUM"],
        "dependencies": ["Sales"],
        "migration_effort_hours": 1,
        "notes": "Simple aggregation, easy to migrate",
    },
    {
        "job_id": "assessment_001",
        "metric_id": "metric_2",
        "metric_name": "Profit Margin",
        "complexity_score": 5,
        "complexity_level": "medium",
        "formula": "[Profit] / [Sales] * 100",
        "functions_used": [],
        "dependencies": ["Profit", "Sales"],
        "migration_effort_hours": 2,
        "notes": "Basic calculation, standard migration",
    },
    {
        "job_id": "assessment_001",
        "metric_id": "metric_3",
        "metric_name": "Revenue Growth",
        "complexity_score": 8,
        "complexity_level": "high",
        "formula": "([Current Revenue] - [Previous Revenue]) / [Previous Revenue]",
        "functions_used": [],
        "dependencies": ["Current Revenue", "Previous Revenue"],
        "migration_effort_hours": 4,
        "notes": "Complex calculation with multiple dependencies",
    },
]

# Visualization Agent Dummy Data
DUMMY_VISUALIZATION = [
    {
        "job_id": "assessment_001",
        "viz_id": "viz_1",
        "viz_name": "Sales by Region",
        "chart_type": "bar_chart",
        "complexity_score": 3,
        "complexity_level": "low",
        "metrics_count": 1,
        "dimensions_count": 1,
        "filters_count": 1,
        "migration_effort_hours": 1,
        "notes": "Standard bar chart, straightforward migration",
    },
    {
        "job_id": "assessment_001",
        "viz_id": "viz_2",
        "viz_name": "Revenue Trend",
        "chart_type": "line_chart",
        "complexity_score": 4,
        "complexity_level": "medium",
        "metrics_count": 1,
        "dimensions_count": 1,
        "filters_count": 0,
        "migration_effort_hours": 2,
        "notes": "Time series visualization",
    },
]

# Dashboard Agent Dummy Data
DUMMY_DASHBOARD = [
    {
        "job_id": "assessment_001",
        "dashboard_id": "dashboard_1",
        "dashboard_name": "Sales Overview",
        "complexity_score": 6,
        "complexity_level": "medium",
        "worksheets_count": 2,
        "filters_count": 2,
        "interactions_count": 2,
        "migration_effort_hours": 3,
        "notes": "Moderate complexity dashboard with filters and interactions",
    },
]

# Data Source Agent Dummy Data
DUMMY_DATASOURCE = [
    {
        "job_id": "assessment_001",
        "datasource_id": "ds_1",
        "datasource_name": "Sales Database",
        "datasource_type": "sql_server",
        "compatibility_score": 9,
        "compatibility_level": "high",
        "tables_count": 3,
        "joins_count": 1,
        "join_complexity": "low",
        "migration_effort_hours": 2,
        "notes": "Standard SQL Server, highly compatible",
    },
]

# Strategy Agent Dummy Data
DUMMY_STRATEGY = {
    "executive_summary": "Assessment completed for 3 dashboards, 4 metrics, 3 visualizations, and 2 datasources. Overall complexity is moderate with estimated migration effort of 15 hours.",
    "complexity_breakdown": {
        "low": 3,
        "medium": 4,
        "high": 1,
    },
    "consolidation_opportunities": [
        {
            "type": "duplicate_metrics",
            "description": "Total Sales metric appears in multiple dashboards",
            "potential_savings_hours": 2,
        },
        {
            "type": "similar_visualizations",
            "description": "Sales by Region and Revenue Trend can share data model",
            "potential_savings_hours": 1,
        },
    ],
    "migration_recommendations": [
        "Start with low-complexity components (Total Sales metric, Sales by Region visualization)",
        "Migrate datasources first to establish data foundation",
        "Consolidate duplicate metrics before migration",
        "Test dashboard interactions thoroughly after migration",
    ],
    "estimated_total_effort_hours": 15,
    "estimated_consolidation_savings_hours": 3,
    "final_estimated_effort_hours": 12,
}

