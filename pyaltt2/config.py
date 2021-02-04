"""
Extra mods required: pyyaml, jsonschema
"""
import yaml
import os

try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass


def load_yaml(fname, schema=None):
    """
    Load config from YAML/JSON file

    Args:
        fname: file name to load
        schema: JSON schema for validation
    """
    with open(fname) as fh:
        data = yaml.load(fh.read())
    if schema:
        import jsonschema
        jsonschema.validate(data, schema=schema)
    return data


def config_value(env=None,
                 config=None,
                 config_path=None,
                 to_str=False,
                 read_file='r',
                 in_place=False,
                 default=LookupError):
    """
    Get config value

    Args:
        env: search in system env, if specified, has top priority
        config: config dict to process
        config_path: config path (e.g. /some/long/key)
        to_str: strinify value before returning
        read_file: if value starts with '/', read it from file with mode
            (default: 'r')
        in_place: replace value in config dict
        default: default value
    Raises:
        LookupError: if value is not found and no default value specified
    """
    value = default
    if config_path is not None and config_path.startswith('/'):
        config_path = config_path[1:]
    if env is not None and env in os.environ:
        value = os.environ[env]
    if value is default or in_place and \
            (config is not None and config_path is not None):
        path = config_path.split('/')
        x = config
        for p in path[:-1]:
            if p not in x and in_place:
                x[p] = {}
            x = x.get(p, {})
        if value is default:
            if path[-1] in x:
                value = x[path[-1]]
    if value is LookupError:
        if env is None and config is not None and config_path is not None:
            msg = f'unable to find value of {config_path}'
        elif env is not None and (config is None or config_path is None):
            msg = f'OS variable {env} is not set'
        elif env is not None and config is not None and config_path is not None:
            msg = (f'unable to find value of {config_path}, '
                   f'OS variable {env} is not set as well')
        else:
            msg = None
        raise LookupError(msg)
    elif read_file and isinstance(value, str) and (value.startswith('/') or
                                                   value.startswith('./')):
        try:
            with open(str(value), read_file) as fh:
                value = fh.read()
        except:
            raise LookupError(f'Unable to read value from {str(value)}')
    elif to_str:
        value = str(value)
    if in_place:
        x[path[-1]] = value
    return value


def choose_file(fname=None, env=None, choices=[]):
    """
    Chooise existing file

    Returned file path is user-expanded

    Args:
        fname: if specified, has top priority and others are not chechked
        env: if specified and set, has second-top priority and choices are not
            inspected
        choices: if env is not set or not specified, choose existing file from
            the list
    Raises:
        LookupError: if file doesn't exists
    """
    if fname:
        fname = os.path.expanduser(fname)
        if os.path.exists(fname):
            return fname
        else:
            raise LookupError(f'No such file {fname}')
    elif env and env in os.environ:
        fname = os.path.expanduser(os.environ[env])
        if os.path.exists(fname):
            return fname
        else:
            raise LookupError(f'No such file {env} = {fname}')
    else:
        ch = []
        for c in choices:
            fname = os.path.expanduser(str(c))
            if os.path.exists(fname):
                return fname
            else:
                ch.append(fname)
        raise LookupError('File not found (tried {}{})'.format(
            env + (', ' if choices else '') if env else '', ', '.join(ch)))
