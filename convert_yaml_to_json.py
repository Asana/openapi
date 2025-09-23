#!/usr/bin/env python3
"""
Convert YAML OpenAPI specification to JSON format.
"""

import json
import yaml
import os
from pathlib import Path


def convert_yaml_to_json():
    """Convert YAML OpenAPI specifications to JSON format."""
    script_dir = Path(__file__).parent

    # Files to convert
    yaml_files = [
        "asana_oas.yaml",
        "app_components_oas.yaml"
    ]

    for yaml_filename in yaml_files:
        yaml_file = script_dir / "defs" / yaml_filename
        json_filename = yaml_filename.replace('.yaml', '.json')
        json_file = script_dir / "defs" / json_filename

        if not yaml_file.exists():
            print(f"Warning: YAML file not found: {yaml_file}")
            continue

        # Load YAML file
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)

        # Write JSON file
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(yaml_data, f, indent=2, ensure_ascii=False)

        print(f"Successfully converted {yaml_file} to {json_file}")


if __name__ == "__main__":
    convert_yaml_to_json()