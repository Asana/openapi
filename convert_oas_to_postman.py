#!/usr/bin/env python3
"""
Convert Open API Spec to Postman Collection

Converts OpenAPI 3.0 specification to Postman Collection v2.1.0 format,
handling request/response bodies, parameters, and tag-based organization.

Prerequisites:
- Open API Specification JSON file in ./defs directory
- POSTMAN_COLLECTION_FILE env variable (if used inside of a GitHub Action)
"""
import json
import yaml
import os
from pathlib import Path
from http import HTTPStatus
import re

# ===== Global Vars =====

ASANA_DEV_DOCS_BASE_URL = "https://developers.asana.com"
OAS_YAML_FILE = 'asana_oas.yaml'

# ===== Global State =====

POSTMAN_COLLECTION = {}
OAS = {}

# ===== Entrypoint =====

def convert_oas_to_postman():
    """Convert Open API Spec to Postman Collection"""
    global OAS
    
    defs_dir = Path(__file__).parent / 'defs'
    oas_file = defs_dir / OAS_YAML_FILE
    output_file = defs_dir / os.getenv('POSTMAN_COLLECTION_FILE', 'asana_postman_collection.json')
    postman_description_file = defs_dir / 'postman_description.md'
    
    # Load collection's description or set to None if file isn't found.
    # This will result in loading the OAS description as a fallback
    postman_description = None

    if os.path.exists(postman_description_file):
        with open(postman_description_file, 'r') as f:
            postman_description = f.read()

    with open(oas_file, 'r') as f:
        OAS = yaml.safe_load(f)
        
        _build_postman_info(OAS.get('info'), postman_description)
        _build_postman_variables(OAS.get('servers')[0])
        _build_postman_auth()
        _build_postman_groups(OAS.get('tags'))
        _build_postman_items(OAS.get('paths'))
        _build_dev_docs_urls()

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(POSTMAN_COLLECTION, f, indent=2, ensure_ascii=False)

    print("Successfully converted Open API Specification to Postman Collection.")
    print(f"Output file: {output_file}")

# ===== Collection Metadata Builders =====

def _build_postman_info(oas_info, collection_description):
    """Build collection info section from OAS info"""
    POSTMAN_COLLECTION['info'] = {
        'name': oas_info.get('title'),
        'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
        'description': {
            'content': collection_description if collection_description else oas_info.get('description'),
            'type': 'text/markdown'
        }
    }

def _build_postman_variables(base_url):
    """Build collection variables for base URL and authentication"""
    POSTMAN_COLLECTION['variable'] = [
        {'key': 'baseUrl', 'value': base_url.get('url')},
        {'key': 'bearerToken', 'value': ''},
        { 'key': 'oauthAppId', 'value': '' },
        { 'key': 'oauthSecret', 'value': '' },
        { 'key': 'oauthScopes', 'value': 'default' }
    ]

def _build_postman_auth():
    """Build collection-level authentication (Bearer token)"""
    # Postman does not allow defining multiple auth schemas,
    # since OAuth require more complex setup, 
    # we'll use it as a default option.
    # POSTMAN_COLLECTION['auth'] = {
    #     'type': 'bearer',
    #     'bearer': [{
    #         'key': 'token',
    #         'value': '{{bearerToken}}',
    #         'type': 'string'
    #     }]
    # }
    POSTMAN_COLLECTION['auth'] = {
        'type': 'oauth2',
        'oauth2': [
			{ "key": "authRequestParams", "value": [] },
			{ "key": "refreshTokenUrl", "value": "https://app.asana.com/-/oauth_token" },
			{ "key": "state", "value": "{{$randomUUID}}" },
			{ "key": "scope", "value": "{{oauthScopes}}" },
			{ "key": "accessTokenUrl", "value": "https://app.asana.com/-/oauth_token" },
			{ "key": "clientId", "value": "{{oauthAppId}}" },
			{ "key": "clientSecret", "value": "{{oauthSecret}}" },
			{ "key": "authUrl", "value": "https://app.asana.com/-/oauth_authorize" },
			{ "key": "useBrowser", "value": True },
			{ "key": "tokenName", "value": "access_token" },
			{ "key": "addTokenTo", "value": "header" }
        ]
    }

def _build_postman_groups(oas_tags):
    """Build folder structure from OAS tags"""
    POSTMAN_COLLECTION['item'] = [
        {
            'name': tag.get('name'),
            'description': {
                'content': tag.get('description'),
                'type': 'text/markdown'
            },
            'item': []
        }
        for tag in oas_tags
    ]

# ===== Request Item Builders =====

