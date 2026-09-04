import asyncio
import subprocess
import time
from argparse import _SubParsersAction
from pathlib import Path
from typing import Any

from yaml_syntax.syntax import YamlSyntax

from swagtrace.consts import DEFAULT_TEST_MODULE_FOLDER, DEFAULT_YAML_FILE
from swagtrace.schemas.yaml_schema import SwagTaceTestFormat
from swagtrace.shared import (
    reset_runner_context,
    set_idle_status_runner,
    set_running_status_runner,
)
from swagtrace.utils import (
    configure_logging,
    function_manager,
    get_test_client,
    load_app,
    load_module,
    load_variables_module,
    print_error_line,
    project_banner_information,
    set_variables_in_data,
)


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

    def __exec_command(self, command: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            command, shell=True, text=True, capture_output=True, check=False
        )

        return result

    async def prepare_tests(self, file: str = "prepare.py"):

        module = load_module(module_path=str(self.project_dire / Path(file)))

        result = self.__exec_command(self.test_sections.prepare.execute)

        await function_manager.execute_function(module.main, cp=result)

        self.GLOBAL_VARIABLES = load_variables_module(module=module)

    async def finale_tests(self, file: str = "final.py"):

        module = load_module(module_path=str(self.project_dire / Path(file)))

        result = self.__exec_command(self.test_sections.final.execute)

        await function_manager.execute_function(module.main, cp=result)

    # TODO: Break this function to two more than a function
    # for clean code and keep specific responsibility for each functions
    async def run_tags_cases(
        self,
    ) -> int:

        passed_test = 0
        failed_test = 0
        start_total_time = time.time()
        GLOBAL_VARIABLES = self.GLOBAL_VARIABLES
        tags = self.test_sections.tags
        verbose = self.verbose
        client = self.client
        execute_function = function_manager.execute_function
        request = lambda *args, **kwargs: execute_function(
            client.request, *args, **kwargs
        )

        tags = {case: tags.pop(case) for case in self.cases if case in tags} or tags

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
                    test_path = f"{self.project_dire}/{tag}/{case.name}.py"
                    excepted_status = case.status_code

                    start_test_time = time.time()
                    token = None

                    try:
                        token = set_running_status_runner()
                        module = load_module(module_path=test_path)
                        await execute_function(module.prepare)
                        variables = load_variables_module(module)

                        url = set_variables_in_data(path, variables, GLOBAL_VARIABLES)
                        body = set_variables_in_data(body, variables, GLOBAL_VARIABLES)

                        # TODO: Handle if body is not JSON
                        response = await request(
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

                        await execute_function(module.main, response=response)

                        duration = round((time.time() - start_test_time) * 1000, 2)
                        passed_test += 1

                        print(
                            f"  ✅ [SUCCESS] Case {case.name} Passed Successfully ({duration}ms)",
                            flush=True,
                        )

                    except AssertionError as e:
                        duration = round((time.time() - start_test_time) * 1000, 2)
                        print(
                            f"  ❌ [FAILED] Case {case.name} ({duration}ms)", flush=True
                        )
                        print(f"         └── AssertionError: {e}", flush=True)
                        failed_test += 1

                    except Exception as e:
                        duration = round((time.time() - start_test_time) * 1000, 2)
                        print(
                            f"  ❌ [Error] Case {case.name} ({duration}ms)", flush=True
                        )
                        print(f"         └── {type(e).__name__}: {e}", flush=True)
                        print_error_line(test_path, e)
                        failed_test += 1

                    finally:
                        try:
                            await execute_function(module.finalize)
                        except Exception as e:
                            print(
                                "  ⚠️ [Warning]: Failed to run finalize function at the end of the test!"
                            )
                            print(f"         └── {type(e).__name__}: {e}", flush=True)
                            print_error_line(test_path, e)
                        finally:
                            reset_runner_context(token=token)

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

    async def run(self) -> int:
        try:
            await self.prepare_tests()

            self.exit_code = await self.run_tags_cases()

        except KeyboardInterrupt:
            print("Test Canceled")

        # TODO: make error message better for user
        except Exception as e:
            print(f"Failed to Run Test! Details: {e}")
            self.exit_code = 1

        finally:
            await self.finale_tests()

        return self.exit_code


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


def set_tester_command(subparsers: _SubParsersAction, command: str = "run") -> str:

    tests_parser = subparsers.add_parser(command, help="run tests")
    tests_parser.add_argument(
        "--host", type=str, help="API Base url", default="http://127.0.0.1:8000"
    )
    tests_parser.add_argument("--app", type=str, help="API Base url")
    tests_parser.add_argument(
        "--file",
        type=str,
        help="path of swagtrace.yaml file",
        default=DEFAULT_YAML_FILE,
    )
    tests_parser.add_argument(
        "--dir",
        type=str,
        help="path of test module",
        default=DEFAULT_TEST_MODULE_FOLDER,
    )
    tests_parser.add_argument(
        "--cases", nargs="*", help="Name of tags saved in Yaml file", default=[]
    )
    tests_parser.add_argument(
        "--verbose", action="store_true", help="verbose", default=False
    )

    tests_parser.set_defaults(func=run_tests)

    return command
