from typing import Any

from types import ModuleType

import requests
import sys
import subprocess
import importlib.util

from pathlib import Path

from yaml_syntax.syntax import YamlSyntax

from swagtrace.yaml_schema import ElementInfo, prepareAndFinal, SwagTaceTestFormat
from swagtrace.utils import set_variables_in_data


GLOBAL_VARIABLES = {}

def load_module(module_path: str):
    path = Path(module_path)
    
    if not path.exists():
        print(f"❌ File Does not exist!: {module_path}")
        return
    
    module_name = path.stem
    
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    return module
    


def run_func_module(module:ModuleType, func:str, verbose:bool=False, *args, **kwargs):
    if hasattr(module, func):
        if verbose:
            print(f"▶ Running {func} function: {module}")
        getattr(module, func)(*args, **kwargs)
    else:
        print(f"⚠ {func} Function Does not exist in {func} file!")


def load_variables_module(module:ModuleType, var_name: str = "VARIABLES") -> dict[str, Any]:

    if hasattr(module, var_name):
        variables = getattr(module, var_name)
        return variables
    else:
        return {}


def project_banner_information(openapi:str, info: dict):

    print(f"OpenAPI: {openapi}")

    for k, v in info.items():
        print(f"{k}: {v}")


def prepare_tests(prepare:prepareAndFinal, file:str, verbose:bool):
    global GLOBAL_VARIABLES
 
    module = load_module(module_path=file)

    run_func_module(module=module, func="prepare", verbose=verbose)

    GLOBAL_VARIABLES = load_variables_module(module=module)

    result = subprocess.run(prepare.execute, shell=True, text=True, capture_output=True)

    print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())
        raise RuntimeError(f"Failed on prepare section test: {result.stderr.strip()}")

    run_func_module(module=module, func="main", verbose=verbose)
    


def run_tags_cases(host:str, tags: dict[str, list[ElementInfo]], dir:str, verbose:bool) -> int:
    global GLOBAL_VARIABLES

    total_test = 0
    passed_test = 0
    failed_test = 0

    for tag, elements in tags.items():
        print(f"Testing {tag} ...")

        for el in elements:

            if verbose:
                print(f" summary = {el.summary}")
                print(f"  description = {el.description}")

            path = el.path
            method = el.method
            for case in el.cases:
                headers = case.request_header
                body = case.request_body
                test_path = f"{dir}/{tag}/{case.name}.py"
                excepted_status = case.status_code
                try:
                    module = load_module(module_path=test_path)
                    run_func_module(module=module, func="prepare", verbose=verbose)
                    variables = load_variables_module(module)

                    url = set_variables_in_data(f"{host}{path}", variables, GLOBAL_VARIABLES)
                    body = set_variables_in_data(body, variables, GLOBAL_VARIABLES)

                    # TODO: Handle if body is not JSON
                    response = requests.request(method=method,
                                                url=url,
                                                headers=headers,
                                                json=body)

                    status_code = response.status_code

                    assert status_code == excepted_status, f"excepted '{excepted_status}' status code but got {status_code} status code!"

                    total_test += 1
                    run_func_module(module=module, func="main", verbose=verbose, **{"response": response})
                    passed_test += 1

                    run_func_module(module=module, func="finalize", verbose=verbose)
                    print(f"✅ [SUCCESS] Case {case.name} Passed Successfully")

                except AssertionError as e:
                    print(f"❌ [FAILED] test {case.name}: {e}")
                    failed_test += 1

                except Exception as e:
                    print(f"❌ [FAILED] Unexpected error: {e}")
                    failed_test += 1

    print("=" * 60)
    print("Test Finished")
    print(f"Result: total: {total_test} passed: {passed_test} failed: {failed_test}")
    print("=" * 60)

    if failed_test:
        return 1

    return 0



def finale_tests(final:prepareAndFinal, file:str, verbose:bool):
    
    module = load_module(module_path=file)

    run_func_module(module=module, func="prepare", verbose=verbose)

    result = subprocess.run(final.execute, shell=True, text=True, capture_output=True)

    print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())
        raise RuntimeError(f"Failed on section final test: {result.stderr.strip()}")

    run_func_module(module=module, func="main", verbose=verbose)


def run_tests(host:str, file:str, dir:str, verbose:bool) -> int:

    yaml_serialized = YamlSyntax.from_file(SwagTaceTestFormat, file)

    test_sections:SwagTaceTestFormat = yaml_serialized.serialized_data

    project_banner_information(test_sections.openapi, test_sections.info)

    prepare_tests(test_sections.prepare, str(Path(dir) / Path("prepare.py")), verbose=verbose)

    exit_code = run_tags_cases(host, test_sections.tags, dir, verbose)

    finale_tests(test_sections.final, str(Path(dir) / Path("final.py")), verbose=verbose)

    return exit_code

