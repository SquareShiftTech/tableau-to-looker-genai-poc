"""
Test Comprehensive Workflow: Full Data Extraction
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.comprehensive_workflow import run_comprehensive_workflow


def test_comprehensive_workflow():
    """Test the comprehensive workflow end-to-end"""
    
    print("\n" + "="*70)
    print("🧪 TEST: COMPREHENSIVE WORKFLOW")
    print("="*70)
    
    # Path to test file - resolve from project root
    project_root = Path(__file__).parent.parent.parent
    test_file = project_root / "input_files" / "tableau" / "sales_summary_final.xml"
    test_file = str(test_file)
    
    print(f"Test file: {test_file}")
    print("Expected: Agent 1 explores, Agent 2 defines schema, Agent 3 extracts features")
    
    # Run workflow
    final_state = run_comprehensive_workflow(test_file, bi_tool_type="tableau")
    
    # Validate results
    print("\n" + "="*70)
    print("📊 VALIDATION")
    print("="*70)
    
    passed = True
    
    # Check Agent 1 results
    if not final_state.get("agent_1_ready"):
        print("❌ Agent 1 not marked as ready")
        passed = False
    else:
        print(f"✅ Agent 1 completed in {final_state.get('agent_1_attempts', 1)} attempt(s)")
    
    # Check inventory
    inventory = final_state.get("inventory", {})
    if len(inventory.get("worksheets", [])) == 0:
        print("❌ No worksheets found in inventory")
        passed = False
    else:
        print(f"✅ Found {len(inventory.get('worksheets', []))} worksheets")
    
    # Check feature schema
    schema = final_state.get("feature_schema", {})
    if not schema:
        print("❌ No feature schema generated")
        passed = False
    else:
        total_features = sum(len(s) for s in schema.values())
        print(f"✅ Feature schema created ({total_features} features defined)")
    
    # Check extracted features
    extracted = final_state.get("extracted_features", {})
    if not extracted:
        print("❌ No features extracted")
        passed = False
    else:
        print(f"✅ Data extracted:")
        print(f"   • Dashboards: {len(extracted.get('dashboards', []))}")
        print(f"   • Worksheets: {len(extracted.get('worksheets', []))}")
        print(f"   • Datasources: {len(extracted.get('datasources', []))}")
        print(f"   • Calculations: {len(extracted.get('calculations', []))}")
    
    # Check extraction stats
    features_attempted = final_state.get("features_attempted", 0)
    features_successful = final_state.get("features_successful", 0)
    features_failed = final_state.get("features_failed", 0)
    
    if features_attempted > 0:
        success_rate = (features_successful / features_attempted) * 100
        print(f"\n📈 Extraction Statistics:")
        print(f"   Attempted: {features_attempted}")
        print(f"   Successful: {features_successful} ({success_rate:.1f}%)")
        print(f"   Failed: {features_failed}")
        print(f"   Retries: {final_state.get('agent_3_retry_count', 0)}")
        
        if success_rate < 50:
            print("   ⚠️  Success rate below threshold")
            passed = False
    
    # Check conversations
    conversations = final_state.get("agent_conversations", [])
    print(f"\n💬 {len(conversations)} conversations logged")
    
    # Overall result
    print("\n" + "="*70)
    if passed and not final_state.get("errors"):
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
        if final_state.get("errors"):
            print("\nErrors:")
            for error in final_state.get("errors", []):
                print(f"  • {error}")
    print("="*70)
    
    return final_state


if __name__ == "__main__":
    test_comprehensive_workflow()
