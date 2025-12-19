"""Main entry point for Tableau Migration Accelerator"""
import xmltodict
import json
import sys
from pathlib import Path

from database.db_manager import DatabaseManager
from agents.workflow import create_workflow


def convert_xml_to_json(xml_file_path: str) -> dict:
    """Convert Tableau XML to JSON"""
    with open(xml_file_path, 'r', encoding='utf-8') as file:
        xml_content = file.read()
    
    json_data = xmltodict.parse(xml_content)
    return json_data


def main():
    """Main execution function"""
    
    print("=" * 60)
    print("🚀 Tableau Migration Accelerator with SQL Agent")
    print("=" * 60)
    
    # Initialize database
    print("\n1️⃣  Initializing database...")
    db = DatabaseManager()
    db.initialize_database()
    
    # Load Tableau XML file
    print("\n2️⃣  Loading Tableau XML...")
    
    # Check if file path provided as argument
    if len(sys.argv) > 1:
        xml_file_path = sys.argv[1]
    else:
        xml_file_path = "input_files/tableau/sales_summary_final.xml"
    
    if not Path(xml_file_path).exists():
        print(f"❌ File not found: {xml_file_path}")
        print("Usage: python main.py <path_to_tableau_xml>")
        return
    
    json_data = convert_xml_to_json(xml_file_path)
    file_name = Path(xml_file_path).stem
    print(f"✅ Loaded XML file: {file_name}")
    
    # Create and run workflow
    print("\n3️⃣  Starting workflow...")
    workflow = create_workflow()
    
    result = workflow.invoke({
        "file_name": f"{file_name}.twb",
        "raw_json": json_data,
        "status": "started",
        "errors": []
    })
    
    # Print results
    print("\n" + "=" * 60)
    print("📋 WORKFLOW RESULTS")
    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"File ID: {result.get('file_id', 'N/A')}")
    
    if result.get('json_analysis'):
        analysis = result['json_analysis']
        print(f"Entities Found: {analysis.get('total_entities', 0)}")
        print(f"Max Depth: {analysis.get('max_depth', 0)}")
    
    if result.get('relational_schema'):
        schema = result['relational_schema']
        print(f"Tables Created: {len(schema.get('tables', []))}")
        for table in schema.get('tables', []):
            print(f"  - {table['table_name']}")
    
    if result.get('errors'):
        print(f"\n❌ Errors:")
        for error in result['errors']:
            print(f"  - {error}")
    else:
        print("\n✅ Process completed successfully!")
        print("\n💡 Next steps:")
        print("  - Query your relational tables for migration assessment")
        print("  - Run SQL queries to analyze Tableau complexity")
        print("  - Use the data for Looker migration planning")


if __name__ == "__main__":
    main()
