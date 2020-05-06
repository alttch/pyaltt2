import re
import ast
from textwrap import dedent
from functools import lru_cache
function_wrong_symbols = re.compile(r"[\ \"\'\:;\<>{}[\]~`]")
params_wrong_symbols = re.compile(r'\w*\s*\(\s*\w*\s*\)\s*')
string_match = re.compile(r'"|\'\w*\"|\'')

@lru_cache(maxsize=4096)
def parse_func_str(val, auto_quote=True):
    val = val.strip()
    if not val or not val.endswith(')'):
        raise ValueError('Invalid syntax')
    params = val[val.find('(') + 1:val.rfind(')')].strip()
    fn = val[:val.find('(')].strip()
    # check function name
    if not fn or function_wrong_symbols.search(fn):
        raise ValueError('Invalid symbols in function name')
    # try parsing params with ast
    try:
        args = 'f({})'.format(params)
        tree = ast.parse(args)
        funccall = tree.body[0].value

        args = [ast.literal_eval(arg) for arg in funccall.args]
        kwargs = {
            arg.arg: ast.literal_eval(arg.value) for arg in funccall.keywords
        }
    # try parsing and auto quoting
    except (ValueError, SyntaxError) as e:
        if not auto_quote:
            raise ValueError(e)
        params = [v for v in val.split('(', 1)[1].rsplit(')', 1)[0].split(',')]
        new_params = []
        if auto_quote:
            for p in params:
                new_p = p.split('=') if p.__contains__('=') else [None, p]
                new_p1 = new_p[1].strip()
                if params_wrong_symbols.match(new_p[1].strip()):
                    raise ValueError(
                        'Invalid symbols in args - {}'.format(new_p1))
                if new_p1 and not string_match.match(new_p1):
                    try:
                        float(new_p1)
                    except ValueError:
                        p = '"{}"'.format(new_p[1].strip(
                        )) if new_p[0] is None else '{}="{}"'.format(
                            new_p[0], new_p1)
                new_params.append(p)
        else:
            new_params = params
        code = dedent("""
        def {}(*args, **kwargs):
            global a, kw
            a = args
            kw = kwargs
        {}""").format(fn, '{}({})'.format(fn, ', '.join(new_params)))
        d = {}
        try:
            exec(code, d)
            args = d['a']
            kwargs = d['kw']
        except Exception as e:
            raise ValueError(str(e))
    return fn, tuple(args), kwargs
