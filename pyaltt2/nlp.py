import re
function_wrong_symbols = re.compile(r"[<>{}[\]~`]")


def parse_func_str(s):
    """
    Parse string to a function

    Parses a given string to a Python-like function

    Examples of valid strings:
    
        myfunc()
        myfunc('test', '123')
        myfunc(test, 123)
        myfunc(1,2,3)
        myfunc(1,2,name='test')
        myfunc(name=test)
        myfunc(name='test',value='123')

    Returns:
        tuple: (function_name, [list of args], {dict of kwargs})
    Raises:
        ValueError
    """
    s = s.strip()
    if not s.endswith(')'):
        raise ValueError('ERROR: argument doesn\'t have brackets')
    r = s.replace(')', '').split('(')
    name = r.pop(0).strip()
    if function_wrong_symbols.search(name) or name.find(' ') != -1:
        raise ValueError('Invalid symbols in argument')
    args = []
    list_args = []
    list_kw = []
    kw = {}
    check = re.compile(r'(,*\s*\'*\w+\'*\s*[=]\s*[\'\"]*.*[\'|\"]*)')
    argum = [i.strip() for i in check.split(r[0]) if i]
    for a in argum:
        a = a.replace(',', '', 1).strip() if a.startswith(',') else a
        if not a.__contains__('='):
            list_args = a
        elif a.__contains__('='):
            if a.startswith('\'') or a.startswith('\"'):
                list_args = a
            else:
                list_kw = a
    if list_args:
        clear_arg = [
            a.strip()
            for a in re.split(
                r'(,*\s*\w*\s*),|(\s*[\"|\'][\w\s,]*[\s\w]*[\"|\'])', list_args)
            if a
        ]
        for t in clear_arg:
            t = t.replace(',', '').strip() if (t.startswith(',') or
                                               t.endswith(',')) else t
            if t.startswith('\'') or t.startswith('"'):
                args.append(t)
            else:
                try:
                    args.append(int(t))
                except ValueError:
                    try:
                        args.append(float(t))
                    except ValueError:
                        args.append(t)
    if list_kw:
        clear_kw = [
            k.strip() for k in re.split(
                r'([,*\s\w]*[=]\s*[\'|\"]*[\w\s=\'\"%]*[,\s\w]*[\'|\",])',
                list_kw) if k
        ]
        for t in clear_kw:
            t = t.replace(',', '').strip() if (t.startswith(',') or
                                               t.endswith(',')) else t
            if not t:
                continue
            k, v = [x.strip() for x in t.split('=', 1) if t]
            if function_wrong_symbols.search(k) or k.find(' ') != -1:
                raise ValueError('Invalid kwargs param')
            try:
                kw[k] = int(v)
            except ValueError:
                try:
                    kw[k] = float(v)
                except ValueError:
                    kw[k] = ''.join(list(v)[1:-1]) if \
                            ((v.__contains__('\'') or v.__contains__('"')) and \
                             list(v)[0] == list(v)[-1]) else v
    return name, args, kw