def _build_postman_items(paths):
    """Build request items from OAS paths and operations"""
    for path, path_obj in paths.items():
        # Collect path-level parameters (shared across all operations)
        path_level_params = _extract_parameters(path_obj.get('parameters', []))
        
        for method, operation in path_obj.items():
            if method not in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                continue
            
            # Merge path-level and operation-level parameters
            operation_params = _extract_parameters(operation.get('parameters', []))
            all_params = {
                'path': path_level_params['path'] + operation_params['path'],
                'query': path_level_params['query'] + operation_params['query']
            }

            # Build the request item
            item = {
                'name': operation.get('summary', f'{method.upper()} {path}'),
                'description': {
                    'content': operation.get('description', ''),
                    'type': 'text/markdown'
                },
                'request': {
                    'method': method.upper(),
                    'url': {
                        'host': ['{{baseUrl}}'],
                        'path': _resolve_request_path(path),
                        'variable': all_params['path'],
                        'query': all_params['query']
                    },
                    'body': _resolve_request_body(operation.get('requestBody'))
                },
                'response': _resolve_responses(operation.get('responses', {}), method.upper(), path, all_params)
            }
            
            # Add item to appropriate tag folder(s)
            tags = operation.get('tags', ['Others'])
            for tag in tags:
                _add_item_to_folder(item, tag)

def _extract_parameters(params):
    """Extract and categorize parameters into path and query"""
    path_params = []
    query_params = []
    
    for param in params:
        resolved_param = _resolve_param(param)
        param_obj = _build_postman_param(resolved_param)
        
        if resolved_param.get('in') == 'query':
            query_params.append(param_obj)
        else:
            path_params.append(param_obj)
    
    return {'path': path_params, 'query': query_params}

def _resolve_request_path(path):
    """Convert OAS path format to Postman format ({param} -> :param)"""
    # [1:] to omit the first empty string
    return path.replace('{', ':').replace('}', '').split('/')[1:]

def _add_item_to_folder(item, tag_name):
    """Add request item to the appropriate tag folder"""
    for folder in POSTMAN_COLLECTION.get('item', []):
        if folder.get('name') == tag_name:
            folder['item'].append(item)
            break

# ===== Parameter Resolvers =====

def _resolve_param(param):
    """Resolve parameter reference if needed"""
    if isinstance(param, dict) and '$ref' in param:
        return _resolve_ref(param['$ref'])
    elif isinstance(param, str):
        return _resolve_ref(param)
    return param

def _build_postman_param(param_obj):
    """Build Postman parameter object from OAS parameter"""
    schema = param_obj.get('schema', {})
    example = param_obj.get('example', '')
    
    # Convert array examples to comma-separated string
    value = ','.join(map(str, example)) if isinstance(example, list) else str(example) if example else ''
    
    return {
        'key': param_obj.get('name'),
        'value': value,
        'type': schema.get('type'),
        'disabled': not param_obj.get('required', False),
        'description': {
            'content': param_obj.get('description', ''),
            'type': 'text/markdown'
        }
    }

# ===== Request Body Resolvers =====

def _resolve_request_body(request_body):
    """Convert OAS request body to Postman body format"""
    if not request_body:
        return None
    
    content = request_body.get('content', {})
    if not content:
        return None
    
    content_type = list(content.keys())[0]
    schema = content[content_type].get('schema', {})
    resolved_schema = _resolve_all_refs(schema)
    
    # Map content type to Postman body mode
    mode_map = {
        'application/json': 'raw',
        'multipart/form-data': 'formdata',
        'application/x-www-form-urlencoded': 'urlencoded'
    }
    mode = mode_map.get(content_type, 'raw')
    
    return _build_raw_body(resolved_schema) if mode == 'raw' else _build_form_body(resolved_schema, mode)

def _build_raw_body(schema):
    """Build raw JSON body from schema"""
    example_data = _build_example_from_schema(schema, ignore_readonly=True)
    return {
        'mode': 'raw',
        'raw': json.dumps(example_data, indent=2),
        'options': {'raw': {'language': 'json'}}
    }

def _build_form_body(schema, mode):
    """Build form-data or urlencoded body from schema"""
    form_fields = _build_form_fields(schema)
    return {
        'mode': mode,
        'formdata': form_fields
    } if mode == 'formdata' else {
        'mode': mode,
        'urlencoded': form_fields
    }

def _build_form_fields(schema):
    """Build form field array from schema properties"""
    if not schema or schema.get('type') != 'object':
        return []
    
    properties = schema.get('properties', {})
    required_fields = schema.get('required', [])
    form_fields = []
    
    for field_name, field_schema in properties.items():
        if field_schema.get('format') == 'binary':
            form_fields.append({
                'key': field_name,
                'type': 'file',
                'src': [],
                'description': field_schema.get('description', '')
            })
        else:
            form_fields.append({
                'key': field_name,
                'value': _get_field_example_value(field_schema),
                'type': 'text',
                'disabled': field_name not in required_fields,
                'description': field_schema.get('description', '')
            })
    
    return form_fields

def _get_field_example_value(field_schema):
    """Get example value for a form field"""
    if 'example' in field_schema:
        return str(field_schema['example'])
    elif 'enum' in field_schema:
        return str(field_schema['enum'][0])
    
    type_defaults = {
        'string': '<string>',
        'number': '0',
        'integer': '0',
        'boolean': 'false'
    }
    return type_defaults.get(field_schema.get('type'), '')

# ===== Response Resolvers =====

