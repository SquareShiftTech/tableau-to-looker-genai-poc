"""Load and validate complexity rules from JSON configuration."""
import json
from pathlib import Path
from typing import Dict, Any, Optional


def load_complexity_rules(platform: str = "tableau") -> Dict[str, Any]:
    """
    Load complexity rules for the given platform.
    
    Args:
        platform: BI platform name (tableau, power_bi, cognos, microstrategy)
    
    Returns:
        Complexity rules dict for the platform, or empty dict if not found
    """
    rules_path = Path(__file__).parent / "complexity_rules.json"
    if not rules_path.exists():
        return {}
    
    with open(rules_path, 'r', encoding='utf-8') as f:
        full_rules = json.load(f)
    
    return full_rules.get(platform, {})
