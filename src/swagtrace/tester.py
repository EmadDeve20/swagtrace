import asyncio
import subprocess
import time
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

from httpx import Client
from yaml_syntax.syntax import YamlSyntax

from swagtrace.config import get_config
from swagtrace.schemas.yaml_schema import (
    ElementInfo,
    SwagTaceTestFormat,
    prepareAndFinal,
)
from swagtrace.utils import (
    arun_func_module,
    configure_logging,
    get_test_client,
    load_app,
    load_module,
    load_variables_module,
    print_error_line,
    project_banner_information,
    run_func_module,
    set_variables_in_data,
    function_manager,
)

GLOBAL_VARIABLES = {}


def prepare_tests(prepare: prepareAndFinal, file: str, verbose: bool):
    global GLOBAL_VARIABLES

    module = load_module(module_path=file)

    result = subprocess.run(prepare.execute, shell=True, text=True, capture_output=True)

    run_func_module(module=module, func="main", verbose=verbose, **{"cp": result})

    GLOBAL_VARIABLES = load_variables_module(module=module)


def run_tags_cases(
    client: Client, tags: dict[str, list[ElementInfo]], dir: str, verbose: bool
) -> int:
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
                    response = client.request(
                        method=method, url=url, headers=headers, json=body
                    )

                    status_code = response.status_code

                    assert status_code == excepted_status, (
                        f"excepted '{excepted_status}' status code but got {status_code} status code!"
                    )
                    if case.response_content:
                        expected_response = case.response_content
                        response_content = response.content.decode()
                        assert response_content == expected_response, (
                            f"excepted '{expected_response}' response but got {response_content} response!"
                        )

                    run_func_module(
                        module=module,
                        func="main",
                        verbose=verbose,
                        **{"response": response},
                    )

                    run_func_module(module=module, func="finalize", verbose=verbose)
                    duration = round((time.time() - start_test_time) * 1000, 2)
                    passed_test += 1

                    print(
                        f"  ✅ [SUCCESS] Case {case.name} Passed Successfully ({duration}ms)"
                    )

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
    print(
        f"Result: total: {passed_test + failed_test} passed: {passed_test} failed: {failed_test}"
    )
    print("=" * 60)

    if failed_test:
        return 1

    return 0


# TODO: I'm going to create a best practice workflow to handle both stnc abd async projects
# I will use this for my own test and my personal project
async def arun_tags_cases(
    client: Client,
    tags: dict[str, list[ElementInfo]],
    cases: list[str],
    dir: str,
    verbose: bool,
) -> int:

    global GLOBAL_VARIABLES

    passed_test = 0
    failed_test = 0
    start_total_time = time.time()

    tags = {case: tags.pop(case) for case in cases if case in tags} or tags

    for tag, elements in tags.items():
        for el in elements:
            if verbose:
                print(f" summary = {el.summary}, flush=True")
                print(f"  description = {el.description}", flush=True)

            path = el.path
            method = el.method
            for case in el.cases:
                headers = case.request_header
                body = case.request_body
                test_path = f"{dir}/{tag}/{case.name}.py"
                excepted_status = case.status_code

                start_test_time = time.time()

                try:
                    module = load_module(module_path=test_path)
                    await arun_func_module(
                        module=module, func="prepare", verbose=verbose
                    )
                    variables = load_variables_module(module)

                    url = set_variables_in_data(path, variables, GLOBAL_VARIABLES)
                    body = set_variables_in_data(body, variables, GLOBAL_VARIABLES)

                    # TODO: Handle if body is not JSON
                    response = client.request(
                        method=method, url=url, headers=headers, json=body
                    )

                    status_code = response.status_code

                    assert status_code == excepted_status, (
                        f"excepted '{excepted_status}' status code but got {status_code} status code!"
                    )
                    if case.response_content:
                        expected_response = case.response_content
                        response_content = response.content.decode()
                        assert response_content == expected_response, (
                            f"excepted '{expected_response}' response but got {response_content} response!"
                        )

                    await arun_func_module(
                        module=module, func="main", verbose=verbose, response=response
                    )

                    duration = round((time.time() - start_test_time) * 1000, 2)
                    passed_test += 1

                    print(
                        f"  ✅ [SUCCESS] Case {case.name} Passed Successfully ({duration}ms)",
                        flush=True,
                    )

                except AssertionError as e:
                    duration = round((time.time() - start_test_time) * 1000, 2)
                    print(f"  ❌ [FAILED] Case {case.name} ({duration}ms)", flush=True)
                    print(f"         └── AssertionError: {e}", flush=True)
                    failed_test += 1

                except Exception as e:
                    duration = round((time.time() - start_test_time) * 1000, 2)
                    print(f"  ❌ [Error] Case {case.name} ({duration}ms)", flush=True)
                    print(f"         └── {type(e).__name__}: {e}", flush=True)
                    print_error_line(test_path, e)
                    failed_test += 1

                finally:
                    try:
                        await arun_func_module(
                            module=module, func="finalize", verbose=verbose
                        )
                    except Exception as e:
                        print(
                            f"  ⚠️ [Warning]: Failed to run finalize function at the end of the test!"
                        )
                        print(f"         └── {type(e).__name__}: {e}", flush=True)
                        print_error_line(test_path, e)

    duration = round((time.time() - start_total_time) * 1000, 2)

    print("=" * 60, flush=True)
    print(f"Test Finished ({duration}ms)", flush=True)
    print(
        f"Result: total: {passed_test + failed_test} passed: {passed_test} failed: {failed_test}",
        flush=True,
    )
    print("=" * 60, flush=True)

    if failed_test:
        return 1

    return 0


