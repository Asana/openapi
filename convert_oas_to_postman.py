#!/usr/bin/env python3
"""
Convert Open API Spec to Postman Collection

Converts OpenAPI 3.0 specification to Postman Collection v2.1.0 format,
handling request/response bodies, parameters, and tag-based organization.

[Internal Asanas] Learn more: https://app.asana.com/0/0/1211836466365216/f

Prerequisites:
- Open API Specification JSON file in ./defs directory
- POSTMAN_COLLECTION_FILE env variable (if used inside of a GitHub Action)
"""
import json
import os
import re
import yaml
from http import HTTPStatus
from pathlib import Path

# ===== Constants =====

ASANA_DEV_DOCS_BASE_URL = "https://developers.asana.com"

# ===== Global mutable state =====

POSTMAN_COLLECTION = {}
OAS = {}

# ===== Entrypoint =====

def convert_oas_to_postman():
    """Convert Open API Spec to Postman Collection"""
    global OAS

    defs_dir = Path(__file__).parent / 'defs'
    oas_file = defs_dir / os.getenv('OAS_FILE', 'asana_oas.yaml')
    output_file = defs_dir / os.getenv('POSTMAN_COLLECTION_FILE', 'asana_postman_collection.json')
    postman_description_file = defs_dir / 'postman_description.md'

    # Load collection's description or set to None if file isn't found.
    # This will result in loading the OAS description as a fallback
    postman_description = None
    if os.path.exists(postman_description_file):
        with open(postman_description_file, 'r', encoding='utf-8') as f:
            postman_description = f.read()

    with open(oas_file, 'r', encoding='utf-8') as f:
        OAS = yaml.safe_load(f)

    # Build collection pieces
    _build_postman_info(OAS.get('info', {}), postman_description)
    servers = OAS.get('servers') or [{}]
    _build_postman_variables(servers[0])
    _build_postman_auth()
    _build_postman_groups(OAS.get('tags', []))
    _build_postman_items(OAS.get('paths', {}))
    _build_dev_docs_urls()

    # Persist collection
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

def _build_postman_variables(server):
    """Build collection variables for base URL and authentication"""
    POSTMAN_COLLECTION['variable'] = [
        {'key': 'baseUrl', 'value': server.get('url')},
        {'key': 'bearerToken', 'value': ''},
        { 'key': 'oauthAppId', 'value': '' },
        { 'key': 'oauthSecret', 'value': '' },
        { 'key': 'oauthScopes', 'value': 'default' }
    ]

def _build_postman_auth():
    """Build collection-level authentication (OAuth2 configuration used by default)"""
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
    """Build request items from OAS paths and endpoints"""
    for path, path_obj in paths.items():
        # Collect path-level parameters (shared across all endpoints)
        path_level_params = _extract_parameters(path_obj.get('parameters', []))
        
        for method, endpoint in path_obj.items():
            if method not in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                continue
            
            # Merge path-level and operation-level parameters
            endpoint_params = _extract_parameters(endpoint.get('parameters', []))
            all_params = {
                'path': path_level_params['path'] + endpoint_params['path'],
                'query': path_level_params['query'] + endpoint_params['query']
            }

            request_body = endpoint.get('requestBody')
            responses = endpoint.get('responses', {})

            request_body_schema = _resolve_all_refs(request_body) if request_body else None
            response_body_schema = None
            if responses:
                # take first response value (successful)
                first_response = next(iter(responses.values()))
                response_body_schema = _resolve_all_refs(first_response) if first_response else None

            request_body_table = _get_table_from_schema(request_body_schema, False) if request_body_schema else ''
            response_body_table = _get_table_from_schema(response_body_schema, True) if response_body_schema else ''

            description_parts = [endpoint.get('description', '')]
            if request_body_table:
                description_parts.extend(['## Request Body:', request_body_table])
            if response_body_table:
                description_parts.extend(['## Response Body:', response_body_table])

            item = {
                'name': endpoint.get('summary', f'{method.upper()} {path}'),
                'request': {
                    'method': method.upper(),
                    'url': {
                        'host': ['{{baseUrl}}'],
                        'path': _resolve_request_path(path),
                        'variable': all_params['path'],
                        'query': all_params['query']
                    },
                    'body': _resolve_request_body(request_body),
                    'description': {
                        'content': '\n\n'.join([
                                endpoint.get('description', ''), 
                                '## Request Body:',
                                request_body_table,
                                '## Response Body:',
                                response_body_table
                            ]).strip(),
                        'type': 'text/markdown'
                    }
                },
                'response': _resolve_responses(responses, method.upper(), path, all_params)
            }

            tags = endpoint.get('tags', ['Others'])
            for tag in tags:
                _add_item_to_folder(item, tag)

def _resolve_request_path(path):
    """Convert OAS path format to Postman format ({param} -> :param)"""
    # [1:] to omit the first empty string from split
    return path.replace('{', ':').replace('}', '').split('/')[1:]

