"""
Interactive Query Troubleshooter for Agent 1 Enhanced

Manual query tool for testing and troubleshooting Agent 1 Enhanced queries.
Allows interactive querying of Tableau files with full exploration and retry logic.
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1_master import master_agent_explore, master_agent_query
from agents.query_router import route_query


class QueryTroubleshooter:
    """Interactive query troubleshooter for Agent 1 Enhanced"""
    
    def __init__(self, tableau_file_path: str):
        """
        Initialize the troubleshooter with a Tableau file
        
        Args:
            tableau_file_path: Path to the Tableau XML file
        """
        self.tableau_file_path = tableau_file_path
        self.state: AnalysisState = None
        self.conversation_history: list = []
        self.output_dir = "output/tableau_analyzer"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def initialize(self):
        """Initialize Master Agent with the Tableau file"""
        print("\n" + "="*70)
        print("🔧 INITIALIZING MASTER AGENT (Master-Worker Architecture)")
        print("="*70)
        print(f"📂 Loading file: {self.tableau_file_path}")
        
        # Create initial state
        self.state = AnalysisState(
            bi_tool_type="tableau",
            file_path=self.tableau_file_path,
            file_json={},
            inventory={},
            agent_1_ready=False,
            json_spec=None,
            complexity_analysis={},
            agent_2_questions=[],
            extracted_features={},
            agent_conversations=[],
            errors=[],
            component_index=None,
            sub_agent_results=None,
            master_ready=False,
            sub_agents_ready=None,
            sub_agent_specs=None
        )
        
        # Run master agent exploration
        print("\n🚀 Starting master-worker exploration...")
        self.state = master_agent_explore(self.state)
        
        if self.state.get("master_ready"):
            print("\n✅ Master Agent is ready for queries!")
            self._print_summary()
        else:
            print("\n❌ Master Agent initialization failed!")
            if self.state.get("errors"):
                for error in self.state["errors"]:
                    print(f"   • {error}")
            return False
        
        return True
    
    def _print_summary(self):
        """Print a summary of the exploration results"""
        inventory = self.state.get("inventory", {})
        summary = inventory.get("summary", {})
        component_index = self.state.get("component_index", {})
        sub_agents_ready = self.state.get("sub_agents_ready", {})
        
        print("\n" + "-"*70)
        print("📊 EXPLORATION SUMMARY")
        print("-"*70)
        print(f"   📄 Worksheets:   {summary.get('total_worksheets', len(inventory.get('worksheets', [])))}")
        print(f"   📊 Dashboards:   {summary.get('total_dashboards', len(inventory.get('dashboards', [])))}")
        print(f"   🗄️  Datasources:  {summary.get('total_datasources', len(inventory.get('datasources', [])))}")
        print(f"   🔢 Calculations: {summary.get('total_calculations', len(inventory.get('calculations', [])))}")
        
        print(f"\n   🤖 SUB-AGENT STATUS:")
        for agent_type, ready in sub_agents_ready.items():
            status = "✅" if ready else "❌"
            print(f"      {status} {agent_type.capitalize()}: {'Ready' if ready else 'Failed'}")
        print("-"*70)
    
    def _print_inventory(self):
        """Print detailed inventory"""
        inventory = self.state.get("inventory", {})
        
        print("\n" + "="*70)
        print("📋 DETAILED INVENTORY")
        print("="*70)
        
        # Worksheets
        worksheets = inventory.get("worksheets", [])
        if worksheets:
            print(f"\n📄 WORKSHEETS ({len(worksheets)}):")
            for i, ws in enumerate(worksheets[:10], 1):  # Show first 10
                name = ws.get("name", "Unknown")
                ws_id = ws.get("id", "N/A")
                print(f"   {i}. {name} (ID: {ws_id})")
            if len(worksheets) > 10:
                print(f"   ... and {len(worksheets) - 10} more")
        else:
            print("\n📄 WORKSHEETS: None found")
        
        # Dashboards
        dashboards = inventory.get("dashboards", [])
        if dashboards:
            print(f"\n📊 DASHBOARDS ({len(dashboards)}):")
            for i, db in enumerate(dashboards[:10], 1):
                name = db.get("name", "Unknown")
                db_id = db.get("id", "N/A")
                worksheets_used = db.get("worksheets_used", [])
                print(f"   {i}. {name} (ID: {db_id}, Worksheets: {len(worksheets_used)})")
            if len(dashboards) > 10:
                print(f"   ... and {len(dashboards) - 10} more")
        else:
            print("\n📊 DASHBOARDS: None found")
        
        # Datasources
        datasources = inventory.get("datasources", [])
        if datasources:
            print(f"\n🗄️  DATASOURCES ({len(datasources)}):")
            for i, ds in enumerate(datasources[:10], 1):
                name = ds.get("name", "Unknown")
                conn_type = ds.get("connection_type", "Unknown")
                print(f"   {i}. {name} (Type: {conn_type})")
            if len(datasources) > 10:
                print(f"   ... and {len(datasources) - 10} more")
        else:
            print("\n🗄️  DATASOURCES: None found")
        
        # Calculations
        calculations = inventory.get("calculations", [])
        if calculations:
            print(f"\n🔢 CALCULATIONS ({len(calculations)}):")
            for i, calc in enumerate(calculations[:10], 1):
                name = calc.get("name", "Unknown")
                formula = calc.get("formula", "N/A")
                formula_preview = formula[:50] + "..." if len(formula) > 50 else formula
                print(f"   {i}. {name}: {formula_preview}")
            if len(calculations) > 10:
                print(f"   ... and {len(calculations) - 10} more")
        else:
            print("\n🔢 CALCULATIONS: None found")
        
        print("\n" + "="*70)
    
    def _print_sub_agent_status(self):
        """Print status of all sub-agents"""
        sub_agents_ready = self.state.get("sub_agents_ready", {})
        sub_agent_results = self.state.get("sub_agent_results", {})
        
        print("\n" + "="*70)
        print("🤖 SUB-AGENT STATUS")
        print("="*70)
        
        for agent_type in ["worksheets", "dashboards", "datasources", "calculations"]:
            ready = sub_agents_ready.get(agent_type, False)
            status_icon = "✅" if ready else "❌"
            status_text = "Ready" if ready else "Failed/Not Ready"
            
            result = sub_agent_results.get(agent_type, {})
            if result:
                component_type = agent_type.rstrip('s')  # Remove 's' for singular
                count_key = f"{component_type}s" if component_type != "calculation" else "calculations"
                count = len(result.get(count_key, []))
                print(f"   {status_icon} {agent_type.capitalize()}: {status_text} ({count} items)")
            else:
                print(f"   {status_icon} {agent_type.capitalize()}: {status_text}")
        
        print("="*70)
    
    def _print_component_index(self):
        """Print component index"""
        component_index = self.state.get("component_index", {})
        
        if not component_index:
            print("❌ Component index not available")
            return
        
        print("\n" + "="*70)
        print("📋 COMPONENT INDEX")
        print("="*70)
        
        for component_type in ["worksheets", "dashboards", "datasources", "calculations"]:
            comp_data = component_index.get(component_type, {})
            count = comp_data.get("count", 0)
            names = comp_data.get("names", [])
            location = comp_data.get("location", "N/A")
            
            print(f"\n{component_type.upper()}:")
            print(f"   Count: {count}")
            print(f"   Location: {location}")
            if names:
                print(f"   Names: {', '.join(names[:10])}")
                if len(names) > 10:
                    print(f"   ... and {len(names) - 10} more")
        
        print("="*70)
    
    def _query_sub_agent_directly(self, agent_type: str, question: str):
        """Query a specific sub-agent directly"""
        from agents.agent_1_master import master_agent_query
        
        print(f"\n💬 Querying {agent_type.upper()} Sub-Agent: {question}")
        print("-"*70)
        
        # Create a modified question to target specific agent
        targeted_question = f"About {agent_type}: {question}"
        
        answer = master_agent_query(self.state, targeted_question, asking_agent="manual")
        
        # Add to conversation history
        self.conversation_history.append({
            "question": question,
            "answer": answer,
            "routing": f"{agent_type}_direct",
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"\n📝 Answer:\n{answer}")
        print("-"*70)
    
    def _save_conversation_history(self):
        """Save conversation history to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{self.output_dir}/manual_queries_{timestamp}.json"
        
        component_index = self.state.get("component_index", {})
        sub_agents_ready = self.state.get("sub_agents_ready", {})
        
        output_data = {
            "tableau_file": self.tableau_file_path,
            "timestamp": timestamp,
            "architecture": "master-worker",
            "exploration_summary": {
                "master_ready": self.state.get("master_ready", False),
                "sub_agents_ready": sub_agents_ready,
                "component_counts": {
                    "worksheets": component_index.get("worksheets", {}).get("count", 0),
                    "dashboards": component_index.get("dashboards", {}).get("count", 0),
                    "datasources": component_index.get("datasources", {}).get("count", 0),
                    "calculations": component_index.get("calculations", {}).get("count", 0)
                }
            },
            "conversation_history": self.conversation_history,
            "inventory_summary": {
                "worksheets": len(self.state.get("inventory", {}).get("worksheets", [])),
                "dashboards": len(self.state.get("inventory", {}).get("dashboards", [])),
                "datasources": len(self.state.get("inventory", {}).get("datasources", [])),
                "calculations": len(self.state.get("inventory", {}).get("calculations", []))
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Conversation history saved to: {output_file}")
        return output_file
    
    def run(self):
        """Run the interactive query loop"""
        if not self.state or not self.state.get("master_ready"):
            print("❌ Master Agent not initialized. Cannot run query loop.")
            return
        
        print("\n" + "="*70)
        print("💬 INTERACTIVE QUERY MODE (Master-Worker Architecture)")
        print("="*70)
        print("\nCommands:")
        print("  • Type a question to query (auto-routed to appropriate sub-agent)")
        print("  • 'explore' - Re-run exploration")
        print("  • 'inventory' - Show detailed inventory")
        print("  • 'summary' - Show exploration summary")
        print("  • 'sub-agents' - Show sub-agent status")
        print("  • 'index' - Show component index")
        print("  • 'query-worksheet <question>' - Query worksheet sub-agent directly")
        print("  • 'query-dashboard <question>' - Query dashboard sub-agent directly")
        print("  • 'query-datasource <question>' - Query datasource sub-agent directly")
        print("  • 'query-calculation <question>' - Query calculation sub-agent directly")
        print("  • 'clear' - Clear conversation history")
        print("  • 'history' - Show conversation history")
        print("  • 'save' - Save conversation history to file")
        print("  • 'exit' or 'quit' - Exit troubleshooter")
        print("\n" + "-"*70)
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['exit', 'quit']:
                    print("\n👋 Exiting troubleshooter...")
                    if self.conversation_history:
                        save = input("Save conversation history? (y/n): ").strip().lower()
                        if save == 'y':
                            self._save_conversation_history()
                    break
                
                elif user_input.lower() == 'explore':
                    print("\n🔄 Re-running exploration...")
                    self.state = master_agent_explore(self.state)
                    if self.state.get("master_ready"):
                        print("✅ Exploration complete!")
                        self._print_summary()
                    else:
                        print("❌ Exploration failed!")
                
                elif user_input.lower() == 'inventory':
                    self._print_inventory()
                
                elif user_input.lower() == 'summary':
                    self._print_summary()
                
                elif user_input.lower() == 'clear':
                    self.conversation_history = []
                    if "agent_conversations" in self.state:
                        self.state["agent_conversations"] = []
                    print("✅ Conversation history cleared")
                
                elif user_input.lower() == 'history':
                    if self.conversation_history:
                        print("\n" + "="*70)
                        print("📜 CONVERSATION HISTORY")
                        print("="*70)
                        for i, entry in enumerate(self.conversation_history, 1):
                            print(f"\n{i}. Q: {entry.get('question', 'N/A')}")
                            answer = entry.get('answer', 'N/A')
                            answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
                            print(f"   A: {answer_preview}")
                        print("="*70)
                    else:
                        print("📜 No conversation history")
                
                elif user_input.lower() == 'save':
                    output_file = self._save_conversation_history()
                    print(f"✅ Saved to {output_file}")
                
                elif user_input.lower() == 'sub-agents':
                    self._print_sub_agent_status()
                
                elif user_input.lower() == 'index':
                    self._print_component_index()
                
                elif user_input.lower().startswith('query-worksheet '):
                    question = user_input[len('query-worksheet '):].strip()
                    if question:
                        self._query_sub_agent_directly("worksheet", question)
                    else:
                        print("❌ Please provide a question after 'query-worksheet'")
                
                elif user_input.lower().startswith('query-dashboard '):
                    question = user_input[len('query-dashboard '):].strip()
                    if question:
                        self._query_sub_agent_directly("dashboard", question)
                    else:
                        print("❌ Please provide a question after 'query-dashboard'")
                
                elif user_input.lower().startswith('query-datasource '):
                    question = user_input[len('query-datasource '):].strip()
                    if question:
                        self._query_sub_agent_directly("datasource", question)
                    else:
                        print("❌ Please provide a question after 'query-datasource'")
                
                elif user_input.lower().startswith('query-calculation '):
                    question = user_input[len('query-calculation '):].strip()
                    if question:
                        self._query_sub_agent_directly("calculation", question)
                    else:
                        print("❌ Please provide a question after 'query-calculation'")
                
                else:
                    # Treat as a query - use master agent routing
                    print(f"\n💬 Querying: {user_input}")
                    print("-"*70)
                    
                    # Show routing decision
                    target_agent, direct_answer = route_query(user_input, self.state)
                    if direct_answer:
                        print(f"📍 Routing: Answered from index (no agent call needed)")
                        answer = direct_answer
                    else:
                        print(f"📍 Routing: {target_agent.upper()} sub-agent")
                        answer = master_agent_query(
                            self.state, 
                            user_input, 
                            asking_agent="manual"
                        )
                    
                    # Add to conversation history
                    self.conversation_history.append({
                        "question": user_input,
                        "answer": answer,
                        "routing": target_agent,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"\n📝 Answer:\n{answer}")
                    print("-"*70)
            
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Exiting...")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()


def main():
    """Main entry point for the query troubleshooter"""
    if len(sys.argv) < 2:
        print("Usage: python -m tableau_analyzer.tools.query_troubleshooter <path_to_tableau_file>")
        print("\nExample:")
        print("  python -m tableau_analyzer.tools.query_troubleshooter input_files/tableau/sales_summary_final.xml")
        sys.exit(1)
    
    tableau_file = sys.argv[1]
    
    # Resolve path
    if not os.path.isabs(tableau_file):
        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent
        tableau_file = str(project_root / tableau_file)
    
    if not os.path.exists(tableau_file):
        print(f"❌ Error: File not found: {tableau_file}")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("🔧 MASTER AGENT - QUERY TROUBLESHOOTER")
    print("="*70)
    print(f"📂 Tableau File: {tableau_file}")
    print("="*70)
    
    troubleshooter = QueryTroubleshooter(tableau_file)
    
    if troubleshooter.initialize():
        troubleshooter.run()
    else:
        print("\n❌ Failed to initialize troubleshooter")
        sys.exit(1)


if __name__ == "__main__":
    main()
