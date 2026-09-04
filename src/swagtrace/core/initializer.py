from __future__ import annotations

import json
import shutil
from argparse import _SubParsersAction
from importlib.resources import files
from pathlib import Path
from typing import Any

import httpx
import yaml

from swagtrace.consts import (
    DEFAULT_TEST_MODULE_FOLDER,
    DEFAULT_YAML_FILE,
    PREPARE_AND_FINAL_FORMAT_FILE,
)
from swagtrace.schemas.yaml_schema import (
    ElementInfo,
    SwagTaceTestFormat,
    prepareAndFinal,
)


def fetch_openapi(
    url: str | None, file: str | None, timeout: float = 10.0
) -> dict[str, Any]:
    if file:
        file_json_format_content = {}

        with open(file, "r") as file_object:
            if file.endswith((".yaml", ".yml")):
                file_json_format_content = yaml.safe_load(file_object.read())
            else:
                file_json_format_content = json.load(file_object)
        return file_json_format_content

    else:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "yaml" in content_type or url.endswith((".yaml", ".yml")):
            return yaml.safe_load(response.text)
        return response.json()


def extract_endpoints(spec: dict[str, Any]) -> SwagTaceTestFormat:

    prepare = prepareAndFinal(execute="echo Starting tests ...")
    final = prepareAndFinal(execute="echo test complete")
    info = spec.get("info", {})
    openapi = spec.get("openapi", "")

    tags_map: dict[str, list[dict[str, Any]]] = {}

    paths = spec.get("paths", {})

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "head",
                "options",
            }:
                continue
            if not isinstance(operation, dict):
                continue

            tags = operation.get("tags", [])
            tag = tags[0] if tags else "Default"

            endpoint_info = ElementInfo(
                method=method.upper(),
                path=path,
                operation_id=operation.get("operationId"),
                summary=operation.get("summary"),
                description=operation.get("description"),
                cases=[],
            )

            if tag not in tags_map:
                tags_map[tag] = []

            tags_map[tag].append(endpoint_info)

    return SwagTaceTestFormat(
        openapi=openapi, info=info, prepare=prepare, tags=tags_map, final=final
    )


def save_endpoints_yaml(endpoints: SwagTaceTestFormat, output_path: str) -> None:
    file_name = DEFAULT_YAML_FILE

    output_path = Path(output_path) / Path(file_name)

    endpoints = endpoints.model_dump()
    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            endpoints, f, allow_unicode=True, sort_keys=False, default_flow_style=False
        )


def create_test_module(output_path: str):

    output_path: Path = Path(output_path)
    module_path: Path = output_path / Path(DEFAULT_TEST_MODULE_FOLDER)
    __init__file = module_path / Path("__init__.py")
    prepare_file = module_path / Path("prepare.py")
    final_file = module_path / Path("final.py")

    module_path.mkdir()

    __init__file.touch()
    prepare_file.write_text(PREPARE_AND_FINAL_FORMAT_FILE)
    final_file.write_text(PREPARE_AND_FINAL_FORMAT_FILE)


def init_config_file(output_path: str):
    template_path = Path(files("swagtrace.templates").joinpath("config.toml"))
    target_path = output_path / Path("swagtrace.toml")

    shutil.copy(template_path, target_path)


def discover_and_save(url: str, output: str, file: str | None = None):
    print(f"Fetching OpenAPI from: {url}")
    spec = fetch_openapi(url=url, file=file)

    print("Extracting endpoints...")
    endpoints = extract_endpoints(spec)

    print("Generating yaml file ...")
    save_endpoints_yaml(endpoints, output)

    print("Creating Test Module ...")
    create_test_module(output)

    print("Initializing Config File ...")
    init_config_file(output)


def set_initializer_command(
    subparsers: _SubParsersAction, command: str = "init"
) -> str:
    init_parser = subparsers.add_parser(command, help="initial project")
    init_parser.add_argument(
        "--url",
        type=str,
        help="url for openapi.json file",
        default="http://localhost:8000/openapi.json",
    )
    init_parser.add_argument(
        "--file",
        type=str,
        help="file of openapi. Json or Yaml format file",
        required=False,
    )
    init_parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="output path for files and folders",
        default=".",
    )
    init_parser.set_defaults(func=discover_and_save)

    return command