def _add_item_to_folder(item, tag_name):
    """Add request item to the appropriate tag folder (first matching folder)"""
    for folder in POSTMAN_COLLECTION.get('item', []):
        if folder.get('name') == tag_name:
            folder['item'].append(item)
            break

# ===== Parameter Resolvers =====

def _extract_parameters(params):
    """Extract and categorize parameters into path and query lists (Postman format)"""
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

def _resolve_param(param):
    """Resolve parameter reference if needed"""
    if isinstance(param, dict) and '$ref' in param:
        return _resolve_ref(param['$ref'])
    if isinstance(param, str):
        return _resolve_ref(param)
    return param

def _build_postman_param(param_obj):
    """Build Postman parameter object from OAS parameter"""
    schema = param_obj.get('schema', {}) if param_obj else {}
    example = param_obj.get('example', '') if param_obj else ''

    # Convert array examples to comma-separated string; otherwise stringified example
    if isinstance(example, list):
        value = ','.join(map(str, example))
    else:
        value = str(example) if example != '' else ''

    return {
        'key': param_obj.get('name'),
        'value': value,
        'type': schema.get('type'),
        'disabled': not param_obj.get('required', False),
        'description': {'content': param_obj.get('description', ''), 'type': 'text/markdown'}
    }

# ===== Request Body Resolvers =====

def _resolve_request_body(request_body):
    """Convert OAS request body to Postman body format"""
    if not request_body:
        return None
    
    content = request_body.get('content', {})
    if not content:
        return None

    content_type = next(iter(content.keys()), None)
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
    if 'enum' in field_schema:
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

    for status_code, response_schema in (oas_responses or {}).items():
        # If the response is a $ref, resolve it
        if '$ref' in response_schema:
            response_schema = _resolve_ref(response_schema['$ref'])

        content = response_schema.get('content', {}) if response_schema else {}
        response_body = None
        content_type = None

        if content:
            content_type = next(iter(content.keys()))
            schema = content[content_type].get('schema', {})
            resolved_schema = _resolve_all_refs(schema)
            response_body = _build_example_from_schema(resolved_schema, ignore_readonly=False)

        headers = [{'key': 'Content-Type', 'value': content_type}] if content_type else []

        # Resolve HTTP status phrase
        try:
            status_text = HTTPStatus(int(status_code)).phrase
        except Exception:
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
                'value': 'Bearer <token>'
            }
        ],
        'body': {}
    }

# ===== Schema Processing & Example Builders =====

def _build_example_from_schema(schema, ignore_readonly=False):
    """Recursively build example JSON from schema definition"""
    if not schema:
        return None

    # Resolve all refs first
    schema = _resolve_all_refs(schema)

    # Merge allOf by flattening into a single object result
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
    if schema_type == 'array':
        items_schema = schema.get('items', {})
        return [_build_example_from_schema(items_schema, ignore_readonly)]
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
        obj = obj.get(part)
        if obj is None:
            raise KeyError(f"Reference path not found: {ref_path}")
    return obj

