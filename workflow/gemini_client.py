"""Gemini 2.5 Flash client wrapper for generating DSL and LookML using Vertex AI."""

import os
from pathlib import Path
from typing import Optional
from .config import VERTEX_AI_PROJECT, VERTEX_AI_LOCATION, GEMINI_MODEL


class GeminiClient:
    """Wrapper for Gemini API calls via Vertex AI."""
    
    def __init__(
        self, 
        project: Optional[str] = None,
        location: Optional[str] = None,
        model: Optional[str] = None
    ):
        from google import genai
        
        project_id = project or VERTEX_AI_PROJECT or os.getenv("GOOGLE_CLOUD_PROJECT")
        location_str = location or VERTEX_AI_LOCATION or "global"
        self.model_name = model or GEMINI_MODEL
        
        if not project_id:
            raise ValueError(
                "VERTEX_AI_PROJECT or GOOGLE_CLOUD_PROJECT environment variable must be set"
            )
        
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location_str,
        )
    
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Generate text using Gemini.
        
        Args:
            prompt: The prompt text
            system_instruction: Optional system instruction for the model
            
        Returns:
            Generated text
        """
        try:
            from google.genai import types
            
            generation_config = types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
            
            contents = [prompt]
            if system_instruction:
                # For Vertex AI, system instruction might need to be passed differently
                # Check if the API supports system_instruction parameter
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=generation_config,
                    system_instruction=system_instruction
                )
            else:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=generation_config
                )
            
            return response.text.strip()
        
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def generate_with_file(self, prompt: str, file_path: str, mime_type: str = "application/json") -> str:
        """
        Generate text using Gemini with file content included in the prompt.
        
        Args:
            prompt: The prompt text
            file_path: Path to file to include in prompt
            mime_type: MIME type of the file (used for formatting, not attachment)
            
        Returns:
            Generated text
        """
        try:
            from google.genai import types
            import json
            
            # Read file content
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read file as text
            file_content = file_path_obj.read_text(encoding='utf-8')
            
            # Format file content based on type
            if mime_type == "application/json":
                try:
                    # Pretty-print JSON for better readability
                    json_data = json.loads(file_content)
                    formatted_content = json.dumps(json_data, indent=2, ensure_ascii=False)
                    file_section = f"\n\n## File Content (JSON):\n```json\n{formatted_content}\n```"
                except json.JSONDecodeError:
                    # If not valid JSON, include as-is
                    file_section = f"\n\n## File Content:\n```\n{file_content}\n```"
            else:
                # For other file types, include as code block
                file_section = f"\n\n## File Content:\n```\n{file_content}\n```"
            
            # Combine prompt with file content
            full_prompt = prompt + file_section
            
            generation_config = types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[full_prompt],
                config=generation_config
            )
            
            return response.text.strip()
        
        except Exception as e:
            raise Exception(f"Gemini API error with file: {str(e)}")
