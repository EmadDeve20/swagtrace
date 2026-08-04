from typing import Optional, Any

from types import ModuleType

from pathlib import Path

from starlette.testclient import TestClient

import re
import importlib
import sys
import logging
import httpx

from swagtrace.config import get_config


def load_module(module_path: str, project_root: Optional[str] = None):
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
    


def run_func_module(module:ModuleType, func:str, verbose:bool=False, *args, **kwargs):
    if hasattr(module, func):
        if verbose:
            print(f"▶ Running {func} function: {module}")
        getattr(module, func)(*args, **kwargs)
    else:
        print(f"⚠ {func} Function Does not exist in {func} file!")


async def arun_func_module(module:ModuleType, func:str, verbose:bool=False, *args, **kwargs):
    if hasattr(module, func):
        if verbose:
            print(f"▶ Running {func} function: {module}")
        await getattr(module, func)(*args, **kwargs)
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


def get_variables(text:str, vars:set = {}) -> set[str]:

    if len(vars) == 0:
        vars = set()

    if "{" in text and "}" in text:
        start_var_idx = text.index("{")
        end_var_idx = text.index("}")

        if start_var_idx > end_var_idx:
            return vars

        vars.add(text[start_var_idx+1:end_var_idx])

        return get_variables(text[end_var_idx+1:], vars)

    return vars


def set_variables_in_data(data:str|dict, vars:dict, global_vars:dict) -> str | dict:

    if isinstance(data, str):
        variables_name =  get_variables(data)

        for vn in variables_name:
            if vn in vars:
                data = data.replace(f"{{{vn}}}", str(vars[vn]))
            elif vn in global_vars:
                data = data.replace(f"{{{vn}}}", str(global_vars[vn]))

    elif isinstance(data, dict):

        for key, val in data.items():
            variables_name =  get_variables(val)

            for vn in variables_name:

                if vn in vars:
                    data[key] = data[key].replace(f"{{{vn}}}", str(vars[vn]))

                elif vn in global_vars:
                    data[key] = data[key].replace(f"{{{vn}}}", str(global_vars[vn]))

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
    pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', template)
    pattern = f'^{pattern}$'

    match = re.match(pattern, actual_path)
    if match:
        return match.groupdict()
    return None


# TODO: Improve this function to yield and handle for transporter in config file [asgi, wsgi]
# also handle for project type [async, sync]
def get_test_client(
    host: Optional[str] = None, 
    app: Optional[str] = None
) -> httpx.Client:

    # In-Memory Mode
    if app:
        module_path, app_name = app.split(":")

        if not module_path.endswith(".py"):
            module_path += ".py"

        module = load_module(module_path)

        app = getattr(module, app_name)

        return TestClient(app)
    
    # Network Mode
    if host:
        return httpx.Client(base_url=host.rstrip('/'))


    raise ValueError("Either 'host' or 'app' parameter must be provided.")


def configure_logging():

    config = get_config()

    logs_level = config.project.logging.model_dump()

    for level in logs_level:

        log_level = getattr(logging, level.upper(), logging.WARNING)

        for logger_name in logs_level[level]:

            logging.getLogger(logger_name).setLevel(log_level)

