import os
import re
import ruamel.yaml

ASANA_OAS_DIR = './defs/asana_oas.yaml'
LANGUAGES = ['java', 'node', 'python', 'php', 'ruby']

# ReadMe code configurations
readme_code_config = {
    'java': {
        # TODO: Dynamically pull the latest java-asana package version number
        # NOTE: this FoldedScalarString method adds this line as a YAML block scalar style so in the future when ReadMe supports '\n' in their install we can go back and add it in here
        # Context: more info on YAML Multiline: https://yaml-multiline.info/
        'install': ruamel.yaml.scalarstring.FoldedScalarString('<dependency><groupId>com.asana</groupId><artifactId>asana</artifactId><version>1.0.0</version></dependency>'),
    },
    'node': {
        'install': 'npm install asana',
    },
    'python': {
        'install': 'pip install asana',
    },
    'php': {
        'install': 'composer require asana/asana',
    },
    'ruby': {
        'install': 'gem install asana',
    }
}

# Let ruamel.yaml know that we don't want to use aliases/anchors in the output YAML file
ruamel.yaml.representer.RoundTripRepresenter.ignore_aliases = lambda x, y: True

yaml = ruamel.yaml.YAML()
# Configure ruamel.yaml to preserve OpenAPI Spec file formatting
yaml.preserve_quotes = True
yaml.indent(sequence=4, offset=2)

# Helper function to convert snakecase to camel case
def camel_case(s):
    # Split underscore using split
    temp = s.split('_')
    # Joining result
    return temp[0] + ''.join(word.title() for word in temp[1:])

# Gather sample code
print('Gathering sample code')
code_samples = {}
for language in LANGUAGES:
    # Add sample code for current client libraries
    for dirpath,_,filenames in os.walk(f'./build/{language}/samples'):
        for filename in filenames:
            with open(f'{dirpath}/{filename}') as fp:
                data = yaml.load(fp)
                for resource, operations in data.items():
                    # Set resource key in code_samples dict
                    # NOTE: java resource name has a "base" suffix. We'll need to remove this so we
                    # can group the sample code together with the other languages
                    resource_name = resource.replace("base", '') if language == 'java' else resource
                    code_samples.setdefault(resource_name, {})
                    # Loop through each operation
                    for operation, code_sample in operations.items():
                        # Convert operation name from snake case to camel case
                        operation_name_camel_case = camel_case(operation)
                        # Set operation name
                        code_samples[resource_name].setdefault(operation_name_camel_case, [])
                        # Add sample code
                        code_samples[resource_name][operation_name_camel_case].append(
                            {
                                "language": language,
                                "install": readme_code_config[language]['install'],
                                "code": code_sample
                            }
                        )
    # Add sample code for preview client libraries
    if language in {"node", "python"}:
        for dirpath,_,filenames in os.walk(f'./build/{language}-preview/docs'):
            for filename in filenames:
                if re.search("^.*Api.yaml$", filename):
                    with open(f'{dirpath}/{filename}') as fp:
                        data = yaml.load(fp)
                        for resource, operations in data.items():
                            # OpenAPI Generator adds "Api" suffix to end of resource names we need
                            # to remove it so we can find a matching resource in our OpenAPI Spec
                            resource_name = resource.replace("Api", '').lower()
                            # Set resource key in code_samples dict
                            code_samples.setdefault(resource_name, {})
                            # Loop through each operation
                            for operation, code_sample in operations.items():
                                # Convert operation name from snake case to camel case
                                # NOTE: the python generator snake cases all opertionIDs we need to
                                # change this to camel case so we can find a matching resource in our OpenAPI Spec
                                operation_name_camel_case = camel_case(operation)
                                # Set operation name
                                code_samples[resource_name].setdefault(operation_name_camel_case, [])
                                # Add sample code
                                code_samples[resource_name][operation_name_camel_case].append(
                                    {
                                        "language": language,
                                        "install": readme_code_config[language]['install'],
                                        "code": code_sample,
                                        "name": f'{language}-preview'
                                    }
                                )

# TODO: Find a more efficient way to inject the sample code
# Load OAS file
with open(ASANA_OAS_DIR) as fp:
    data = yaml.load(fp)

    # Add code samples to each enpoint in the OAS
    for resource, operations in code_samples.items():
        print(f'Adding code samples to {resource}')
        for operation in operations:
            for endpoint, endpoint_data in data['paths'].items():
                for method, method_data in endpoint_data.items():
                    if method in ['delete', 'get', 'post', 'put']:
                        if method_data['operationId'] == operation:
                            modified_data = data['paths'][endpoint][method]
                            modified_data.setdefault('x-readme', {})
                            modified_data['x-readme'].setdefault('code-samples', [])
                            modified_data['x-readme']['code-samples'] = code_samples[resource][operation]

# Update OpenAPI Spec file with injected code samples
with open(ASANA_OAS_DIR, 'w') as fp:
    yaml.dump(data, fp)
