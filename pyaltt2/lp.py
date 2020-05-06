import re
import ast
from textwrap import dedent
from functools import lru_cache

function_wrong_symbols = re.compile(r"[\ \"\'\:;\<>{}[\]~`]")


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

    def _format_arg(arg, kw=False):
        try:
            return ast.literal_eval(arg.value if kw else arg)
        except:
            if auto_quote:
                try:
                    return [
                        _format_arg(a)
                        for a in (arg.value.elts if kw else arg.elts)
                    ]
                except:
                    try:
                        return '{}.{}'.format(
                            arg.value.value.id,
                            arg.value.attr) if kw else '{}.{}'.format(
                                arg.value.id, arg.attr)
                    except:
                        try:
                            return arg.value.id if kw else arg.id
                        except:
                            _invalid_arg(arg)
            else:
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
    args = [_format_arg(arg) for arg in funccall.args]
    kwargs = {arg.arg: _format_arg(arg, kw=True) for arg in funccall.keywords}
    return fn, args, kwargs
