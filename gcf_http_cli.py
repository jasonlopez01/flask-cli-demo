import argparse
import importlib
import json
import os
import sys
from typing import Callable, Optional, Tuple

import flask

# Allow import from current working directory modules
sys.path.append(os.getcwd())


# Constants
CLI_VERSION = "0.0.1"

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"]

GCF_MODULE_PATH_ENV_VAR = "PD_FLASK_UTILS_GCF_PATH"

DEFAULT_GCF_MAIN_PATH = "main.main"


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


def import_main_gcf_entrypoint() -> Callable:
    """
    Import the main function entrypoint from a python module deployed as a Cloud Function
    Finds the import path based on an env variable "PD_FLASK_UTILS_GCF_PATH", defaults to "main.main"
    :return: a function acting as the main entrypoint for a python Cloud Function
    """
    gcf_main_import_path = os.environ.get(
        GCF_MODULE_PATH_ENV_VAR, DEFAULT_GCF_MAIN_PATH
    )
    gcf_main_import_path_list = gcf_main_import_path.split(".")

    main_module_name = ".".join(gcf_main_import_path_list[0:-1])
    gcf_main_name = gcf_main_import_path_list[-1]

    # Import main module with GCF entrypoint function
    main_gcf = importlib.import_module(main_module_name)
    return getattr(main_gcf, gcf_main_name)


def mock_gcf_flask_request(
    gcf_main_func: Callable, http_method: str, endpoint: str, payload: Optional[dict]
) -> Tuple[int, str]:
    """
    Make a mock request to an entrypoint function of a HTTP Triggered Cloud Function via the flask test client
    :param gcf_main_func: a function acting as the main entrypoint for a python Cloud Function (HTTP Trigger)
    :param http_method: HTTP Method to use as uppercase string (eg. GET, POST, etc.)
    :param endpoint: endpoint of Flask App to call
    :param payload: Dict to include as json body
    :return: Tuple of mock HTTP Response Status Code and Data
    """
    assert http_method in HTTP_METHODS

    test_app = flask.Flask(__name__)

    with test_app.test_request_context(endpoint, method=http_method, json=payload):
        resp = gcf_main_func(flask.request)

    return int(resp.status_code), resp.data.decode("utf-8")


def main():

    # Import main function entrypoint
    try:
        gcf_entrypoint: Callable = import_main_gcf_entrypoint()
    except Exception as e:
        gcf_import_error = e
        gcf_entrypoint = None

    # Setup CLI
    gcf_cli = argparse.ArgumentParser(
        description=f"""
        CLI wrapper around a Python function acting as the entrypoint to a Cloud Function (HTTP Trigger).
        Attempts importing a the function with current working directory as root.
        Uses import path specified in env variable {GCF_MODULE_PATH_ENV_VAR},
        with format of "module.function" (default set to "{DEFAULT_GCF_MAIN_PATH}")
        """
    )
    gcf_cli.add_argument(
        "--http-method",
        type=str,
        default="POST",
        help="HTTP Method to mock when calling a given endpoint",
        choices=HTTP_METHODS,
    )
    gcf_cli.add_argument(
        "--json",
        type=str,
        help="JSON formatted input to include in payload of request, or path to a JSON file",
    )
    gcf_cli.add_argument(
        "--endpoint", type=str, help="Endpoint to call, defaults to '/'", default="/"
    )
    gcf_cli.version = CLI_VERSION
    gcf_cli.add_argument("--version", action="version")

    # Parse inputs
    args = gcf_cli.parse_args()
    endpoint: str = args.endpoint
    http_method: str = args.http_method
    json_payload: str = args.json

    payload: Optional[dict] = load_json(json_payload)

    if not gcf_entrypoint:
        error_prefix = "ERROR: "
        print(f"{error_prefix}{gcf_import_error}")
        print(
            f"{error_prefix}Attempt to import gcf entrypoint function from {GCF_MAIN_IMPORT_PATH} failed."
        )
        print(f"{error_prefix}Attempts import with current working directory as root.")
        print(
            f"{error_prefix}Can set a different import path via env variable {GCF_MODULE_PATH_ENV_VAR} (ex. export {GCF_MODULE_PATH_ENV_VAR}=moduleA.my_gcf_main_func)"
        )
        sys.exit(gcf_import_error)


    # Use flask test client to make mock request
    status_code, resp_content = mock_gcf_flask_request(
        gcf_main_func=gcf_entrypoint,
        http_method=http_method,
        endpoint=endpoint,
        payload=payload,
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
