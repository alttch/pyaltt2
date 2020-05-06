import re
import ast
from textwrap import dedent
from functools import lru_cache
function_wrong_symbols = re.compile(r"[\ \"\'\:;\<>{}[\]~`]")
params_wrong_symbols = re.compile(r'\w*\s*\(\s*\w*\s*\)\s*')
string_match = re.compile(r'"|\'\w*\"|\'')


@lru_cache(maxsize=4096)
def parse_func_str(val, auto_quote=True):
    """
    Parse function call from string

    Returns:
        tuple fn, args, kwargs
    Raises:
        ValueError: if string is invalid
    """

    def _invalid_arg(arg):
        raise ValueError('Invalid argument')

    def _format_arg(arg):
        try:
            return '{}.{}'.format(arg.value.id, arg.attr)
        except AttributeError:
            try:
                return arg.value.id
            except AttributeError:
                try:
                    return arg.id
                except AttributeError:
                    _invalid_arg(arg)

    val = val.strip()
    if not val or not val.endswith(')'):
        raise ValueError('Invalid syntax')
    params = val[val.find('(') + 1:val.rfind(')')].strip()
    fn = val[:val.find('(')].strip()
    # check function name
    if not fn or function_wrong_symbols.search(fn):
        raise ValueError('Invalid symbols in function name')
    # try parsing params with ast
    args = 'f({})'.format(params)
    try:
        tree = ast.parse(args)
    except:
        raise ValueError('Invalid syntax')
    funccall = tree.body[0].value
    args = []
    for arg in funccall.args:
        try:
            args.append(ast.literal_eval(arg))
        except:
            if auto_quote:
                args.append(_format_arg(arg))
            else:
                _invalid_arg(arg)
    kwargs = {}
    for arg in funccall.keywords:
        try:
            kwargs[arg.arg] = ast.literal_eval(arg.value)
        except:
            if auto_quote:
                try:
                    kwargs[arg.arg] = _format_arg(arg)
                except:
                    _invalid_arg(arg)
            else:
                _invalid_arg(arg)
    return fn, args, kwargs
