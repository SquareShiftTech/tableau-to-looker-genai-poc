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
    
    def _prepare_content(self, content: str, max_chars: Optional[int] = None) -> str:
        """
        Prepare content for Gemini - sample if too large.
        
        Args:
            content: Full file content
            max_chars: Maximum characters to send (default: from settings.chunk_max_size_bytes)
        
        Returns:
            Content to send (full or sampled)
        """
        if max_chars is None:
            max_chars = self.settings.chunk_max_size_bytes
        
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
    
    async def analyze_components_with_strategy(
        self,
        strategy: Dict[str, Any],
        file_path: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Agent-driven component discovery using file splitting strategy.
        
        Gives the strategy to Gemini and lets it use tools to discover components.
        Agent decides how to use the strategy and combines results intelligently.
        
        Args:
            strategy: File splitting strategy from File Analysis Agent
            file_path: Path to the file
            platform: BI platform name
            
        Returns:
            Dict with discovered components (combined from all chunks)
        """
        logger.info(f"Analyzing components with strategy for {platform} file: {file_path}")
        
        # Build prompt that gives strategy to agent
        try:
            prompt = self._build_strategy_based_prompt(strategy, file_path, platform)
        except Exception as e:
            logger.error(f"Error building prompt: {e}", exc_info=True)
            raise
        
        try:
            logger.info("Calling Gemini API...")
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                logger.error("Gemini returned empty response")
                raise ValueError("Empty response from Gemini")
            
            result_text = response.text
            logger.info(f"Received response from Gemini: {len(result_text):,} characters")
            logger.debug(f"Gemini response (first 500 chars): {result_text[:500]}")
            
            # Extract JSON from response
            result_text = self._extract_json(result_text)
            logger.debug(f"Extracted JSON (first 500 chars): {result_text[:500]}")
            
            discovered_components = json.loads(result_text)
            
            # Log what was discovered
            dashboards = discovered_components.get('dashboards', [])
            metrics = discovered_components.get('metrics', [])
            visualizations = discovered_components.get('visualizations', [])
            datasources = discovered_components.get('datasources', [])
            
            logger.info(f"Successfully discovered components using strategy:")
            logger.info(f"  - Dashboards: {len(dashboards)}")
            logger.info(f"  - Metrics: {len(metrics)}")
            logger.info(f"  - Visualizations: {len(visualizations)}")
            logger.info(f"  - Data Sources: {len(datasources)}")
            
            # Warn if all empty
            total = len(dashboards) + len(metrics) + len(visualizations) + len(datasources)
            if total == 0:
                logger.warning("⚠️  WARNING: All component arrays are empty! This may indicate:")
                logger.warning("   1. Chunks were not read correctly (wrong element names)")
                logger.warning("   2. Gemini couldn't parse the XML content")
                logger.warning("   3. Context window was exceeded (content truncated)")
                logger.warning("   4. XML structure doesn't match expected format")
            
            return discovered_components
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            logger.error(f"Response text (first 1000 chars): {result_text[:1000] if 'result_text' in locals() else 'N/A'}")
            raise
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Error calling Gemini with strategy: {error_type}: {error_msg}")
            logger.error(f"Full error traceback:", exc_info=True)
            
            # Check if it's a context window error
            if 'token' in error_msg.lower() or 'context' in error_msg.lower() or 'limit' in error_msg.lower():
                logger.error("⚠️  CONTEXT WINDOW ERROR DETECTED - Strategy needs refinement!")
            
            # Re-raise instead of returning empty - let caller handle it
            raise
    
    async def extract_components_from_element(
        self,
        element_name: str,
        element_content: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Extract components from a single element file.
        
        Args:
            element_name: Name of the element (e.g., "dashboards", "worksheets", "datasources")
            element_content: Full XML content of the element (no truncation)
            platform: BI platform name
            
        Returns:
            Dict with extracted components and relationship IDs:
            {
                "dashboards": [...],  // If element is dashboards
                "worksheets": [...],  // If element is worksheets
                "datasources": [...], // If element is datasources
                "filters": [...],     // If element contains filters
                "parameters": [...],  // If element contains parameters
                "calculations": [...] // If element contains calculations
            }
        """
        logger.info(f"Extracting components from {element_name} element ({len(element_content):,} chars)")
        
        # Build generic discovery prompt
        prompt = self._build_element_extraction_prompt(element_name, element_content, platform)
        
        try:
            logger.info(f"Calling Gemini to extract components from {element_name}...")
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                logger.error(f"Gemini returned empty response for {element_name}")
                return {}
            
            result_text = response.text
            logger.info(f"Received response from Gemini for {element_name}: {len(result_text):,} characters")
            
            # Extract JSON from response
            result_text = self._extract_json(result_text)
            components = json.loads(result_text)
            
            # Count extracted components
            total_components = sum(
                len(v) if isinstance(v, list) else 0 
                for v in components.values()
            )
            logger.info(f"Extracted {total_components} components from {element_name}")
            
            return components
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response for {element_name}: {e}")
            logger.error(f"Response text (first 1000 chars): {result_text[:1000] if 'result_text' in locals() else 'N/A'}")
            return {}  # Return empty dict on error, don't fail entire process
        except Exception as e:
            logger.error(f"Error extracting components from {element_name}: {e}", exc_info=True)
            return {}  # Return empty dict on error, don't fail entire process
    
    def _build_element_extraction_prompt(
        self,
        element_name: str,
        element_content: str,
        platform: str
    ) -> str:
        """
        Build generic prompt for component discovery.
        
        This is a simple discovery prompt - it asks the LLM to identify components
        (id, name) and their relationships. Detailed extraction happens in Parsing Agent.
        
        Args:
            element_name: Name of the element (e.g., "dashboards", "worksheets")
            element_content: XML content of the element
            platform: BI platform name
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are analyzing {platform.upper()} workbook XML to discover components and their relationships.

You have been provided with the {element_name.upper()} element from the workbook:

{element_content}

Your task is to DISCOVER what components exist in this element and identify their relationships.

For each component you find, extract:
- id (unique identifier)
- name
- relationships (list of IDs/names of other components this references)

Component types you might find:
- dashboards
- worksheets  
- datasources
- filters
- parameters
- calculations

IMPORTANT: 
- Let the XML structure guide you - discover what's actually there
- Focus on relationships - which components reference which other components
- Keep it simple - just id, name, and relationship IDs
- Don't extract detailed properties (formulas, connection strings, etc.) - that's for later

Return valid JSON only (no markdown formatting). Use this structure:

{{
    "dashboards": [
        {{"id": "...", "name": "...", "worksheets": [...], "filters": [...], "parameters": [...]}}
    ],
    "worksheets": [
        {{"id": "...", "name": "...", "datasources": [...], "calculations": [...], "filters": [...]}}
    ],
    "datasources": [
        {{"id": "...", "name": "...", "calculations": [...]}}
    ],
    "filters": [
        {{"id": "...", "name": "...", "related_dashboards": [...], "related_worksheets": [...]}}
    ],
    "parameters": [
        {{"id": "...", "name": "...", "related_dashboards": [...]}}
    ],
    "calculations": [
        {{"id": "...", "name": "...", "related_worksheets": [...], "related_datasources": [...]}}
    ]
}}

Only include component types that actually exist in this element. Omit empty arrays.
"""
        
        return prompt
    
    async def extract_component_catalog(
        self,
        element_contents: Dict[str, str],
        platform: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Extract component catalog by processing each element separately.
        
        This method processes each element file sequentially with individual LLM calls,
        then merges all results into a single component catalog.
        
        Args:
            element_contents: Dict mapping element_name -> XML content (e.g., {"datasources": "<datasources>...</datasources>"})
            platform: BI platform name (tableau, power_bi, etc.)
            output_dir: Output directory path (for logging)
            
        Returns:
            Dict with component catalog structure:
            {
                "dashboards": [...],
                "worksheets": [...],
                "datasources": [...],
                "filters": [...],
                "parameters": [...],
                "calculations": [...]
            }
        """
        logger.info(f"Extracting component catalog from {len(element_contents)} element files for {platform}")
        
        # Initialize merged catalog
        merged_catalog = {
            "dashboards": [],
            "worksheets": [],
            "datasources": [],
            "filters": [],
            "parameters": [],
            "calculations": []
        }
        
        # Process each element sequentially
        for element_name, element_content in element_contents.items():
            logger.info(f"Processing element: {element_name}")
            
            try:
                result = await self.extract_components_from_element(
                    element_name, element_content, platform
                )
                
                # Merge results into catalog
                for component_type in merged_catalog.keys():
                    if component_type in result and isinstance(result[component_type], list):
                        merged_catalog[component_type].extend(result[component_type])
                        logger.info(f"  Added {len(result[component_type])} {component_type} from {element_name}")
                
            except Exception as e:
                logger.error(f"Error processing element {element_name}: {e}", exc_info=True)
                # Continue with other elements even if one fails
                continue
        
        # Log summary
        dashboards = merged_catalog.get('dashboards', [])
        worksheets = merged_catalog.get('worksheets', [])
        datasources = merged_catalog.get('datasources', [])
        filters = merged_catalog.get('filters', [])
        parameters = merged_catalog.get('parameters', [])
        calculations = merged_catalog.get('calculations', [])
        
        logger.info(f"Successfully extracted component catalog:")
        logger.info(f"  - Dashboards: {len(dashboards)}")
        logger.info(f"  - Worksheets: {len(worksheets)}")
        logger.info(f"  - Data Sources: {len(datasources)}")
        logger.info(f"  - Filters: {len(filters)}")
        logger.info(f"  - Parameters: {len(parameters)}")
        logger.info(f"  - Calculations: {len(calculations)}")
        
        return merged_catalog
    
    def _build_strategy_based_prompt(
        self,
        strategy: Dict[str, Any],
        file_path: str,
        platform: str
    ) -> str:
        """Build prompt for agent-driven exploration with strategy."""
        from utils.xml_utils import read_xml_element
        
        # Get processing order and chunks
        processing_order = strategy.get('processing_order', [])
        chunks = {chunk['chunk_id']: chunk for chunk in strategy.get('chunks', [])}
        
        logger.info(f"Building prompt with {len(processing_order)} chunks in processing order")
        
        # Read all chunks using simple tool (we do the reading, agent does reasoning)
        chunk_contents = {}
        chunk_sizes = {}
        
        for chunk_id in processing_order:
            chunk = chunks.get(chunk_id)
            if not chunk:
                logger.warning(f"Chunk {chunk_id} not found in chunks dictionary")
                continue
            
            target_elements = chunk.get('target_elements', [])
            logger.info(f"Processing chunk '{chunk_id}': target_elements={target_elements}")
            
            chunk_xml_parts = []
            
            # Read each target element
            for element_name in target_elements:
                logger.debug(f"  Reading element: {element_name}")
                element_content = read_xml_element(file_path, element_name)
                
                if element_content:
                    element_size = len(element_content)
                    logger.info(f"  ✓ Found '{element_name}': {element_size:,} characters")
                    chunk_xml_parts.append(f"<!-- {element_name} elements -->\n{element_content}")
                else:
                    logger.warning(f"  ✗ No content found for element '{element_name}'")
                    logger.warning(f"    This element may not exist in the XML file!")
            
            # Also read context elements if needed
            context_needed = chunk.get('context_needed', [])
            if context_needed:
                logger.info(f"  Reading context from: {context_needed}")
            
            for context_chunk_id in context_needed:
                context_chunk = chunks.get(context_chunk_id)
                if context_chunk:
                    for context_element in context_chunk.get('target_elements', []):
                        logger.debug(f"  Reading context element: {context_element}")
                        context_content = read_xml_element(file_path, context_element)
                        if context_content:
                            context_size = len(context_content)
                            logger.info(f"  ✓ Context '{context_element}': {context_size:,} characters")
                            chunk_xml_parts.append(f"<!-- Context: {context_element} from {context_chunk_id} -->\n{context_content}")
                        else:
                            logger.warning(f"  ✗ No context content for '{context_element}'")
            
            if chunk_xml_parts:
                chunk_content = '\n\n'.join(chunk_xml_parts)
                chunk_size = len(chunk_content)
                chunk_contents[chunk_id] = chunk_content
                chunk_sizes[chunk_id] = chunk_size
                
                max_size = chunk.get('max_size_bytes', self.settings.chunk_max_size_bytes)
                logger.info(f"Chunk '{chunk_id}' total size: {chunk_size:,} bytes (max: {max_size:,})")
                
                if chunk_size > max_size:
                    logger.warning(f"⚠️  WARNING: Chunk '{chunk_id}' exceeds max_size_bytes!")
                    logger.warning(f"    Actual: {chunk_size:,} bytes, Max: {max_size:,} bytes")
                    logger.warning(f"    This may cause context window errors!")
            else:
                logger.warning(f"⚠️  WARNING: Chunk '{chunk_id}' has NO content!")
                logger.warning(f"    This will result in empty component discovery!")
                chunk_contents[chunk_id] = '<!-- No content found -->'
        
        # Log summary
        total_size = sum(chunk_sizes.values())
        logger.info(f"Total chunk content size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
        
        # Build prompt with all chunk contents
        chunks_info = []
        for chunk_id in processing_order:
            chunk = chunks.get(chunk_id)
            if not chunk:
                continue
            chunks_info.append(f"""
=== Chunk: {chunk_id} ===
Target Elements: {chunk.get('target_elements', [])}
Priority: {chunk.get('priority', 'medium')}
Context Needed: {chunk.get('context_needed', [])}

XML Content:
{chunk_contents.get(chunk_id, '<!-- No content found -->')}
""")
        
        prompt = f"""You are analyzing a {platform.upper()} metadata file to discover all components.

You have a file splitting strategy that breaks the file into manageable chunks. The chunks have already been extracted for you.

File: {file_path}
Strategy Method: {strategy.get('split_method', 'element_based')}
Processing Order: {processing_order}

Chunks with XML Content:
{''.join(chunks_info)}

Instructions:
1. Analyze each chunk's XML content to discover components
2. Combine all results intelligently:
   - Remove duplicates (check by ID or name)
   - Maintain relationships between components (e.g., worksheets use datasources)
   - Ensure complete coverage of all components from all chunks
3. Process chunks in order, but combine results into a single catalog

Important:
- Each component should have: id, name, platform, and type-specific fields
- For visualizations, identify chart type (bar_chart, line_chart, pie_chart, table, etc.)
- For datasources, identify connection type (sql_server, postgresql, excel, etc.)
- Maintain relationships (e.g., which worksheets use which datasources)

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

Analyze all chunks and return the complete combined result.
"""
        
        prompt_size = len(prompt)
        logger.info(f"Built prompt: {prompt_size:,} characters ({prompt_size/1024/1024:.2f} MB)")
        if prompt_size > 1000000:  # 1MB
            logger.warning(f"⚠️  Prompt is very large ({prompt_size:,} chars), may exceed context window")
        
        return prompt
    
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
2. Keeps chunks under {self.settings.chunk_max_size_bytes:,} bytes ({self.settings.chunk_max_size_bytes/1024:.1f}KB) for efficient Gemini processing
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
            "max_size_bytes": {self.settings.chunk_max_size_bytes},
            "context_needed": []
        }},
        {{
            "chunk_id": "chunk_2",
            "target_elements": ["worksheets"],
            "priority": "high",
            "max_size_bytes": {self.settings.chunk_max_size_bytes},
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
                "max_size_bytes": self.settings.chunk_max_size_bytes,
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
    
    async def refine_file_splitting_strategy(
        self,
        structure_info: Dict[str, Any],
        platform: str,
        file_path: str,
        previous_strategy: Dict[str, Any],
        refinement_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refine strategy based on feedback from exploration agent.
        
        Args:
            structure_info: Structure metadata from analyzer
            platform: BI platform name
            file_path: Path to file (for logging)
            previous_strategy: The strategy that failed
            refinement_feedback: Feedback about what went wrong
            
        Returns:
            Dict with refined splitting strategy
        """
        logger.info(f"Refining splitting strategy for {platform} file: {file_path}")
        logger.info(f"Refinement reason: {refinement_feedback.get('reason')}")
        
        # Build prompt explaining what went wrong and asking for more granular strategy
        prompt = self._build_refinement_prompt(
            structure_info, platform, previous_strategy, refinement_feedback
        )
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Extract JSON from response
            result_text = self._extract_json(result_text)
            strategy = json.loads(result_text)
            
            logger.info(f"Successfully refined splitting strategy")
            logger.info(f"Refined strategy has {len(strategy.get('chunks', []))} chunks")
            return strategy
            
        except Exception as e:
            logger.error(f"Error refining strategy: {e}")
            # Return more granular default strategy
            return self._create_refined_default_strategy(structure_info, refinement_feedback)
    
    def _build_refinement_prompt(
        self,
        structure_info: Dict[str, Any],
        platform: str,
        previous_strategy: Dict[str, Any],
        refinement_feedback: Dict[str, Any]
    ) -> str:
        """Build prompt for strategy refinement."""
        file_size_mb = structure_info['file_size_bytes'] / 1024 / 1024
        
        return f"""The previous splitting strategy failed. You need to create a MORE GRANULAR strategy.

Previous Strategy Failure:
{json.dumps(refinement_feedback, indent=2)}

Previous Strategy (that failed):
{json.dumps(previous_strategy, indent=2)}

File Information:
- Size: {structure_info['file_size_bytes']:,} bytes ({file_size_mb:.2f} MB)
- Type: {structure_info['file_type']}
- Platform: {structure_info['platform']}

File Structure:
- Root elements: {structure_info['root_elements']}
- Element counts: {json.dumps(structure_info['element_counts'], indent=2)}
- Element hierarchy: {json.dumps(structure_info['element_hierarchy'], indent=2)}

CRITICAL: Use EXACT element names from element_counts above. Do NOT assume element names like 'worksheets' - check what actually exists in the file.

Create a MORE GRANULAR strategy that:
1. Splits problematic chunks into smaller pieces
2. Uses 'split_by: individual_child_element' for large chunks (e.g., split each worksheet/dashboard individually)
3. Ensures each chunk is under {self.settings.chunk_max_size_bytes:,} bytes ({self.settings.chunk_max_size_bytes/1024:.1f}KB) (max_size_bytes: {self.settings.chunk_max_size_bytes})
4. Uses EXACT element names from element_counts (not assumptions)
5. Maintains context relationships between chunks
6. Prioritizes important sections first

Return a JSON object with this structure:
{{
    "split_method": "element_based",
    "chunks": [
        {{
            "chunk_id": "chunk_1",
            "target_elements": ["exact_element_name_from_file"],
            "priority": "high",
            "max_size_bytes": {self.settings.chunk_max_size_bytes},
            "context_needed": [],
            "split_by": "individual_child_element"
        }}
    ],
    "processing_order": ["chunk_1", "chunk_2"],
    "context_preservation": {{
        "global_context": [],
        "chunk_dependencies": {{}}
    }}
}}

Return ONLY valid JSON, no markdown formatting.
"""
    
    def _create_refined_default_strategy(
        self,
        structure_info: Dict[str, Any],
        refinement_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a more granular default strategy when refinement fails."""
        logger.warning("Using refined default splitting strategy")
        
        # Get actual element names from structure
        element_counts = structure_info.get("element_counts", {})
        
        # Find key elements (prioritize those that likely contain components)
        key_elements = []
        for elem, count in element_counts.items():
            if count > 0 and elem in ['datasources', 'datasource', 'windows', 'window', 'dashboards', 'dashboard']:
                key_elements.append(elem)
        
        # If no key elements found, use top elements by count
        if not key_elements:
            sorted_elements = sorted(element_counts.items(), key=lambda x: x[1], reverse=True)
            key_elements = [elem for elem, count in sorted_elements[:5] if count > 0]
        
        chunks = []
        processing_order = []
        
        for i, elem in enumerate(key_elements[:10], 1):  # Limit to 10 chunks for granularity
            chunk_id = f"refined_chunk_{i}"
            chunks.append({
                "chunk_id": chunk_id,
                "target_elements": [elem],
                "priority": "high" if elem in ['datasources', 'datasource', 'windows', 'window'] else "medium",
                "max_size_bytes": self.settings.chunk_max_size_bytes,
                "context_needed": [],
                "split_by": "individual_child_element" if elem in ['windows', 'dashboards'] else "section_group"
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
