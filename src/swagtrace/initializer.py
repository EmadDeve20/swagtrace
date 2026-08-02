from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
import yaml
from swagtrace.consts import DEFAULT_TEST_MODULE_FOLDER, DEFAULT_YAML_FILE, PREPARE_AND_FINAL_FORMAT_FILE
from swagtrace.yaml_schema import ElementInfo, prepareAndFinal, SwagTaceTestFormat


def fetch_openapi(url: str, timeout: float = 10.0) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout)
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
            if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            if not isinstance(operation, dict):
                continue

            tags = operation.get("tags", [])
            tag = tags[0] if tags else "Default"

            
            endpoint_info = ElementInfo(
                method= method.upper(),
                path= path,
                operation_id= operation.get("operationId"),
                summary= operation.get("summary"),
                description= operation.get("description"),
                cases= []
            )

            if tag not in tags_map:
                tags_map[tag] = []

            tags_map[tag].append(endpoint_info)


    return SwagTaceTestFormat(
        openapi=openapi,
        info=info,
        prepare=prepare,
        tags=tags_map,
        final=final
    )

def save_endpoints_yaml(endpoints: SwagTaceTestFormat, output_path: str) -> None:
    file_name = DEFAULT_YAML_FILE

    output_path = Path(output_path) / Path(file_name)
   
    endpoints  = endpoints.model_dump()
    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(endpoints, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def create_test_module(output_path: str):

    output_path:Path = Path(output_path)
    module_path:Path = output_path / Path(DEFAULT_TEST_MODULE_FOLDER)
    __init__file = module_path / Path("__init__.py")
    prepare_file = module_path / Path("prepare.py")
    final_file = module_path / Path("final.py")

    module_path.mkdir()

    __init__file.touch()
    prepare_file.write_text(PREPARE_AND_FINAL_FORMAT_FILE)
    final_file.write_text(PREPARE_AND_FINAL_FORMAT_FILE)


def discover_and_save(url: str, output: str):
    print(f"Fetching OpenAPI from: {url}")
    spec = fetch_openapi(url)

    print("Extracting endpoints...")
    endpoints = extract_endpoints(spec)

    print("Generating yaml file ...")
    save_endpoints_yaml(endpoints, output)

    print("Creating Test Module ...")
    create_test_module(output)


