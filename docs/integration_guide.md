# Integration Guide: Complexity Analysis Agent with XML to Dict Agent

## Overview

There are two ways to integrate the Complexity Analysis Agent with the XML to Dict Agent workflow:

1. **Unified Workflow** (Recommended) - Sequential workflow that chains both agents
2. **Extended Ingestion Agent** - Add complexity tools directly to ingestion agent

## Approach 1: Unified Workflow (Recommended)

### File: `evaluations/unified_tableau_workflow.py`

This creates a sequential workflow:
```
Ingestion Agent → Complexity Analysis Agent → End
```

### Usage:

```bash
# Run full workflow (ingestion + complexity analysis)
python evaluations/unified_tableau_workflow.py

# Skip ingestion (assume data already loaded)
python evaluations/unified_tableau_workflow.py --skip-ingestion

# Run only complexity analysis
python evaluations/unified_tableau_workflow.py --complexity-only

# Fresh start (truncate tables first)
python evaluations/unified_tableau_workflow.py --fresh
```

### Benefits:
- Clear separation of concerns
- Can run complexity analysis independently
- Easy to add more agents in the future
- State management is explicit

## Approach 2: Extended Ingestion Agent

### Modified: `evaluations/xml_to_dict_agent.py`

The ingestion agent can now optionally include complexity analysis tools.

### Usage:

```bash
# Run ingestion with complexity analysis
python evaluations/xml_to_dict_agent.py --complexity

# Fresh start with complexity analysis
python evaluations/xml_to_dict_agent.py --fresh --complexity
```

### Benefits:
- Single agent handles everything
- LLM decides when to run complexity analysis
- Simpler for basic use cases

## Workflow Comparison

### Unified Workflow Structure:
```
┌─────────────────┐
│  Ingestion      │
│  Agent          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Complexity     │
│  Analysis       │
│  Agent          │
└────────┬────────┘
         │
         ▼
        END
```

### Extended Agent Structure:
```
┌─────────────────────────────┐
│  Ingestion Agent            │
│  (with complexity tools)    │
│                             │
│  Tools:                     │
│  - initialize_database      │
│  - convert_and_store_files  │
│  - ingest_to_tables         │
│  - analyze_*_complexity     │
└─────────────┬───────────────┘
              │
              ▼
             END
```

## Recommendation

**Use Unified Workflow** for:
- Production deployments
- When you need to run complexity analysis independently
- When you want clear separation between ingestion and analysis

**Use Extended Agent** for:
- Quick prototyping
- When you want the LLM to decide when to analyze
- Simpler command-line interface

## Example Output

Both approaches generate the same output:
- `evaluations/complexity_analysis_results.json` with per-instance complexity data

## Next Steps

1. Test with sample data
2. Add more analysis agents (e.g., datasource compatibility)
3. Generate HTML report from complexity results
