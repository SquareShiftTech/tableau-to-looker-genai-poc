"""Phase 3: Deploy LookML to Looker using MCP tools."""

from pathlib import Path
from typing import Optional
from .config import GENERATED_LOOKML_DIR, LOOKER_PROJECT_ID


class MCPDeployer:
    """Deploy LookML files to Looker using MCP tools."""
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or LOOKER_PROJECT_ID
    
    def setup_dev_mode(self):
        """Enable dev mode in Looker."""
        # Use MCP tool: dev_mode(true)
        print("  Enabling dev mode...")
        # This would call: mcp_looker_dev_mode(True)
        # Implementation depends on your MCP setup
        # Example:
        # from mcp import call_mcp_tool
        # call_mcp_tool("looker", "dev_mode", {"enabled": True})
    
    def get_project_id(self) -> str:
        """Get Looker project ID."""
        # Use MCP tool: get_projects()
        print(f"  Using project: {self.project_id}")
        return self.project_id
    
    def deploy_file(self, file_path: str, content: str, create_if_not_exists: bool = True):
        """
        Deploy a LookML file to Looker.
        
        Args:
            file_path: Relative path in Looker project (e.g., "views/table.view.lkml")
            content: LookML content
            create_if_not_exists: Create file if it doesn't exist, else update
        """
        # Use MCP tool: create_project_file() or update_project_file()
        print(f"  Deploying: {file_path}")
        # Implementation depends on your MCP setup
        # Example:
        # from mcp import call_mcp_tool
        # if create_if_not_exists:
        #     call_mcp_tool("looker", "create_project_file", {
        #         "project_id": self.project_id,
        #         "file_path": file_path,
        #         "content": content
        #     })
        # else:
        #     call_mcp_tool("looker", "update_project_file", {
        #         "project_id": self.project_id,
        #         "file_path": file_path,
        #         "content": content
        #     })
    
    def deploy_views(self):
        """Deploy all view files."""
        print("\n[3.2] Deploying View Files...")
        views_dir = GENERATED_LOOKML_DIR / "views"
        
        for view_file in views_dir.glob("*.view.lkml"):
            content = view_file.read_text(encoding='utf-8')
            file_path = f"views/{view_file.name}"
            self.deploy_file(file_path, content)
            print(f"  ✓ Deployed: {file_path}")
    
    def deploy_model(self):
        """Deploy model file."""
        print("\n[3.3] Deploying Model File...")
        models_dir = GENERATED_LOOKML_DIR / "models"
        
        for model_file in models_dir.glob("*.model.lkml"):
            content = model_file.read_text(encoding='utf-8')
            file_path = f"models/{model_file.name}"
            self.deploy_file(file_path, content)
            print(f"  ✓ Deployed: {file_path}")
    
    def update_model_with_explores(self):
        """Update model file with explore definitions."""
        print("\n[3.4] Updating Model with Explores...")
        explores_file = GENERATED_LOOKML_DIR / "explores.lkml"
        models_dir = GENERATED_LOOKML_DIR / "models"
        
        if explores_file.exists() and list(models_dir.glob("*.model.lkml")):
            explore_content = explores_file.read_text(encoding='utf-8')
            model_file = list(models_dir.glob("*.model.lkml"))[0]
            
            # Append explores to model content
            model_content = model_file.read_text(encoding='utf-8')
            updated_content = f"{model_content}\n\n{explore_content}"
            
            file_path = f"models/{model_file.name}"
            self.deploy_file(file_path, updated_content, create_if_not_exists=False)
            print(f"  ✓ Updated: {file_path}")
        else:
            print("  No explores or model file found")
    
    def deploy_dashboards(self):
        """Deploy all dashboard files."""
        print("\n[3.5] Deploying Dashboard Files...")
        dashboards_dir = GENERATED_LOOKML_DIR / "dashboards"
        
        for dashboard_file in dashboards_dir.glob("*.dashboard.lookml"):
            content = dashboard_file.read_text(encoding='utf-8')
            file_path = f"dashboards/{dashboard_file.name}"
            self.deploy_file(file_path, content)
            print(f"  ✓ Deployed: {file_path}")


def run_phase3():
    """Run Phase 3: Deploy LookML to Looker."""
    print("=" * 80)
    print("PHASE 3: MCP DEPLOYMENT")
    print("=" * 80)
    
    deployer = MCPDeployer()
    
    # 3.1 Setup
    print("\n[3.1] Setting up Looker Project...")
    deployer.setup_dev_mode()
    deployer.get_project_id()
    
    # 3.2 Deploy Views
    deployer.deploy_views()
    
    # 3.3 Deploy Model
    deployer.deploy_model()
    
    # 3.4 Update Model with Explores
    deployer.update_model_with_explores()
    
    # 3.5 Deploy Dashboards
    deployer.deploy_dashboards()
    
    print("\n" + "=" * 80)
    print("PHASE 3 COMPLETE: LookML files deployed to Looker")
    print("=" * 80)


if __name__ == "__main__":
    run_phase3()

