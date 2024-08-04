import ast
import builtins
import re
from typing import Any, Callable, Dict, Text


from tools import tools
from tools.logHandler import SingletonLogger
from tools.tools import get_data_by_json_path

VariablesMapping = Dict[Text, Any]
FunctionsMapping = Dict[Text, Callable]
# use $$ to escape $ notation
dolloar_regex_compile = re.compile(r"\$\$")
# variable notation, e.g. ${var} or $var
# variable should start with a-zA-Z_
variable_regex_compile = re.compile(r"\$\{([a-zA-Z_]\w*)\}|\$([a-zA-Z_]\w*)")
# 提取jsonPath $.request.txCodeCallbackList[0].txCode
json_path_regex_compile = re.compile(r"\$[\w\[\]\-\.]+")
# function notation, e.g. ${func1($var_1, $var_3)}
# function_regex_compile = re.compile(r"\$\{([a-zA-Z_]\w*)\(([\$\w\.\-/\s=,]*)\)\}")
function_regex_compile = re.compile(r"\$\{([a-zA-Z_]\w*)\(([\$\w\.\[\]\-/\s=,]*)\)\}")

logger = SingletonLogger().logger


def parse_string_value(str_value: Text) -> Any:
    """parse string to number if possible
    e.g. "123" => 123
         "12.2" => 12.3
         "abc" => "abc"
         "$var" => "$var"
    """
    try:
        return ast.literal_eval(str_value)
    except ValueError:
        return str_value
    except SyntaxError:
        # e.g. $var, ${func}
        return str_value


def parse_function_params(params: Text) -> Dict:
    """parse function params to args and kwargs.

    Args:
        params (str): function param in string

    Returns:
        dict: function meta dict

            {
                "args": [],
                "kwargs": {}
            }

    Examples:
        >>> parse_function_params("")
        {'args': [], 'kwargs': {}}

        >>> parse_function_params("5")
        {'args': [5], 'kwargs': {}}

        >>> parse_function_params("1, 2")
        {'args': [1, 2], 'kwargs': {}}

        >>> parse_function_params("a=1, b=2")
        {'args': [], 'kwargs': {'a': 1, 'b': 2}}

        >>> parse_function_params("1, 2, a=3, b=4")
        {'args': [1, 2], 'kwargs': {'a':3, 'b':4}}

    """
    function_meta = {"args": [], "kwargs": {}}

    params_str = params.strip()
    if params_str == "":
        return function_meta

    args_list = params_str.split(",")
    for arg in args_list:
        arg = arg.strip()
        if "=" in arg:
            key, value = arg.split("=")
            function_meta["kwargs"][key.strip()] = parse_string_value(value.strip())
        else:
            function_meta["args"].append(parse_string_value(arg))

    return function_meta


def get_mapping_variable(
        variable_name: Text, variables_mapping: VariablesMapping
) -> Any:
    """get variable from variables_mapping.

    Args:
        variable_name (str): variable name
        variables_mapping (dict): variables mapping

    Returns:
        mapping variable value.

    Raises:
        exceptions.VariableNotFound: variable is not found.

    """
    # TODO: get variable from debugtalk module and environ
    try:
        return variables_mapping[variable_name]
    except KeyError:
        raise RuntimeError(f"VariableNotFound {variable_name} not found in {variables_mapping}")


def get_mapping_function(
        function_name: Text, functions_mapping: FunctionsMapping
) -> Callable:
    """get function from functions_mapping,
        if not found, then try to check if builtin function.

    Args:
        function_name (str): function name
        functions_mapping (dict): functions mapping

    Returns:
        mapping function object.

    Raises:
        exceptions.FunctionNotFound: function is neither defined in debugtalk.py nor builtin.

    """
    if function_name in functions_mapping:
        return functions_mapping[function_name]

    elif function_name in ["environ", "ENV"]:
        return tools.get_os_environ

    try:
        # check if Python builtin functions
        return getattr(builtins, function_name)
    except AttributeError:
        pass

    raise RuntimeError(f"FunctionNotFound {function_name} is not found.")

