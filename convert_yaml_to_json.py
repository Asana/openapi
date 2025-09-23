#!/usr/bin/env python3
"""
Convert YAML OpenAPI specification to JSON format.
"""

import json
import yaml
import os
from pathlib import Path


def convert_yaml_to_json():
    """Convert asana_oas.yaml to asana_oas.json."""
    script_dir = Path(__file__).parent
    yaml_file = script_dir / "defs" / "asana_oas.yaml"
    json_file = script_dir / "defs" / "asana_oas.json"

    if not yaml_file.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")

    # Load YAML file
    with open(yaml_file, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)

    # Write JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(yaml_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully converted {yaml_file} to {json_file}")


if __name__ == "__main__":
    convert_yaml_to_json()