def _resolve_responses(oas_responses, method, path, params):
    """Convert OAS responses to Postman response examples"""
    responses = []
    
    for status_code, response_schema in oas_responses.items():
        if '$ref' in response_schema:
            response_schema = _resolve_ref(response_schema['$ref'])
        
        # Build response body from schema
        content = response_schema.get('content', {})
        response_body = None
        content_type = None
        
        if content:
            content_type = list(content.keys())[0]
            schema = content[content_type].get('schema', {})
            resolved_schema = _resolve_all_refs(schema)
            response_body = _build_example_from_schema(resolved_schema, ignore_readonly=False)
        
        headers = [{'key': 'Content-Type', 'value': content_type}] if content_type else []
        
        # Get HTTP status text safely
        try:
            status_text = HTTPStatus(int(status_code)).phrase
        except ValueError:
            status_text = 'Unknown'
        
        responses.append({
            'name': f"[{status_code}] {response_schema.get('description', '')}",
            'originalRequest': _build_original_request(method, path, params),
            'code': int(status_code),
            'status': status_text,
            'header': headers,
            'body': json.dumps(response_body, indent=2) if response_body else '',
            '_postman_previewlanguage': 'json' if content_type == 'application/json' else 'text'
        })
    
    return responses

def _build_original_request(method, path, params):
    """Build originalRequest object for response examples"""
    return {
        'method': method,
        'url': {
            'host': ['{{baseUrl}}'],
            'path': _resolve_request_path(path),
            'variable': params.get('path', []),
            'query': params.get('query', [])
        },
        'header': [
            {'key': 'Accept', 'value': 'application/json'},
            {
                'key': 'Authorization',
                'value': 'Bearer <token>',
                'description': {
                    'content': 'Added as a part of security scheme: bearer',
                    'type': 'text/plain'
                }
            }
        ],
        'body': {}
    }

# ===== Schema Processing =====

def _build_example_from_schema(schema, ignore_readonly=False):
    """Recursively build example JSON from schema definition"""
    if not schema:
        return None
    
    # Merge allOf schemas
    if 'allOf' in schema:
        result = {}
        for sub_schema in schema['allOf']:
            sub_result = _build_example_from_schema(sub_schema, ignore_readonly)
            if isinstance(sub_result, dict):
                result.update(sub_result)
        return result
    
    schema_type = schema.get('type')
    
    if schema_type == 'object':
        return _build_object_example(schema, ignore_readonly)
    elif schema_type == 'array':
        items_schema = schema.get('items', {})
        return [_build_example_from_schema(items_schema, ignore_readonly)]
    else:
        return _build_primitive_example(schema)

def _build_object_example(schema, ignore_readonly):
    """Build example for object type schema"""
    properties = schema.get('properties', {})
    result = {}
    
    for prop_name, prop_schema in properties.items():
        if ignore_readonly and prop_schema.get('readOnly', False):
            continue
        result[prop_name] = _build_example_from_schema(prop_schema, ignore_readonly)
    
    return result

def _build_primitive_example(schema):
    """Build example value for primitive types"""
    if 'example' in schema:
        return schema['example']
    elif 'enum' in schema:
        return schema['enum'][0]
    
    type_examples = {
        'string': '<string>',
        'number': 0,
        'integer': 0,
        'boolean': False
    }
    return type_examples.get(schema.get('type'), '<value>')

# ===== Reference Resolution =====

def _resolve_ref(ref_path):
    """Resolve JSON reference pointer (e.g., #/components/schemas/User)"""
    parts = ref_path.replace('#/', '').split('/')
    obj = OAS
    for part in parts:
        obj = obj[part]
    return obj

def _resolve_all_refs(obj):
    """Recursively resolve all $ref keys in nested structure"""
    if isinstance(obj, dict):
        if '$ref' in obj:
            return _resolve_all_refs(_resolve_ref(obj['$ref']))
        return {k: _resolve_all_refs(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_all_refs(item) for item in obj]
    else:
        return obj

# ===== Postman Collection post-processing =====

def _build_dev_docs_urls():
    """
    Replace relative markdown links with absolute URLs 
    and remove whitespace between link elements in all descriptions
    """
    
    def process_value(obj):
        if isinstance(obj, dict):
            # Check if this is a markdown content object and update links
            if obj.get('type') == 'text/markdown' and 'content' in obj:
                content = obj.get('content')
                if content:
                    # Remove whitespaces between ] and ( in markdown links
                    content = re.sub(r'\]\s+\(', r'](', content)
                    
                    # Replace [text](/path) with [text]({{DEV_DOCS_BASE_URL}}/path)
                    content = re.sub(
                        r'\[([^\]]+)\]\((?<!:)(/[^\)]+)\)',
                        fr'[\1]({ASANA_DEV_DOCS_BASE_URL}\2)',
                        content
                    )
                    
                    obj['content'] = content
            # Recursively process all dict values
            for value in obj.values():
                process_value(value)
        elif isinstance(obj, list):
            # Recursively process all list items
            for item in obj:
                process_value(item)
    
    process_value(POSTMAN_COLLECTION)

# ===== Entrypoint =====

if __name__ == "__main__":
    convert_oas_to_postman()