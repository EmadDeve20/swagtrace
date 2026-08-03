

import subprocess
import time

from pathlib import Path

from httpx import Client

from yaml_syntax.syntax import YamlSyntax

from swagtrace.yaml_schema import ElementInfo, prepareAndFinal, SwagTaceTestFormat
from swagtrace.utils import (
set_variables_in_data,
get_test_client,
load_module,
load_variables_module,
run_func_module,
project_banner_information,
configure_logging
)


GLOBAL_VARIABLES = {}


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
    


def run_tags_cases(client:Client, tags: dict[str, list[ElementInfo]], dir:str, verbose:bool) -> int:
    global GLOBAL_VARIABLES

    passed_test = 0
    failed_test = 0
    start_total_time = time.time()

    for tag, elements in tags.items():
        print(f"Testing {tag} ...")

        for el in elements:

            if verbose:
                print(f" summary = {el.summary}")
                print(f"  description = {el.description}")

            path = el.path
            method = el.method
            for case in el.cases:
                start_test_time = time.time()
                headers = case.request_header
                body = case.request_body
                test_path = f"{dir}/{tag}/{case.name}.py"
                excepted_status = case.status_code

                try:
                    module = load_module(module_path=test_path)
                    run_func_module(module=module, func="prepare", verbose=verbose)
                    variables = load_variables_module(module)

                    url = set_variables_in_data(path, variables, GLOBAL_VARIABLES)
                    body = set_variables_in_data(body, variables, GLOBAL_VARIABLES)

                    # TODO: Handle if body is not JSON
                    response = client.request(method=method,
                                                url=url,
                                                headers=headers,
                                                json=body)

                    status_code = response.status_code

                    assert status_code == excepted_status, f"excepted '{excepted_status}' status code but got {status_code} status code!"
                    if case.response_content:
                        expected_response = case.response_content
                        response_content = response.content.decode()
                        assert response_content == expected_response, f"excepted '{expected_response}' response but got {response_content} response!"

                    run_func_module(module=module, func="main", verbose=verbose, **{"response": response})

                    run_func_module(module=module, func="finalize", verbose=verbose)
                    duration = round((time.time() - start_test_time) * 1000, 2)
                    passed_test += 1

                    print(f"  ✅ [SUCCESS] Case {case.name} Passed Successfully ({duration}ms)")

                except AssertionError as e:
                    duration = round((time.time() - start_test_time) * 1000, 2)
                    print(f"  ❌ [FAILED] Case {case.name} ({duration}ms)")
                    print(f"         └── AssertionError: {e}")
                    failed_test += 1

                except Exception as e:
                    duration = round((time.time() - start_test_time) * 1000, 2)
                    print(f"  ❌ [Error] Case {case.name} ({duration}ms)")
                    print(f"         └── {type(e).__name__}: {e}")
                    failed_test += 1

    duration = round((time.time() - start_total_time) * 1000, 2)

    print("=" * 60)
    print(f"Test Finished ({duration}ms)")
    print(f"Result: total: {passed_test + failed_test} passed: {passed_test} failed: {failed_test}")
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


def run_tests(host:str|None, app:str|None, file:str, dir:str, verbose:bool) -> int:

    try:
        client = get_test_client(host=host, app=app)
    except Exception as e:
        print(e)
        return 1

    yaml_serialized = YamlSyntax.from_file(SwagTaceTestFormat, file)

    test_sections:SwagTaceTestFormat = yaml_serialized.serialized_data

    project_banner_information(test_sections.openapi, test_sections.info)

    configure_logging()

    prepare_tests(test_sections.prepare, str(Path(dir) / Path("prepare.py")), verbose=verbose)

    exit_code = run_tags_cases(client, test_sections.tags, dir, verbose)

    finale_tests(test_sections.final, str(Path(dir) / Path("final.py")), verbose=verbose)

    return exit_code

