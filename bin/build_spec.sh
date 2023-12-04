#! /bin/bash -e

# Build the OpenAPI Spec
make build_spec

# Clone client libraries
mkdir -p build
checkout_client_lib() (
	url="$1"
	dest="$2"

	if [[ -d "$dest" ]]; then
		cd $dest
		echo "Getting latest changes for $dest"
		git checkout master
		git pull
        return
	fi

	git clone "$url" "$dest"
)

checkout_version_client_lib() (
	url="$1"
	dest="$2"
	tag="$3"

	if [[ -d "$dest" ]]; then
		cd $dest
		echo "Getting version $tag for $dest"
		git checkout $tag
        return
	fi

	git clone "$url" "$dest"
	cd $dest
	git checkout $tag
)

checkout_client_lib "https://github.com/Asana/java-asana.git" build/java
checkout_client_lib "https://github.com/Asana/node-asana.git" build/node
checkout_client_lib "https://github.com/Asana/python-asana.git" build/python
checkout_client_lib "https://github.com/Asana/php-asana.git" build/php
checkout_client_lib "https://github.com/Asana/ruby-asana.git" build/ruby

# Beta Client Libraries
checkout_version_client_lib "https://github.com/Asana/node-asana.git" build/node-sdk-v1 v1.0.2
checkout_version_client_lib "https://github.com/Asana/python-asana.git" build/python-sdk-v3 v3.2.2

# Run script to add client library sample code to OpenAPI Spec file
python add_code_samples_to_oas.py
