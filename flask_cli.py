import argparse
import importlib
import json
import logging
import os
import sys
from typing import List, Optional, Tuple

import flask
from flask.testing import FlaskClient

# Allow import from current working directory modules
sys.path.append(os.getcwd())


# Constants
CLI_VERSION = "0.0.1"

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"]

FLASK_MODULE_PATH_ENV_VAR = "PD_FLASK_UTILS_APP_PATH"

DEFAULT_FLASK_APP_PATH = "main.app"

FLASK_APP_IMPORT_PATH = os.environ.get(
        FLASK_MODULE_PATH_ENV_VAR, DEFAULT_FLASK_APP_PATH
    )


# Functions
def load_json(json_payload: str) -> Optional[dict]:
    """
    Load either json string or file
    :param json_payload:
    :return:
    """

    if json_payload is None:
        return None

    if isinstance(json_payload, dict):
        return json_payload

    if os.path.isfile(json_payload):
        with open(json_payload, "r") as f:
            return json.load(f)
    else:
        return json.loads(json_payload)


def import_main_flask_app() -> flask.app:
    """
    Import a python module with a Flask App.
    Finds the import path based on an env variable "PD_FLASK_UTILS_APP_PATH", defaults to "main.app"
    :return: a Flask.app Object
    """
    flask_app_import_path_list = FLASK_APP_IMPORT_PATH.split(".")

    flask_module_name = ".".join(flask_app_import_path_list[0:-1])
    flask_app_name = flask_app_import_path_list[-1]

    # Import main module with flask App, disable INFO logging during import to skip flask initialization messages
    logging.disable(logging.INFO)
    main_flask = importlib.import_module(flask_module_name)
    logging.disable(logging.NOTSET)
    return getattr(main_flask, flask_app_name)


def load_flask_app_url_map(flask_app: flask.app) -> List[str]:
    """
    Retrieve list of endpoints registered in a Flask App
    :param flask_app: a flask.app Object
    :return: list of endpoints registered on the Flask App
    """
    links = []
    for rule in flask_app.url_map.iter_rules():
        # exclude API doc endpoints like swagger ui and openapi spec
        if not any([rule.rule.startswith("/apidoc"), rule.rule.startswith("/static")]):
            links.append(rule.rule)
    return links


def mock_flask_request(
    flask_app: flask.app, http_method: str, endpoint: str, payload: Optional[dict]
) -> Tuple[int, str]:
    """
    Make a mock request via the test client of a given Flask App
    :param flask_app: Flask App
    :param http_method: HTTP Method to use as uppercase string (eg. GET, POST, etc.)
    :param endpoint: endpoint of Flask App to call
    :param payload: Dict to include as json body
    :return: Tuple of mock HTTP Response Status Code and Data
    """
    assert http_method in HTTP_METHODS

    client: FlaskClient = flask_app.test_client()

    if http_method == "GET":
        resp = client.get(endpoint)
    elif http_method == "POST":
        resp = client.post(endpoint, json=payload)
    elif http_method == "PUT":
        resp = client.put(endpoint, json=payload)
    elif http_method == "DELETE":
        resp = client.delete(endpoint, json=payload)
    else:
        return 500, "Method not supported by CLI"

    return int(resp.status_code), resp.data.decode("utf-8")


def main():

    # Attempt import flask app Object and load in endpoints of flask app
    try:
        flask_app: flask.app = import_main_flask_app()
        ENDPOINTS = load_flask_app_url_map(flask_app)
    except Exception as e:
        flask_app = None
        ENDPOINTS = []
        flask_app_import_error = e

    # Setup CLI
    flask_cli = argparse.ArgumentParser(
        description=f"""
        CLI wrapper around a Flask App.
        Attempts importing a flask app with current working directory as root.
        Uses import path specified in env variable {FLASK_MODULE_PATH_ENV_VAR},
        with format of "module.flask-app" (default set to "{DEFAULT_FLASK_APP_PATH}")
        """
    )
    flask_cli.add_argument(
        "--endpoint", type=str, help="Endpoint to call", default="/", choices=ENDPOINTS
    )
    flask_cli.add_argument(
        "--http-method",
        type=str,
        default="POST",
        help="HTTP Method to mock when calling a given endpoint",
        choices=HTTP_METHODS,
    )
    flask_cli.add_argument(
        "--json",
        type=str,
        help="JSON formatted input to include in payload of request, or path to a JSON file",
    )
    flask_cli.version = CLI_VERSION
    flask_cli.add_argument("--version", action="version")

    # Parse inputs
    args = flask_cli.parse_args()
    endpoint: str = args.endpoint
    http_method: str = args.http_method
    json_payload: str = args.json

    payload: Optional[dict] = load_json(json_payload)

    # Raise error if failed to import flask app
    if not flask_app:
        error_prefix = "ERROR: "
        print(f"{error_prefix}{flask_app_import_error}")
        print(
            f"{error_prefix}Attempt to import flask app from {FLASK_APP_IMPORT_PATH} failed."
        )
        print(f"{error_prefix}Attempts import with current working directory as root.")
        print(
            f"{error_prefix}Can set a different import path via env variable {FLASK_MODULE_PATH_ENV_VAR} (ex. export {FLASK_MODULE_PATH_ENV_VAR}=moduleA.moduleB.myapp)"
        )
        sys.exit(flask_app_import_error)

    # Use flask test client to make mock request
    status_code, resp_content = mock_flask_request(
        flask_app=flask_app, http_method=http_method, endpoint=endpoint, payload=payload
    )

    # Exit with response status code and content
    exit_value = 1
    print("\n", "-" * 100)
    if 200 <= status_code < 300:
        print(
            f"Finished successfully with mock status code {status_code}\n{resp_content}"
        )
        exit_value = 0
    else:
        print(
            f"Endpoint command failed with mock status code {status_code}\n{resp_content}"
        )
        exit_value = resp_content

    return sys.exit(exit_value)


if __name__ == "__main__":
    main()
