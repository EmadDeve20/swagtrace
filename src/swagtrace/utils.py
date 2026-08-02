import re


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
                data = data.replace(f"{{{vn}}}", vars[vn])
            elif vn in global_vars:
                data = data.replace(f"{{{vn}}}", global_vars[vn])

    elif isinstance(data, dict):

        for key, val in data.items():
            variables_name =  get_variables(val)

            for vn in variables_name:
                if vn in vars:
                    data[key] = vars[vn]
                elif vn in global_vars:
                    data = global_vars[vn]

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
