"""LLM service for Gemini API calls via Vertex AI."""
from typing import List, Dict, Any, Optional
import json
import os
from utils.logger import logger
from config.settings import get_settings
import vertexai
from vertexai.generative_models import GenerativeModel


class LLMService:
    """Service for interacting with Gemini LLM via Vertex AI."""
    
    def __init__(self):
        self.settings = get_settings()
        self.model_name = self.settings.gemini_model
        self.location = self.settings.vertex_ai_location
        
        # Initialize Vertex AI (uses default project from environment)
        project_id = self.settings.gcp_project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            vertexai.init(project=project_id, location=self.location)
            logger.info(f"Vertex AI initialized with project: {project_id}, location: {self.location}")
        else:
            logger.warning("No GCP project ID found, Vertex AI may use default project")
            vertexai.init(location=self.location)
        
        self.model = GenerativeModel(self.model_name)
        logger.info(f"LLMService initialized with model: {self.model_name}")
    
    async def analyze_components(
        self, 
        file_content: str, 
        platform: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Analyze metadata file to discover components using Gemini.
        
        Args:
            file_content: XML/JSON content of the BI file
            platform: BI platform (tableau, power_bi, microstrategy, cognos)
            file_path: Path to the file (for logging)
        
        Returns:
            Dict with discovered components matching DUMMY_EXPLORATION format
        """
        logger.info(f"Analyzing components from {platform} file: {file_path}")
        
        # Handle large files - sample if too big
        content_to_analyze = self._prepare_content(file_content)
        
        # Build structured prompt
        prompt = self._build_exploration_prompt(content_to_analyze, platform)
        
        # Call Gemini
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Parse JSON from response
            # Gemini might wrap JSON in markdown code blocks
            result_text = self._extract_json(result_text)
            discovered_components = json.loads(result_text)
            
            logger.info(f"Successfully discovered components from {file_path}")
            return discovered_components
            
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            # Return empty structure on error
            return {
                "dashboards": [],
                "metrics": [],
                "visualizations": [],
                "datasources": []
            }
    
    def _prepare_content(self, content: str, max_chars: int = 500000) -> str:
        """
        Prepare content for Gemini - sample if too large.
        
        Args:
            content: Full file content
            max_chars: Maximum characters to send (Gemini has limits)
        
        Returns:
            Content to send (full or sampled)
        """
        if len(content) <= max_chars:
            return content
        
        logger.info(f"File is large ({len(content)} chars), sampling first {max_chars} chars")
        # Send beginning (usually has structure/headers) + note about truncation
        sampled = content[:max_chars]
        return f"{sampled}\n\n[Note: File truncated for analysis - showing first {max_chars} characters]"
    
    def _build_exploration_prompt(self, content: str, platform: str) -> str:
        """Build structured prompt for component discovery."""
        return f"""Analyze this {platform.upper()} metadata file and discover all components.

Return a JSON object with this EXACT structure (no markdown, just JSON):
{{
    "dashboards": [
        {{"id": "unique_id", "name": "dashboard_name", "platform": "{platform}"}}
    ],
    "metrics": [
        {{"id": "unique_id", "name": "metric_name", "platform": "{platform}"}}
    ],
    "visualizations": [
        {{"id": "unique_id", "name": "viz_name", "type": "chart_type", "platform": "{platform}"}}
    ],
    "datasources": [
        {{"id": "unique_id", "name": "ds_name", "type": "connection_type", "platform": "{platform}"}}
    ]
}}

Important:
- Extract ALL components you find
- Use meaningful IDs (can be name-based or sequential)
- For visualizations, identify chart type (bar_chart, line_chart, pie_chart, table, etc.)
- For datasources, identify connection type (sql_server, postgresql, excel, etc.)
- Return empty arrays [] if no components of that type found

File Content:
{content}
"""
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from Gemini response (might be wrapped in markdown)."""
        text = text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```
        
        if text.endswith("```"):
            text = text[:-3]  # Remove closing ```
        
        return text.strip()
    
    async def create_file_splitting_strategy(
        self,
        structure_info: Dict[str, Any],
        platform: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Call Gemini to create intelligent file splitting strategy.
        
        Args:
            structure_info: Structure metadata from analyzer
            platform: BI platform name
            file_path: Path to file (for logging)
        
        Returns:
            Dict with splitting strategy
        """
        logger.info(f"Creating splitting strategy for {platform} file: {file_path}")
        
        # Build prompt with structure info (not full file)
        prompt = self._build_strategy_prompt(structure_info, platform)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Extract JSON from response
            result_text = self._extract_json(result_text)
            strategy = json.loads(result_text)
            
            logger.info(f"Successfully created splitting strategy")
            return strategy
            
        except Exception as e:
            logger.error(f"Error creating strategy: {e}")
            # Return default strategy
            return self._create_default_strategy(structure_info)
    
    def _build_strategy_prompt(self, structure_info: Dict[str, Any], platform: str) -> str:
        """Build prompt for strategy creation."""
        file_size_mb = structure_info['file_size_bytes'] / 1024 / 1024
        
        return f"""Analyze this {platform.upper()} file structure and create an intelligent splitting strategy.

File Information:
- Size: {structure_info['file_size_bytes']:,} bytes ({file_size_mb:.2f} MB)
- Type: {structure_info['file_type']}
- Platform: {structure_info['platform']}

Structure Discovered:
- Root elements: {structure_info['root_elements']}
- Element counts: {structure_info['element_counts']}
- Element hierarchy: {structure_info['element_hierarchy']}
- Estimated sections: {structure_info['estimated_sections']}

Sample Content (first 20KB showing structure):
{structure_info['sample_content'][:20000]}

Create a splitting strategy that:
1. Splits by logical XML elements (datasources, worksheets, dashboards, etc.)
2. Keeps chunks under 500KB for efficient Gemini processing
3. Preserves context between chunks (e.g., datasource info needed for worksheets)
4. Prioritizes important sections (datasources, worksheets first)
5. Maintains relationships between components

Return a JSON object with this structure:
{{
    "split_method": "element_based",
    "chunks": [
        {{
            "chunk_id": "chunk_1",
            "target_elements": ["datasources"],
            "priority": "high",
            "max_size_bytes": 500000,
            "context_needed": []
        }},
        {{
            "chunk_id": "chunk_2",
            "target_elements": ["worksheets"],
            "priority": "high",
            "max_size_bytes": 500000,
            "context_needed": ["datasources"],
            "split_by": "individual"
        }}
    ],
    "processing_order": ["chunk_1", "chunk_2"],
    "context_preservation": {{
        "global_context": ["workbook_metadata"],
        "chunk_dependencies": {{
            "chunk_2": ["chunk_1"]
        }}
    }}
}}

Return ONLY valid JSON, no markdown formatting.
"""
    
    def _create_default_strategy(self, structure_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a default strategy if LLM fails."""
        logger.warning("Using default splitting strategy")
        
        # Create simple strategy based on root elements
        chunks = []
        processing_order = []
        
        root_elements = structure_info.get("root_elements", [])
        if not root_elements:
            root_elements = list(structure_info.get("element_counts", {}).keys())[:5]
        
        for i, elem in enumerate(root_elements[:5], 1):  # Limit to 5 chunks
            chunk_id = f"chunk_{i}"
            chunks.append({
                "chunk_id": chunk_id,
                "target_elements": [elem],
                "priority": "high" if elem in ['datasources', 'worksheets'] else "medium",
                "max_size_bytes": 500000,
                "context_needed": []
            })
            processing_order.append(chunk_id)
        
        return {
            "split_method": "element_based",
            "chunks": chunks,
            "processing_order": processing_order,
            "context_preservation": {
                "global_context": [],
                "chunk_dependencies": {}
            }
        }
    
    # Keep other methods for future agents
    async def extract_complexity_details(
        self, 
        components: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract complexity-relevant details from components.
        
        FUTURE LLM IMPLEMENTATION:
        - Call Gemini API to analyze each component
        - Extract formulas, structure, dependencies
        - Return parsed details
        
        Currently returns dummy data.
        """
        logger.info("Extracting complexity details from components")
        # TODO: Implement real Gemini API call
        return {
            "metrics": [],
            "dashboards": [],
            "visualizations": [],
            "datasources": []
        }
    
    async def analyze_calculations(self, metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze calculation/metric complexity.
        
        FUTURE LLM IMPLEMENTATION:
        - Call Gemini API to analyze formula complexity
        - Identify functions, dependencies, complexity scores
        - Return analysis results
        
        Currently returns dummy data.
        """
        logger.info(f"Analyzing {len(metrics)} calculations")
        # TODO: Implement real Gemini API call
        return []
    
    async def analyze_visualizations(
        self, 
        visualizations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze visualization complexity.
        
        FUTURE LLM IMPLEMENTATION:
        - Call Gemini API to analyze chart types, data complexity
        - Return analysis results
        
        Currently returns dummy data.
        """
        logger.info(f"Analyzing {len(visualizations)} visualizations")
        # TODO: Implement real Gemini API call
        return []
    
    async def analyze_dashboards(
        self, 
        dashboards: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze dashboard structure and complexity.
        
        FUTURE LLM IMPLEMENTATION:
        - Call Gemini API to analyze dashboard structure, filters, interactions
        - Return analysis results
        
        Currently returns dummy data.
        """
        logger.info(f"Analyzing {len(dashboards)} dashboards")
        # TODO: Implement real Gemini API call
        return []
    
    async def analyze_datasources(
        self, 
        datasources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze data source compatibility and complexity.
        
        FUTURE LLM IMPLEMENTATION:
        - Call Gemini API to analyze compatibility, join complexity
        - Return analysis results
        
        Currently returns dummy data.
        """
        logger.info(f"Analyzing {len(datasources)} datasources")
        # TODO: Implement real Gemini API call
        return []
    
    async def generate_recommendations(
        self, 
        analyses: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generate migration recommendations and strategy.
        
        FUTURE LLM IMPLEMENTATION:
        - Call Gemini API with all analyses
        - Generate executive summary, consolidation opportunities, recommendations
        - Return final report
        
        Currently returns dummy data.
        """
        logger.info("Generating recommendations from analyses")
        # TODO: Implement real Gemini API call
        return {}


# Global service instance
llm_service = LLMService()