def _resolve_all_refs(obj):
    """Recursively resolve all $ref keys in nested structure"""
    if isinstance(obj, dict):
        if '$ref' in obj:
            return _resolve_all_refs(_resolve_ref(obj['$ref']))
        return {k: _resolve_all_refs(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_all_refs(item) for item in obj]
    return obj

# ===== Postman Collection post-processing =====

def _build_dev_docs_urls():
    """
    Replace relative markdown links with absolute URLs
    and remove whitespace between link elements in all descriptions
    """
    pattern_whitespace = re.compile(r'\]\s+\(')
    pattern_relative_link = re.compile(r'\[([^\]]+)\]\((?<!:)(/[^\)]+)\)')

    def process_value(obj):
        if isinstance(obj, dict):
            # If this looks like a text/markdown block, rewrite markdown links
            if obj.get('type') == 'text/markdown' and 'content' in obj:
                content = obj.get('content') or ''
                if content:
                    content = pattern_whitespace.sub('](', content)
                    content = pattern_relative_link.sub(fr'[\1]({ASANA_DEV_DOCS_BASE_URL}\2)', content)
                    obj['content'] = content
            for value in obj.values():
                process_value(value)
        elif isinstance(obj, list):
            for item in obj:
                process_value(item)

    process_value(POSTMAN_COLLECTION)

# ===== Markdown Table Generation from Schemas =====

def _get_table_from_schema(body_schema, include_readonly=True):
    """Converts request/response body Open API schema to readable Markdown table"""
    if not body_schema or not isinstance(body_schema, dict):
        return ''

    content = body_schema.get('content', {})
    if not content:
        return ''

    content_type = next(iter(content.keys()), '')
    schema = content[content_type].get('schema', {})
    if not schema:
        return ''

    normalized_schema = _normalize_schema(schema)
    required_fields = normalized_schema.get('required', [])
    properties = normalized_schema.get('properties', {})
    if not properties:
        return ''

    lines = [
        '| Field | Type | Enum Values | Description |',
        '|-------|------|-------------|-------------|'
    ]
    lines.extend(_build_field_rows(properties, required_fields, include_readonly))
    return '\n'.join(lines)

def _normalize_schema(schema):
    """Normalize schema by merging allOf, anyOf, oneOf into a single usable schema"""
    if not isinstance(schema, dict):
        return schema

    # Merge allOf entries into a single schema (properties & required fields)
    if 'allOf' in schema:
        merged = {}
        merged_properties = {}
        merged_required = []
        for sub_schema in schema['allOf']:
            normalized_sub = _normalize_schema(sub_schema)
            if isinstance(normalized_sub, dict):
                if 'properties' in normalized_sub:
                    merged_properties.update(normalized_sub['properties'])
                if 'required' in normalized_sub:
                    merged_required.extend(normalized_sub['required'])
                for key, value in normalized_sub.items():
                    if key not in ['properties', 'required', 'allOf']:
                        merged[key] = value
        if merged_properties:
            merged['properties'] = merged_properties
        if merged_required:
            merged['required'] = list(set(merged_required))
        return merged

    # For anyOf/oneOf prefer first schema that defines properties
    if 'anyOf' in schema or 'oneOf' in schema:
        schemas = schema.get('anyOf') or schema.get('oneOf')
        for sub_schema in schemas:
            normalized_sub = _normalize_schema(sub_schema)
            if isinstance(normalized_sub, dict) and 'properties' in normalized_sub:
                return normalized_sub
        return _normalize_schema(schemas[0]) if schemas else schema

    # Recursively normalize nested properties
    if 'properties' in schema:
        normalized_props = {}
        for prop_name, prop_schema in schema['properties'].items():
            normalized_props[prop_name] = _normalize_schema(prop_schema)
        copy = dict(schema)
        copy['properties'] = normalized_props
        return copy

    return schema

def _build_field_rows(properties, required_fields, include_readonly=True, prefix=''):
    """Recursively build table rows for schema properties"""
    rows = []
    for field_name, field_schema in properties.items():
        normalized_field = _normalize_schema(field_schema)

        if not include_readonly and normalized_field.get('readOnly', False):
            continue

        full_name = f'{prefix}{field_name}'
        field_type = _get_field_type(normalized_field)
        enum_values = _get_enum_values(normalized_field)
        description = _clean_description(normalized_field.get('description', ''))

        rows.append(f'| `{full_name}` | {field_type} | {enum_values} | {description} |')

        # Recurse into nested object properties
        if 'properties' in normalized_field:
            nested_required = normalized_field.get('required', [])
            rows.extend(_build_field_rows(
                normalized_field['properties'], 
                nested_required, 
                include_readonly,
                f'{full_name}.'
            ))
        
        # Handle array items with object properties
        if normalized_field.get('type') == 'array' and 'items' in normalized_field:
            items_schema = _normalize_schema(normalized_field['items'])
            
            # If array items have properties (i.e., they're objects), expand them
            if 'properties' in items_schema:
                items_required = items_schema.get('required', [])
                rows.extend(_build_field_rows(
                    items_schema['properties'],
                    items_required,
                    include_readonly,
                    f'{full_name}[].'
                ))
    
    return rows

def _get_field_type(field_schema):
    """Get formatted type string for a field"""
    field_type = field_schema.get('type', 'any')
    
    # If properties exist but no type specified, it's an object
    if field_type == 'any' and 'properties' in field_schema:
        field_type = 'object'

    if field_type == 'array':
        items = field_schema.get('items', {})
        # Normalize items schema to handle allOf/anyOf/oneOf
        normalized_items = _normalize_schema(items)
        item_type = normalized_items.get('type', 'any')
        return f'array[{item_type}]'

    field_format = field_schema.get('format')
    if field_format:
        return f'{field_type}({field_format})'
    return field_type

def _get_enum_values(field_schema):
    """Get formatted enum values string"""
    enum = field_schema.get('enum')
    if not enum:
        return ''
    
    # Format enum values, and add limit if too many
    limit = 10
    if len(enum) <= limit:
        return ', '.join(f'`{option}`' for option in enum)
    shown = ', '.join(f'`{option}`' for option in enum[:limit])
    return f'{shown}, ... (+{len(enum) - limit} more)'

def _clean_description(description):
    """Clean description text for markdown table compatibility"""
    if not description:
        return ''
    
    # Replace newlines with spaces to prevent table breaking
    cleaned = description.replace('\n', ' ')
    
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Escape pipe characters that would break the table
    cleaned = cleaned.replace('|', '\\|')
    return cleaned.strip()

# ===== Entrypoint =====

if __name__ == "__main__":
    convert_oas_to_postman()
