"""
Convert complexity_analysis_results.json to HTML report matching looker_migration_template format
"""

import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path


def load_json_data(json_path: str) -> dict:
    """Load JSON data from file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_complexity_class(complexity: str) -> str:
    """Get CSS class for complexity badge"""
    complexity_lower = complexity.lower()
    if complexity_lower == "low":
        return "complexity-low"
    elif complexity_lower == "medium":
        return "complexity-medium"
    elif complexity_lower == "high":
        return "complexity-high"
    elif complexity_lower == "critical":
        return "complexity-critical"
    return "complexity-medium"


def calculate_statistics(data: dict) -> dict:
    """Calculate summary statistics from JSON data"""
    stats = {
        "total_workbooks": set(),
        "total_dashboards": set(),
        "total_worksheets": set(),
        "visualization_counts": defaultdict(int),
        "calculated_field_counts": defaultdict(int),
        "dashboard_counts": defaultdict(int),
        "complexity_distribution": defaultdict(int),
        "feature_usage": defaultdict(lambda: {"workbooks": set(), "dashboards": set()})
    }
    
    # Process visualizations
    for item in data.get("visualization_complexity", []):
        stats["total_workbooks"].add(item.get("workbook_name", ""))
        stats["total_worksheets"].add(item.get("worksheet_name", ""))
        complexity = item.get("complexity", "Medium")
        stats["complexity_distribution"][complexity] += 1
        feature = item.get("feature", "")
        stats["feature_usage"][f"Charts-{feature}"]["workbooks"].add(item.get("workbook_name", ""))
        for dash in item.get("dashboard_names", []):
            stats["total_dashboards"].add(dash)
            stats["feature_usage"][f"Charts-{feature}"]["dashboards"].add(dash)
    
    # Process calculated fields
    for item in data.get("calculated_field_complexity", []):
        stats["total_workbooks"].add(item.get("workbook_name", ""))
        stats["total_worksheets"].add(item.get("worksheet_name", ""))
        complexity = item.get("complexity", "Medium")
        stats["complexity_distribution"][complexity] += 1
        feature = item.get("feature", "")
        stats["feature_usage"][f"Calculated Fields-{feature}"]["workbooks"].add(item.get("workbook_name", ""))
    
    # Process dashboards
    for item in data.get("dashboard_complexity", []):
        stats["total_workbooks"].add(item.get("workbook_name", ""))
        dashboard_name = item.get("dashboard_name", "")
        if dashboard_name:
            stats["total_dashboards"].add(dashboard_name)
        complexity = item.get("complexity", "Medium")
        stats["complexity_distribution"][complexity] += 1
        feature = item.get("feature", "")
        feature_area = item.get("feature_area", "")
        stats["feature_usage"][f"{feature_area}-{feature}"]["workbooks"].add(item.get("workbook_name", ""))
        if dashboard_name:
            stats["feature_usage"][f"{feature_area}-{feature}"]["dashboards"].add(dashboard_name)
    
    # Convert sets to counts
    stats["total_workbooks"] = len(stats["total_workbooks"])
    stats["total_dashboards"] = len(stats["total_dashboards"])
    stats["total_worksheets"] = len(stats["total_worksheets"])
    
    # Convert feature usage sets to counts
    for key in stats["feature_usage"]:
        stats["feature_usage"][key]["workbooks"] = len(stats["feature_usage"][key]["workbooks"])
        stats["feature_usage"][key]["dashboards"] = len(stats["feature_usage"][key]["dashboards"])
    
    return stats


def aggregate_features(data: dict) -> dict:
    """Aggregate features by type and complexity"""
    aggregated = {
        "visualizations": defaultdict(lambda: {"workbooks": set(), "dashboards": set(), "complexity": "Medium"}),
        "calculated_fields": defaultdict(lambda: {"workbooks": set(), "worksheets": set(), "complexity": "Medium", "examples": []}),
        "dashboards": defaultdict(lambda: {"workbooks": set(), "dashboards": set(), "complexity": "Medium"})
    }
    
    # Aggregate visualizations
    for item in data.get("visualization_complexity", []):
        feature = item.get("feature", "")
        feature_area = item.get("feature_area", "")
        key = f"{feature_area}-{feature}"
        aggregated["visualizations"][key]["workbooks"].add(item.get("workbook_name", ""))
        aggregated["visualizations"][key]["complexity"] = item.get("complexity", "Medium")
        for dash in item.get("dashboard_names", []):
            aggregated["visualizations"][key]["dashboards"].add(dash)
    
    # Aggregate calculated fields
    for item in data.get("calculated_field_complexity", []):
        feature = item.get("feature", "")
        key = f"Calculated Fields-{feature}"
        aggregated["calculated_fields"][key]["workbooks"].add(item.get("workbook_name", ""))
        aggregated["calculated_fields"][key]["worksheets"].add(item.get("worksheet_name", ""))
        aggregated["calculated_fields"][key]["complexity"] = item.get("complexity", "Medium")
        # Store example (field_name and formula)
        if len(aggregated["calculated_fields"][key]["examples"]) < 3:
            aggregated["calculated_fields"][key]["examples"].append({
                "field_name": item.get("field_name", ""),
                "formula": item.get("formula", "")
            })
    
    # Aggregate dashboards
    for item in data.get("dashboard_complexity", []):
        feature = item.get("feature", "")
        feature_area = item.get("feature_area", "")
        key = f"{feature_area}-{feature}"
        aggregated["dashboards"][key]["workbooks"].add(item.get("workbook_name", ""))
        aggregated["dashboards"][key]["complexity"] = item.get("complexity", "Medium")
        dashboard_name = item.get("dashboard_name", "")
        if dashboard_name:
            aggregated["dashboards"][key]["dashboards"].add(dashboard_name)
    
    # Convert sets to counts
    for category in aggregated:
        for key in aggregated[category]:
            aggregated[category][key]["workbooks"] = len(aggregated[category][key]["workbooks"])
            if "dashboards" in aggregated[category][key]:
                aggregated[category][key]["dashboards"] = len(aggregated[category][key]["dashboards"])
            if "worksheets" in aggregated[category][key]:
                aggregated[category][key]["worksheets"] = len(aggregated[category][key]["worksheets"])
    
    return aggregated


def generate_html(data: dict, stats: dict, aggregated: dict) -> str:
    """Generate HTML report"""
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y - %I:%M %p")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tableau to Looker Migration Assessment Report</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: #f8f9fa;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        /* Header Section */
        .report-header {{
            background: linear-gradient(135deg, #2d7d4a 0%, #1a5c35 100%);
            color: white;
            padding: 40px;
            position: relative;
        }}
        
        .logo-container {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .logo {{
            width: 180px;
            height: 50px;
            background: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.3em;
            color: #2d7d4a;
            letter-spacing: -1px;
        }}
        
        .report-header h1 {{
            font-size: 2.2em;
            margin-bottom: 10px;
        }}
        
        .report-metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.3);
        }}
        
        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .metadata-label {{
            font-size: 0.85em;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .metadata-value {{
            font-size: 1.1em;
            font-weight: 600;
            margin-top: 5px;
        }}
        
        /* Section Styles */
        .section {{
            padding: 40px;
            page-break-inside: avoid;
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #2d7d4a;
            margin-bottom: 25px;
            padding-bottom: 10px;
            border-bottom: 3px solid #2d7d4a;
        }}
        
        .section-subtitle {{
            font-size: 1.4em;
            color: #1a5c35;
            margin: 30px 0 15px 0;
        }}
        
        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
        }}
        
        thead {{
            background: #2d7d4a;
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        tbody tr:hover {{
            background: #f8f9fa;
        }}
        
        tbody tr:nth-child(even) {{
            background: #fafbfc;
        }}
        
        /* Complexity Badges */
        .complexity-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        .complexity-low {{
            background: #d4edda;
            color: #155724;
        }}
        
        .complexity-medium {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .complexity-high {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .complexity-critical {{
            background: #dc3545;
            color: white;
        }}
        
        /* Effort Box */
        .effort-box {{
            background: linear-gradient(135deg, #2d7d4a 0%, #1a5c35 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
            text-align: center;
        }}
        
        .effort-label {{
            font-size: 1em;
            opacity: 0.9;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .effort-value {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        
        .effort-detail {{
            font-size: 1em;
            opacity: 0.85;
            margin-top: 5px;
        }}
        
        /* Chart Container */
        .chart-container {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        
        .chart-title {{
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 15px;
            color: #495057;
        }}
        
        /* Footer */
        .report-footer {{
            background: #2c3e50;
            color: white;
            padding: 30px 40px;
            text-align: center;
        }}
        
        .footer-text {{
            font-size: 0.9em;
            opacity: 0.8;
        }}
        
        /* Print Styles */
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .section {{
                page-break-inside: avoid;
            }}
        }}
        
        /* Utility Classes */
        .text-center {{
            text-align: center;
        }}
        
        .mb-20 {{
            margin-bottom: 20px;
        }}
        
        .mt-20 {{
            margin-top: 20px;
        }}
        
        .formula-text {{
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            background: #f8f9fa;
            padding: 4px 8px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="report-header">
            <div class="logo-container">
                <div class="logo">SQUARESHIFT</div>
            </div>
            <h1>Tableau to Looker Migration Assessment Report</h1>
            <div class="report-metadata">
                <div class="metadata-item">
                    <span class="metadata-label">Date Generated</span>
                    <span class="metadata-value">{date_str}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Total Workbooks</span>
                    <span class="metadata-value">{stats['total_workbooks']}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Total Dashboards</span>
                    <span class="metadata-value">{stats['total_dashboards']}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Total Worksheets</span>
                    <span class="metadata-value">{stats['total_worksheets']}</span>
                </div>
            </div>
        </div>

        <!-- 1. Executive Summary -->
        <div class="section">
            <h2 class="section-title">1. Executive Summary</h2>
            
            <p style="margin-bottom: 20px; font-size: 1.05em; line-height: 1.8;">
                This assessment analyzed the Tableau environment ({stats['total_workbooks']} workbooks, {stats['total_dashboards']} dashboards, {stats['total_worksheets']} worksheets) 
                focusing on inventory, usage, and complexity to inform the Looker migration strategy.
            </p>

            <div class="chart-container">
                <div class="chart-title">High-Level Complexity Overview</div>
                <table>
                    <thead>
                        <tr>
                            <th>Complexity Level</th>
                            <th>Count</th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    # Add complexity distribution
    for complexity in ["Low", "Medium", "High", "Critical"]:
        count = stats["complexity_distribution"].get(complexity, 0)
        if count > 0:
            html += f"""
                        <tr>
                            <td><span class="complexity-badge {get_complexity_class(complexity)}">{complexity}</span></td>
                            <td>{count}</td>
                        </tr>"""
    
    html += """
                    </tbody>
                </table>
            </div>

            <div class="chart-container mt-20">
                <div class="chart-title">Key Findings</div>
                <table>
                    <thead>
                        <tr>
                            <th>Area</th>
                            <th>Complexity / Impact</th>
                            <th>Workbooks Affected</th>
                            <th>Dashboards Affected</th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    # Add feature usage summary
    for feature_key, usage in sorted(stats["feature_usage"].items(), key=lambda x: x[0]):
        feature_area, feature = feature_key.split("-", 1) if "-" in feature_key else (feature_key, "")
        complexity = "Medium"  # Default, could be calculated from items
        workbooks_count = usage.get("workbooks", 0)
        dashboards_count = usage.get("dashboards", 0)
        
        if workbooks_count > 0 or dashboards_count > 0:
            html += f"""
                        <tr>
                            <td><strong>{feature_area}</strong></td>
                            <td><span class="complexity-badge {get_complexity_class(complexity)}">{complexity}</span></td>
                            <td>{workbooks_count} workbooks</td>
                            <td>{dashboards_count} dashboards</td>
                        </tr>"""
    
    html += """
                    </tbody>
                </table>
            </div>

            <div class="effort-box">
                <div class="effort-label">Estimated Migration Effort</div>
                <div class="effort-value">TBD</div>
                <div class="effort-detail">(Based on complexity analysis)</div>
            </div>
        </div>

        <!-- 2. Inventory Summary -->
        <div class="section">
            <h2 class="section-title">2. Inventory Summary</h2>
            
            <table>
                <thead>
                    <tr>
                        <th>Asset Type</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Total Workbooks Assessed</strong></td>
                        <td>{stats['total_workbooks']}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Dashboards</strong></td>
                        <td>{stats['total_dashboards']}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Worksheets</strong></td>
                        <td>{stats['total_worksheets']}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 3. Complexity Analysis -->
        <div class="section">
            <h2 class="section-title">3. Complexity Analysis</h2>
            
            <h3 class="section-subtitle">3.1 Visualization Complexity Breakdown</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>Feature Area</th>
                        <th>Feature</th>
                        <th>Complexity</th>
                        <th>Workbooks Affected</th>
                        <th>Dashboards Affected</th>
                    </tr>
                </thead>
                <tbody>"""
    
    # Add visualization features
    for key, info in sorted(aggregated["visualizations"].items()):
        feature_area, feature = key.split("-", 1) if "-" in key else (key, "")
        complexity = info.get("complexity", "Medium")
        workbooks = info.get("workbooks", 0)
        dashboards = info.get("dashboards", 0)
        
        html += f"""
                    <tr>
                        <td><strong>{feature_area}</strong></td>
                        <td>{feature}</td>
                        <td><span class="complexity-badge {get_complexity_class(complexity)}">{complexity}</span></td>
                        <td>{workbooks}</td>
                        <td>{dashboards}</td>
                    </tr>"""
    
    html += """
                </tbody>
            </table>

            <h3 class="section-subtitle">3.2 Calculated Field Complexity Breakdown</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>Feature Area</th>
                        <th>Feature</th>
                        <th>Complexity</th>
                        <th>Workbooks Affected</th>
                        <th>Worksheets Affected</th>
                        <th>Example Fields</th>
                    </tr>
                </thead>
                <tbody>"""
    
    # Add calculated field features
    for key, info in sorted(aggregated["calculated_fields"].items()):
        feature_area, feature = key.split("-", 1) if "-" in key else (key, "")
        complexity = info.get("complexity", "Medium")
        workbooks = info.get("workbooks", 0)
        worksheets = info.get("worksheets", 0)
        examples = info.get("examples", [])
        example_text = ", ".join([ex.get("field_name", "") for ex in examples[:3]])
        
        html += f"""
                    <tr>
                        <td><strong>{feature_area}</strong></td>
                        <td>{feature}</td>
                        <td><span class="complexity-badge {get_complexity_class(complexity)}">{complexity}</span></td>
                        <td>{workbooks}</td>
                        <td>{worksheets}</td>
                        <td>{example_text if example_text else "N/A"}</td>
                    </tr>"""
    
    html += """
                </tbody>
            </table>

            <h3 class="section-subtitle">3.3 Dashboard Complexity Breakdown</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>Feature Area</th>
                        <th>Feature</th>
                        <th>Complexity</th>
                        <th>Workbooks Affected</th>
                        <th>Dashboards Affected</th>
                    </tr>
                </thead>
                <tbody>"""
    
    # Add dashboard features
    for key, info in sorted(aggregated["dashboards"].items()):
        feature_area, feature = key.split("-", 1) if "-" in key else (key, "")
        complexity = info.get("complexity", "Medium")
        workbooks = info.get("workbooks", 0)
        dashboards = info.get("dashboards", 0)
        
        html += f"""
                    <tr>
                        <td><strong>{feature_area}</strong></td>
                        <td>{feature}</td>
                        <td><span class="complexity-badge {get_complexity_class(complexity)}">{complexity}</span></td>
                        <td>{workbooks}</td>
                        <td>{dashboards}</td>
                    </tr>"""
    
    html += """
                </tbody>
            </table>
        </div>

        <!-- 4. Detailed Feature Analysis -->
        <div class="section">
            <h2 class="section-title">4. Detailed Feature Analysis</h2>
            
            <h3 class="section-subtitle">4.1 Visualization Details</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>Feature</th>
                        <th>Complexity</th>
                        <th>Worksheet</th>
                        <th>Workbook</th>
                        <th>Dashboards</th>
                    </tr>
                </thead>
                <tbody>"""
    
    # Add detailed visualization items (limit to first 100 for readability)
    for item in data.get("visualization_complexity", [])[:100]:
        feature = item.get("feature", "")
        complexity = item.get("complexity", "Medium")
        worksheet = item.get("worksheet_name", "")
        workbook = item.get("workbook_name", "")
        dashboards = ", ".join(item.get("dashboard_names", [])) or "None"
        
        html += f"""
                    <tr>
                        <td>{feature}</td>
                        <td><span class="complexity-badge {get_complexity_class(complexity)}">{complexity}</span></td>
                        <td>{worksheet}</td>
                        <td>{workbook}</td>
                        <td>{dashboards}</td>
                    </tr>"""
    
    html += """
                </tbody>
            </table>

            <h3 class="section-subtitle">4.2 Calculated Field Details</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>Field Name</th>
                        <th>Formula</th>
                        <th>Complexity</th>
                        <th>Worksheet</th>
                        <th>Workbook</th>
                    </tr>
                </thead>
                <tbody>"""
    
    # Add detailed calculated field items (limit to first 100)
    for item in data.get("calculated_field_complexity", [])[:100]:
        field_name = item.get("field_name", "")
        formula = item.get("formula", "")
        complexity = item.get("complexity", "Medium")
        worksheet = item.get("worksheet_name", "")
        workbook = item.get("workbook_name", "")
        
        html += f"""
                    <tr>
                        <td>{field_name}</td>
                        <td><span class="formula-text">{formula[:100]}{'...' if len(formula) > 100 else ''}</span></td>
                        <td><span class="complexity-badge {get_complexity_class(complexity)}">{complexity}</span></td>
                        <td>{worksheet}</td>
                        <td>{workbook}</td>
                    </tr>"""
    
    html += """
                </tbody>
            </table>

            <h3 class="section-subtitle">4.3 Dashboard Details</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>Feature</th>
                        <th>Complexity</th>
                        <th>Dashboard</th>
                        <th>Workbook</th>
                        <th>Component Count</th>
                    </tr>
                </thead>
                <tbody>"""
    
    # Add detailed dashboard items
    for item in data.get("dashboard_complexity", []):
        feature = item.get("feature", "")
        complexity = item.get("complexity", "Medium")
        dashboard = item.get("dashboard_name", item.get("action_name", ""))
        workbook = item.get("workbook_name", "")
        component_count = item.get("component_count", "")
        
        html += f"""
                    <tr>
                        <td>{feature}</td>
                        <td><span class="complexity-badge {get_complexity_class(complexity)}">{complexity}</span></td>
                        <td>{dashboard}</td>
                        <td>{workbook}</td>
                        <td>{component_count if component_count else "N/A"}</td>
                    </tr>"""
    
    html += """
                </tbody>
            </table>
        </div>

        <!-- Footer -->
        <div class="report-footer">
            <div class="footer-text">
                Generated by Tableau to Looker Migration Assessment Tool | SquareShift
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return html


def main():
    """Main function to convert JSON to HTML"""
    json_path = Path("evaluations/complexity_analysis_results.json")
    output_path = Path("evaluations/complexity_analysis_report.html")
    
    print(f"Loading JSON data from {json_path}...")
    data = load_json_data(str(json_path))
    
    print("Calculating statistics...")
    stats = calculate_statistics(data)
    
    print("Aggregating features...")
    aggregated = aggregate_features(data)
    
    print("Generating HTML report...")
    html = generate_html(data, stats, aggregated)
    
    print(f"Writing HTML to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Report generated successfully: {output_path}")
    print(f"   - Workbooks: {stats['total_workbooks']}")
    print(f"   - Dashboards: {stats['total_dashboards']}")
    print(f"   - Worksheets: {stats['total_worksheets']}")


if __name__ == "__main__":
    main()
