import importlib
import inspect
import linecache
import logging
import os
import re
import sys
import traceback
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

from readchar import readkey

DATA_OUTPUT = TypeVar("DATA_OUTPUT", str, dict[str, Any], list)


import httpx2 as httpx
from starlette.testclient import TestClient

from swagtrace.config import get_config


def load_module(module_path: str, project_root: str | None = None):
    path = Path(module_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"❌ File '{module_path}' Does not exist!")

    if project_root is None:
        project_root = str(path.parent)
    else:
        project_root = str(Path(project_root).resolve())

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    module_name = path.stem

    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


class function_manager:
    def __init__(self, func):
        self.func = func

        if inspect.iscoroutinefunction(func) or inspect.isawaitable(func):
            self.is_async = True
            self._wrapper = self._async_wrapper
        else:
            self.is_async = False
            self._wrapper = self._sync_wrapper

    def __call__(self, *args, **kwargs):
        return self._wrapper(*args, **kwargs)

    def _sync_wrapper(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    async def _async_wrapper(self, *args, **kwargs):
        if inspect.isawaitable(self.func) and not inspect.iscoroutinefunction(
            self.func
        ):
            return await self.func

        return await self.func(*args, **kwargs)

    @staticmethod
    def get_function_address(func, *args, **kwrags):
        new_instance = function_manager(func)
        return new_instance(*args, **kwrags)

    @staticmethod
    async def execute_function(func, *args, **kwrags):
        new_instance = function_manager(func)

        if new_instance.is_async:
            return await new_instance(*args, **kwrags)

        return new_instance(*args, **kwrags)


def run_func_module(
    module: ModuleType, func: str, verbose: bool = False, *args, **kwargs
):
    if hasattr(module, func):
        if verbose:
            print(f"▶ Running {func} function: {module}")
        getattr(module, func)(*args, **kwargs)
    else:
        print(f"⚠ {func} Function Does not exist in {module} file!")


async def arun_func_module(
    module: ModuleType, func: str, verbose: bool = False, *args, **kwargs
):
    if hasattr(module, func):
        if verbose:
            print(f"▶ Running {func} function: {module}")
        await getattr(module, func)(*args, **kwargs)
    else:
        print(f"⚠ {func} Function Does not exist in {func} file!")


def load_variables_module(
    module: ModuleType, var_name: str = "VARIABLES"
) -> dict[str, Any]:

    if hasattr(module, var_name):
        variables = getattr(module, var_name)
        return variables
    else:
        return {}


def project_banner_information(openapi: str, info: dict):

    print(f"OpenAPI: {openapi}")

    for k, v in info.items():
        print(f"{k}: {v}")


def set_variables_in_data(
    data: DATA_OUTPUT, vars: dict, global_vars: dict
) -> DATA_OUTPUT:
    pattern = re.compile(r"\{(\w+)\}")

    def replacer(match: re.Match) -> str:
        key = match.group(1)

        if key in vars:
            return str(vars[key])

        elif key in global_vars:
            return str(global_vars[key])

        return match.group(0)

    if isinstance(data, str):
        return pattern.sub(replacer, data)

    elif isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, (dict, list, str)):
                data[key] = set_variables_in_data(val, vars, global_vars)

    elif isinstance(data, list):
        for idx, chunk in enumerate(data):
            if isinstance(chunk, (dict, list, str)):
                data[idx] = set_variables_in_data(chunk, vars, global_vars)

    return data


def match_path_template(template: str, actual_path: str) -> dict | None:
    """
    Match an actual URL path against a path template containing path parameters.

    Path parameters in the template must be written as {param_name}.
    On a successful match, returns a dictionary mapping each parameter name
    to the value extracted from the actual path. Returns None if the paths
    do not match.

    Args:
        template: Path template, e.g. "/users/{user_id}/orders/{order_id}"
        actual_path: Concrete path received from the request, e.g. "/users/42/orders/abc-123"

    Returns:
        A dict of captured path parameters on success, otherwise None.
    """
    # Convert {param} placeholders into named regex groups
    pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", template)
    pattern = f"^{pattern}$"

    match = re.match(pattern, actual_path)
    if match:
        return match.groupdict()
    return None


def load_app(app_path: str) -> tuple[ModuleType, Any]:

    module_path, app_name = app_path.split(":")

    if not module_path.endswith(".py"):
        module_path += ".py"

    module = load_module(module_path)

    return module, app_name


# TODO: Improve this function to yield and handle for transporter in config file [asgi, wsgi]
# also handle for project type [async, sync]
def get_test_client(host: str | None = None, app: Any | None = None) -> httpx.Client:

    # In-Memory Mode
    if app:
        return TestClient(app)

    # Network Mode
    if host:
        return httpx.Client(base_url=host.rstrip("/"))

    raise ValueError("Either 'host' or 'app' parameter must be provided.")


def configure_logging():

    config = get_config()

    logs_level = config.project.logging.model_dump()

    for level in logs_level:
        log_level = getattr(logging, level.upper(), logging.WARNING)

        for logger_name in logs_level[level]:
            logging.getLogger(logger_name).setLevel(log_level)


def print_error_line(test_path: str | Path, e: Exception):

    tb = traceback.extract_tb(e.__traceback__)

    frame = None
    for f in reversed(tb):
        if os.path.abspath(f.filename) == os.path.abspath(test_path):
            frame = f
            break

    if frame:
        print(f"\n         File: {frame.filename}")
        print(f"         Line: {frame.lineno}\n")

        start = max(frame.lineno - 2, 1)
        end = frame.lineno + 2

        for lineno in range(start, end + 1):
            code = linecache.getline(frame.filename, lineno).rstrip()

            if lineno == frame.lineno:
                print(f"      >>> {lineno:4} | {code}")
            else:
                print(f"          {lineno:4} | {code}")
    else:
        traceback.print_exc()

def getch(prompt:str) -> str:
    """
    get character from input/user

    Args:
        prompt (str): prompt message to get user Input

    Returns:
        str: return inout character
    """

    print(prompt, flush=True)

    return readkey()

    
def get_yes_no_user_options(
    msg: str, yes_option: str = "y", no_option: str = "n", default_option: str = "y"
) -> bool:
    """
    Ask yes/no question from user 

    Args:
        msg (str): message to get yse or no answer. write answer without Question mark it will add at the end of question automatically
        yes_option (str, optional): Character for yes answer. Defaults to "y".
        no_option (str, optional): Character for no answer. Defaults to "n".
        default_option (str, optional): Default option it useful when user only press Enter key. Defaults to "y".

    Raises:
        ValueError: raise Value error if default_option is not same of one of yes/no options 

    Returns:
        bool: return user's answer. it will be True of user answer was Yes otherwise, False
    """

    if default_option != yes_option and default_option != no_option:
        raise ValueError("default_option must be one of yes or no options!")

    user_input_prompt = f"{msg}? [{yes_option.upper() if default_option.lower() == yes_option.lower() else yes_option.lower()}/{no_option.upper() if default_option.lower() == no_option.lower() else no_option.lower()}]"

    DEFAULT_INPUT_CHAR = ["\n", "\r\n", "\r"]

    user_op = getch(user_input_prompt)

    while (
        user_op.lower() != yes_option.lower()
        and user_op.lower() != no_option.lower()
        and user_op not in DEFAULT_INPUT_CHAR
    ):
        if user_op != no_option:
            print("Wrong Answer!")

        user_op = getch(user_input_prompt)

    if user_op in DEFAULT_INPUT_CHAR:
        user_op = default_option

    return user_op == yes_option 

