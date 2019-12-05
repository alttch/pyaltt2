import re
function_wrong_symbols = re.compile(r"[\ \"\'\:;_\/<>{}[\]~`]")


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
    params = [v.replace(')', '') if v.endswith(')') else v for v in
              val.split('(', 1)[1].split(',')]
    new_params = []
    if auto_quote:
        for p in params:
            if p and not re.match(r'"|\'\w*\"|\'', p.strip()):
                if not p.__contains__('='):
                    try:
                        float(p)
                    except ValueError:
                        p = '"{}"'.format(p.strip())
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
