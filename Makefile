setup:
ifndef OPENAPI_DIR
	$(error OPENAPI_DIR is not set. Please see https://app.asana.com/0/0/1200652548580470/f before running)
endif
	cd $$OPENAPI_DIR && pip install -r requirements.txt

build_spec:
ifndef OPENAPI_DIR
	$(error OPENAPI_DIR is not set. Please see https://app.asana.com/0/0/1200652548580470/f before running)
endif
	python $$OPENAPI_DIR/build.py && cp $$OPENAPI_DIR/dist/asana_oas_docs.yaml ./defs/asana_oas.yaml && cp $$OPENAPI_DIR/app_components_oas.yaml ./defs/app_components_oas.yaml && cp $$OPENAPI_DIR/dist/asana_oas_sdk.yaml ./defs/asana_sdk_oas.yaml
