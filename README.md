# Asana's OpenAPI Specifications

This repository contains the [OpenAPI Specification](https://swagger.io/specification/) for Asana's APIs.

To learn more about Asana's APIs, [visit our developer documentation](https://developers.asana.com/docs).

# Setup

Install dependencies:

```
make setup
```

# Usage

To build (i.e., update) the OpenAPI specifications for the REST API (`./defs/asana_oas.yaml`) and for app components (`./defs/app_components_oas.yaml`), create a new branch and run the following:

```
make build_spec
```

Then, create a pull request with the new specifications.

