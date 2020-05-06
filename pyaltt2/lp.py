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
    if fn[0] in ('@', '!', '?'):
        pfx = fn[0]
        fn = fn[1:]
    else:
        pfx = ''
    # check function name
    if not fn or function_wrong_symbols.search(fn):
        raise ValueError('Invalid symbols in function name')
    # try parsing params with ast
    try:
        code = 'f({})'.format(params)
        try:
            tree = ast.parse(code)
        except:
            raise ValueError('Invalid syntax')
        funccall = tree.body[0].value
        args = [_format_arg(arg) for arg in funccall.args]
        kwargs = {
            arg.arg: _format_arg(arg, kw=True) for arg in funccall.keywords
        }
    except ValueError:
        # try parsing manually, less features
        try:
            if val.rsplit(')', 1)[1].strip():
                raise ValueError
        except IndexError:
            raise ValueError
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
            args = list(d['a'])
            kwargs = d['kw']
        except Exception as e:
            raise ValueError(str(e))
    return pfx + fn, args, kwargs
