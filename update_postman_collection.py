#!/usr/bin/env python3
"""
Updates existing Postman Collection with the JSON file via Postman API.

Prerequisites:
- Existing Postman collection .json file in defs directory
- POSTMAN_API_KEY env variable
- POSTMAN_COLLECTION_ID env variable (API key must have write access to that collection)
- POSTMAN_COLLECTION_FILE env variable
"""

from pathlib import Path
import requests
import json
import os
import sys

def upload_to_postman():
    """Update Postman Collection via Postman API."""
    
    # Get required environment variables
    api_key = os.getenv('POSTMAN_API_KEY')
    collection_id = os.getenv('POSTMAN_COLLECTION_ID')
    collection_file = os.getenv('POSTMAN_COLLECTION_FILE')

    if not all([api_key, collection_id, collection_file]):
        print("❌ Missing required environment variables:")
        print(f"   POSTMAN_API_KEY: {'✅' if api_key else '❌'}")
        print(f"   POSTMAN_COLLECTION_ID: {'✅' if collection_id else '❌'}")
        print(f"   POSTMAN_COLLECTION_FILE: {'✅' if collection_file else '❌'}")
        sys.exit(1)
    
    # Locate collection file
    file_path = Path(collection_file)
    
    if not file_path.exists():
        print(f"❌ Collection file not found: {file_path}")
        sys.exit(1)
    
    # Load collection from file
    try:
        with open(file_path, 'r') as f:
            collection = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {collection_file}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to read {collection_file}: {e}")
        sys.exit(1)
    
    # Upload to Postman
    print("Updating collection...")
    try:
        response = requests.put(
            f'https://api.getpostman.com/collections/{collection_id}',
            headers={'X-Api-Key': api_key},
            json={'collection': collection}
        )
        response.raise_for_status()
        
        print("✅ Successfully updated collection")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ API error ({response.status_code}): {response.text}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    upload_to_postman()