def parse_string(
        raw_string: Text,
        variables_mapping: VariablesMapping,
        functions_mapping: FunctionsMapping,
        json_data: Dict = None
) -> Any:
    """parse string content with variables and functions mapping.

    Args:
        raw_string: raw string content to be parsed.
        variables_mapping: variables mapping.
        functions_mapping: functions mapping.

    Returns:
        str: parsed string content.

    Examples:
        >>> raw_string = "abc${add_one($num)}def"
        >>> variables_mapping = {"num": 3}
        >>> functions_mapping = {"add_one": lambda x: x + 1}
        >>> parse_string(raw_string, variables_mapping, functions_mapping)
            "abc4def"

    """
    try:
        match_start_position = raw_string.index("$", 0)
        parsed_string = raw_string[0:match_start_position]
    except ValueError:
        parsed_string = raw_string
        return parsed_string

    while match_start_position < len(raw_string):

        # Notice: notation priority
        # $$ > ${func($a, $b)} > $var

        # search $$
        dollar_match = dolloar_regex_compile.match(raw_string, match_start_position)
        if dollar_match:
            match_start_position = dollar_match.end()
            parsed_string += "$"
            continue

        # search function like ${func($a, $b)}
        func_match = function_regex_compile.match(raw_string, match_start_position)
        if func_match:
            func_name = func_match.group(1)
            func = get_mapping_function(func_name, functions_mapping)

            func_params_str = func_match.group(2)
            function_meta = parse_function_params(func_params_str)
            args = function_meta["args"]
            kwargs = function_meta["kwargs"]
            parsed_args = parse_data(args, variables_mapping, functions_mapping, json_data=json_data)
            parsed_kwargs = parse_data(kwargs, variables_mapping, functions_mapping, json_data=json_data)

            try:
                func_eval_value = func(*parsed_args, **parsed_kwargs)
            except Exception as ex:
                logger.error(
                    f"call function error:\n"
                    f"func_name: {func_name}\n"
                    f"args: {parsed_args}\n"
                    f"kwargs: {parsed_kwargs}\n"
                    f"{type(ex).__name__}: {ex}"
                )
                raise

            func_raw_str = "${" + func_name + f"({func_params_str})" + "}"
            if func_raw_str == raw_string:
                # raw_string is a function, e.g. "${add_one(3)}", return its eval value directly
                return func_eval_value

            # raw_string contains one or many functions, e.g. "abc${add_one(3)}def"
            parsed_string += str(func_eval_value)
            match_start_position = func_match.end()
            continue

        # search variable like ${var} or $var
        var_match = variable_regex_compile.match(raw_string, match_start_position)
        if var_match:
            var_name = var_match.group(1) or var_match.group(2)
            var_value = get_mapping_variable(var_name, variables_mapping)

            if f"${var_name}" == raw_string or "${" + var_name + "}" == raw_string:
                # raw_string is a variable, $var or ${var}, return its value directly
                return var_value

            # raw_string contains one or many variables, e.g. "abc${var}def"
            parsed_string += str(var_value)
            match_start_position = var_match.end()
            continue

        json_path_match = json_path_regex_compile.match(raw_string, match_start_position)
        if json_path_match:
            json_path = json_path_match.group(0)

            data = get_data_by_json_path(json_data, json_path)
            if f"${json_path}" == raw_string or "${" + data + "}" == raw_string:
                # raw_string is a variable, $var or ${var}, return its value directly
                return json_path

            parsed_string += str(data)
            match_start_position = json_path_match.end()
            continue

        curr_position = match_start_position
        try:
            # find next $ location
            match_start_position = raw_string.index("$", curr_position + 1)
            remain_string = raw_string[curr_position:match_start_position]
        except ValueError:
            remain_string = raw_string[curr_position:]
            # break while loop
            match_start_position = len(raw_string)

        parsed_string += remain_string

    return parsed_string


def parse_data(
        raw_data: Any,
        variables_mapping: VariablesMapping = None,
        functions_mapping: FunctionsMapping = None,
        json_data: Dict = None
) -> Any:
    """parse raw data with evaluated variables mapping.
    Notice: variables_mapping should not contain any variable or function.
    """
    if isinstance(raw_data, str):
        # content in string format may contains variables and functions
        variables_mapping = variables_mapping or {}
        functions_mapping = functions_mapping or {}
        # only strip whitespaces and tabs, \n\r is left because they maybe used in changeset
        raw_data = raw_data.strip(" \t")
        return parse_string(raw_data, variables_mapping, functions_mapping, json_data=json_data)

    elif isinstance(raw_data, (list, set, tuple)):
        return [
            parse_data(item, variables_mapping, functions_mapping, json_data=json_data) for item in raw_data
        ]

    elif isinstance(raw_data, dict):
        parsed_data = {}
        for key, value in raw_data.items():
            parsed_key = parse_data(key, variables_mapping, functions_mapping, json_data=json_data)
            parsed_value = parse_data(value, variables_mapping, functions_mapping, json_data=json_data)
            parsed_data[parsed_key] = parsed_value

        return parsed_data

    else:
        # other types, e.g. None, int, float, bool
        return raw_data


if __name__ == '__main__':
    raw_string = '${method1($.request.tx_CodeCallbackList[0].tx-Code)}'
    match_start_position = 10
    json_path_match = json_path_regex_compile.match(raw_string, match_start_position)

    result1 = json_path_match.group(0)
    print(result1)
