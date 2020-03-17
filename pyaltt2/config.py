import yaml
import os

try:
    yaml.warnings({'YAMLLoadWarning': False})
except:
    pass


def load_yaml(fname):
    """
    Load config from YAML/JSON file
    """
    with open(fname) as fh:
        return yaml.load(fh.read())


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
    """
    value = default
    if env is not None and env in os.environ:
        value = os.environ[env]
    if value is default or in_place and \
            (config is not None and config_path is not None):
        path = config_path.split('/')
        x = config
        for p in path[:-1] if path[0] != '' else path[1:-1]:
            if p not in x and in_place:
                x[p] = {}
            x = x.get(p, {})
        if value is default:
            if path[-1] in x:
                value = x[path[-1]]
    if value is LookupError:
        raise LookupError
    elif read_file and isinstance(value, str) and (value.startswith('/') or
                                                   value.startswith('./')):
        with open(str(value), read_file) as fh:
            value = fh.read()
    elif to_str:
        value = str(value)
    if in_place:
        x[path[-1]] = value
    return value