def finale_tests(final: prepareAndFinal, file: str, verbose: bool):

    module = load_module(module_path=file)

    result = subprocess.run(final.execute, shell=True, text=True, capture_output=True)

    run_func_module(module=module, func="main", verbose=verbose, **{"cp": result})


# TODO: Update Workflow if need run app first and app like FastAPI need DB
# because app load first and if DB will generate on prepare stage, it can got and error
def run_tests(
    host: str | None,
    app: str | None,
    file: str,
    dir: str,
    cases: list[str],
    verbose: bool,
) -> int:

    exit_code = 0
    app_module = None
    app_name = None

    if app:
        app_module, app_name = load_app(app_path=app)
        app = getattr(app_module, app_name)

    config = get_config()

    yaml_serialized = YamlSyntax.from_file(SwagTaceTestFormat, file)

    test_sections: SwagTaceTestFormat = yaml_serialized.serialized_data

    try:
        project_banner_information(test_sections.openapi, test_sections.info)
    except Exception as e:
        finale_tests(
            test_sections.final, str(Path(dir) / Path("final.py")), verbose=verbose
        )
        return 1

    prepare_tests(
        test_sections.prepare, str(Path(dir) / Path("prepare.py")), verbose=verbose
    )

    try:
        client = get_test_client(host=host, app=app)
    except Exception as e:
        print(e)
        return 1

    configure_logging()

    if config.project.type == "async":
        exit_code = asyncio.run(
            arun_tags_cases(client, test_sections.tags, cases, dir, verbose)
        )
    else:
        exit_code = run_tags_cases(client, test_sections.tags, dir, verbose)

    finale_tests(
        test_sections.final, str(Path(dir) / Path("final.py")), verbose=verbose
    )

    return exit_code


class TestRunner:
    def __init__(
        self,
        host: str | None,
        app: str | None,
        file: str,
        dir: str,
        cases: list[str],
        verbose: bool,
    ):

        self.exit_code = 0
        self.app_module = None
        self.app_name = None
        self.cases = cases
        self.project_dire = Path(dir)
        self.verbose = verbose
        self.GLOBAL_VARIABLES: dict[str, Any] = {}

        if app:
            app_module, app_name = load_app(app_path=app)
            app = getattr(app_module, app_name)

        yaml_serialized = YamlSyntax.from_file(SwagTaceTestFormat, file)

        self.test_sections: SwagTaceTestFormat = yaml_serialized.serialized_data

        project_banner_information(self.test_sections.openapi, self.test_sections.info)

        self.client = get_test_client(host=host, app=app)

        configure_logging()

    async def __exec_command(self, command: str) -> asyncio.subprocess.Process:
        return await asyncio.create_subprocess_shell(
            command,
            shell=True,
        )

    async def prepare_tests(self, file: str = "prepare.py"):

        module = load_module(module_path=str(self.project_dire /  Path(file)))

        result = await self.__exec_command(self.test_sections.prepare.execute)

        await function_manager.execute_function(module.main, cp=result)

        self.GLOBAL_VARIABLES = load_variables_module(module=module)

    async def finale_tests(self, file: str = "final.py"):

        module = load_module(module_path=str(self.project_dire /  Path(file)))

        result = await self.__exec_command(self.test_sections.prepare.execute)

        await function_manager.execute_function(module.main, cp=result)

    async def run(self) -> int:
        try:
            await self.prepare_tests()

            await self.finale_tests()

            return 0

        # TODO: make error message better for user
        except Exception as e:
            print(f"Failed to Run Test! Details: {e}")
            return 1


def run_tests(
    host: str | None,
    app: str | None,
    file: str,
    dir: str,
    cases: list[str],
    verbose: bool,
) -> int:

    test_runner = TestRunner(
        host=host, app=app, file=file, cases=cases, dir=dir, verbose=verbose
    )

    exit_code = asyncio.run(test_runner.run())

    return exit_code
