# Asana's OpenAPI Specifications

This repository contains the [OpenAPI Specification](https://swagger.io/specification/) for Asana's APIs.

To learn more about Asana's APIs, [visit our developer documentation](https://developers.asana.com/docs). You may also directly view API references for:

* [Asana's REST API](https://developers.asana.com/reference/rest-api-reference)
* [App components](https://developers.asana.com/reference/ac-api-reference)

# Setup

1. Clone this repository to your local machine. 

2. Navigate to project's root directory via your terminal, then install dependencies:

```
make setup
```

# Usage

To build (i.e., update) the OpenAPI specifications for the REST API (`./defs/asana_oas.yaml`) and for app components (`./defs/app_components_oas.yaml`), create a new branch and run the following:

```
./bin/build_spec.sh
```

_Note for internal Asanas: If you see errors regarding `OPENAPI_DIR` not being set, see this task: [https://app.asana.com/0/0/1200652548580470/f](https://app.asana.com/0/0/1200652548580470/f)_

The script may take a few moments to fully run. When complete, create a pull request in this repository with the result.
