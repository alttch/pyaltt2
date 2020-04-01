"""
JSON processing and output functions

Automatically imports rapidjson if present
"""
import sys

try:
    import rapidjson as json
except:
    import json

loads = json.loads


def dumps(data, pretty=False, unpicklable=False, pickle_opts={}, **kwargs):
    """
    Dump to JSON

    Args:
        data: data to dump
        pretty: set indent and sort keys
        unpicklable: one-way dump for complex objects (requires jsonpickle)
        pickle_opts: sent to jsonpickle.encode() as-is
        **kwargs: sent to json.dumps() as-is
    """
    if unpicklable:
        import jsonpickle
        data = json.loads(
            jsonpickle.encode(data, unpicklable=True, **pickle_opts))
    return json.dumps(data, indent=4, sort_keys=True, **
                      kwargs) if pretty else json.dumps(data, **kwargs)


def jprint(data, colored=True, force_colored=False, file=None):
    """
    Pretty print JSON

    Args:
        data: data to encode and print
        colored: colorize output (default: True)
        force_colored: force colorize, even if stream is not a tty
        file: output stream (default: sys.stdout)
    """
    j = dumps(data, pretty=True, unpicklable=True)
    if file is None: file = sys.stdout
    if colored and (file.isatty() or force_colored):
        from pygments import highlight, lexers, formatters
        j = highlight(j, lexers.JsonLexer(), formatters.TerminalFormatter())
    print(j, file=file)
