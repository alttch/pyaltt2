import re
function_wrong_symbols = re.compile(r"[\ \"\'\:;\<>{}[\]~`]")
params_wrong_symbols = re.compile(r'\w*\s*\(\s*\w*\s*\)\s*')
string_match = re.compile(r'"|\'\w*\"|\'')


def parse_func_str(val, auto_quote=True):
    """
    Parse value as function string
    e.g. myfunc(123, name="test")
    Args:
        val: value to parse
        auto_quote: quotes wrapper
    Returns:
        tuple: function-name, tuple of args, dict of kwargs
    Raises:
        ValueError: if function string can not be parsed
    """
    import textwrap
    if '(' not in val:
        raise ValueError
    val = val.strip()
    fname = val.split('(', 1)[0].strip()
    if not fname or function_wrong_symbols.search(fname):
        raise ValueError('Invalid symbols in function name')
    if fname[0] in ('@', '!', '?'):
        pfx = fname[0]
        fname = fname[1:]
    else:
        pfx = ''
    # check val suffix to avoid injections
    try:
        if val.rsplit(')', 1)[1].strip(): raise ValueError
    except IndexError:
        raise ValueError
    params = [v for v in val.split('(', 1)[1].rsplit(')', 1)[0].split(',')]
    new_params = []
    if auto_quote:
        for p in params:
            new_p = p.split('=') if p.__contains__('=') else [None, p]
            new_p1 = new_p[1].strip()
            if params_wrong_symbols.match(new_p[1].strip()):
                raise ValueError('Invalid symbols in args - {}'.format(new_p1))
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
    code = textwrap.dedent("""
    def {}(*args, **kwargs):
        global a, kw
        a = args
        kw = kwargs
    {}""").format(fname, '{}({})'.format(fname, ', '.join(new_params)))
    d = {}
    try:
        exec(code, d)
    except Exception as e:
        raise ValueError(str(e))
    return pfx + fname, d['a'], d['kw']
