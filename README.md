# flask-cli-demo
 
Demo of wrapping a Flask App in a CLI to call it's endpoints by mocking HTTP Requests. Includes demos for GCP Python HTTP and PubSub Cloud Functions. Idea is to be able to run a specific Flask App via a command instead of HTTP Request, for example, to move a backend workload deployed as an API to a container.

## Contents
Each python module is a stand alone CLI wrapper (so some code is duplicated). Can bundle together as a single library, just a demo for now.
- [flask_cli.py](flask_cli.py) - wraps a Flask App
- [gcf_http_cli.py](gcf_http_cli.py) - wraps a Python HTTP Cloud Function
- [gcf_pubsub_cli.py](gcf_pubsub_cli.py) - wraps a Python PubSub Cloud Function

## Usage
Attempts importing a flask app or function acting as main entrypoint to a Google Clodu Function with current working directory as root. Uses import path specified in an env variable. For example, PD_FLASK_UTILS_APP_PATH="module.flask-app"

Each file can be called as a CLI and has --help | -h flags for help text.

Examples:
- `python flask_cli.py -h`, `python gcf_pubsub_cli.py --help`, etc.
- `python flask_cli.py --endpoint="/my-route" --http-method=GET`
- `python flask_cli.py --http-method=POST --json="/path_to_payload.json"`
- `python flask_cli.py --endpoint="/my-route" --http-method=POST --json='{"message":"Hello"}'`