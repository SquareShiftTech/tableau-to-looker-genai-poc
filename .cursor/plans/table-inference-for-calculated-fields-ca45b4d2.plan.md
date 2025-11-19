<!-- ca45b4d2-8aef-46e4-9443-7f5559ec79c8 363c04b7-f2ce-4688-b64b-7a4591141a4d -->
# Migrate to Vertex AI Only

## Changes Required

### 1. Update Dependencies (`pyproject.toml`)

- Replace `google-generativeai>=0.3.0` with `google-genai>=0.2.0`
- Remove API key dependency

### 2. Update Configuration (`workflow/config.py`)

- Remove `GEMINI_API_KEY` configuration
- Add Vertex AI configuration:
- `VERTEX_AI_PROJECT` (from env `GOOGLE_CLOUD_PROJECT` or config)
- `VERTEX_AI_LOCATION` (default: "global")
- Update `GEMINI_MODEL` to "gemini-2.5-flash" (Vertex AI model name)

### 3. Rewrite Gemini Client (`workflow/gemini_client.py`)

- Remove all `google-generativeai` imports and API key logic
- Use `from google import genai` and `from google.genai import types`
- Initialize client with `genai.Client(vertexai=True, project=..., location=...)`
- Update `generate()` method to use `client.models.generate_content()`
- Update `generate_with_file()` to:
- Read local JSON files as bytes
- Use `types.Part.from_data(data=file_bytes, mime_type=mime_type)`
- Pass parts in `contents` parameter
- Remove file upload/cleanup logic (not needed with Vertex AI)

### 4. Update Documentation (`workflow/README.md`)

- Remove API key setup instructions
- Add Vertex AI setup instructions:
- Enable Vertex AI API
- Service account setup
- Set `GOOGLE_CLOUD_PROJECT` environment variable
- Authentication via `GOOGLE_APPLICATION_CREDENTIALS`

## Implementation Details

**File handling**: Local JSON files will be read as bytes and passed using `types.Part.from_data()` since we're not using GCS URIs.

**Generation config**: Use `types.GenerationConfig()` for temperature, top_p, top_k, max_output_tokens.

**Error handling**: Maintain existing error handling patterns but update error messages for Vertex AI context.

### To-dos

- [ ] Create tableau_parser/extractors/table_inference.py with recursive table resolution logic
- [ ] Add enrich_chunk_with_table_inference() function to examples/usage.py and call it after creating field chunks
- [ ] Update fields_prompt.txt section 3 (CALCULATED FIELDS) to use inferred_table and ref_tables from enriched chunks
- [ ] Update CALCS output format in fields_prompt.txt to include table and ref_tables
- [ ] Replace calculated field example in fields_prompt.txt with new format showing inferred_table
- [ ] Add TableInferenceExtractor to tableau_parser/extractors/__init__.py exports
- [ ] Update pyproject.toml: replace google-generativeai with google-genai
- [ ] Update workflow/config.py: remove GEMINI_API_KEY, add VERTEX_AI_PROJECT and VERTEX_AI_LOCATION
- [ ] Rewrite workflow/gemini_client.py: use google-genai with Vertex AI pattern, handle local files with from_data()
- [ ] Update workflow/README.md: remove API key instructions, add Vertex AI setup guide