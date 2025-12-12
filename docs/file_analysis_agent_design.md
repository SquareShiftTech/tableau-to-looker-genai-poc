# File Analysis Agent - Recursive Splitting Design

## Problem

Large element files (>500KB) are skipped by Exploration Agent, causing incomplete component discovery.

**Example:**
- `worksheets.xml` (2.7MB) → Exploration Agent skips → No worksheets discovered

## Solution

Recursively split files by XML element levels until all files are ≤ X KB.

**Approach:**
1. Extract first-level elements → Save each to separate file
2. For each file: IF size > X KB → Split by next-level XML elements
3. Recursively check and split until all files ≤ X KB
4. No structure analysis, no metadata extraction - just file splitting

## Design

### Flow

```
1. Get first-level XML elements (datasources, worksheets, dashboards)
   → Save each to {element_name}.xml

2. For each file:
   ├─ Check file size
   │
   ├─ IF size ≤ X KB:
   │   └─ Keep as-is, add to output list
   │
   └─ IF size > X KB:
       ├─ Parse XML to find child elements (next level)
       ├─ Split into {element_name}_{index}.xml (one per child)
       ├─ Remove original file
       └─ Recursively check each new file (go to step 2)

3. Output: List of all final files (all ≤ X KB)
```

### Example Transformation

```
BEFORE:
  worksheets.xml (2.7MB)
    └─ Contains 50 <worksheet> elements

AFTER (Recursive Split):
  worksheet_1.xml (45KB) ✓
  worksheet_2.xml (52KB) ✓
  worksheet_3.xml (38KB) ✓
  ... (50 files, all ≤ 500KB)
```

### Recursive Splitting Logic

**Level 1:** First-level elements
- `worksheets.xml` (2.7MB) → Split by `<worksheet>` children

**Level 2:** If still large, split further
- `worksheet_1.xml` (600KB) → Split by next-level children (if any)

**Stop Condition:**
- File size ≤ X KB, OR
- Single XML element (can't split further)

## Implementation

### 1. New Function: `split_xml_file_recursive()`

**File:** `utils/xml_utils.py`

```python
def split_xml_file_recursive(
    file_path: str,
    output_dir: str,
    size_threshold: int = 500000,
    current_level: int = 0,
    max_levels: int = 10
) -> List[Dict[str, Any]]:
    """
    Recursively split XML file by element levels until all files ≤ size_threshold.
    
    Args:
        file_path: Path to XML file to split
        output_dir: Directory to save split files
        size_threshold: Maximum file size in bytes (default: 500KB)
        current_level: Current recursion level (prevent infinite loops)
        max_levels: Maximum recursion depth
    
    Returns:
        List of file metadata dicts: [{'file_path': '...', 'size_bytes': ...}, ...]
    """
    # 1. Check file size
    # 2. IF size ≤ threshold: Return single file metadata
    # 3. IF size > threshold:
    #    - Parse XML to find child elements
    #    - For each child:
    #      - Extract child XML
    #      - Save to {base_name}_{index}.xml
    #      - Recursively call this function on new file
    #    - Remove original file
    #    - Return list of all split file metadata
```

### 2. Update File Analysis Agent

**File:** `agents/file_analysis_agent.py`

**Changes:**
```python
# After extracting first-level elements
for element_name in element_names:
    # Read and save element
    element_content = read_xml_element(file_path, element_name)
    element_file_path = os.path.join(output_dir, f"{element_name}.xml")
    with open(element_file_path, 'w', encoding='utf-8') as f:
        f.write(element_content)
    
    # Recursively split if needed
    split_files = split_xml_file_recursive(
        element_file_path,
        output_dir,
        size_threshold=settings.chunk_max_size_bytes
    )
    
    parsed_elements_paths.extend(split_files)
```

### 3. Output Structure

**Simple file list (no metadata extraction):**
```python
parsed_elements_paths = [
    {
        'file_path': 'output/job_id/dashboards.xml',
        'size_bytes': 45000
    },
    {
        'file_path': 'output/job_id/worksheet_1.xml',
        'size_bytes': 45000
    },
    {
        'file_path': 'output/job_id/worksheet_2.xml',
        'size_bytes': 52000
    }
    # ... all files ≤ 500KB
]
```

## Edge Cases

1. **Very large single element (>X KB):** Keep as-is, log warning (can't split further)
2. **No child elements:** Keep file, stop recursion
3. **Invalid XML:** Catch exception, keep original file
4. **Empty file:** Skip, don't add to output
5. **Max recursion depth:** Stop splitting, log warning

## Benefits

- **Simple:** Just recursive file splitting, no complex logic
- **Effective:** Guarantees all files ≤ X KB
- **Lightweight:** Minimal code, no metadata extraction
- **Platform agnostic:** Works for any XML structure
- **Agent-friendly:** Downstream agents handle structure discovery

## Configuration

Uses existing `chunk_max_size_bytes` setting (default: 500KB) from `config/settings.py`.
