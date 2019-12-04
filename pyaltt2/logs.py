"""
Requires neotermcolor

neotermcolor styles:

- logger:10 - debug log message
- logger:20 - info log message
- logger:30 - warning log message
- logger:40 - error log message
- logger:50 - critical log message
- logger:exception - exceptions, printed to stdout (w/o logging)

Keeping records in memory requires atasker library
"""
import logging
import logging.handlers
import platform
import neotermcolor
import threading
import time

from .network import parse_host_port

from types import SimpleNamespace

_exceptions = []

_exception_log_lock = threading.RLock()

config = SimpleNamespace(
        log_file=None,
        log_stdout=2,
        syslog=None,
        level=20,
        tracebacks=False, # log exception tracebacks
        ignore=None, # ignore symbol
        stdout_ignore=True, # use ignore symbol for stdout
        keep_logmem=0,
        keep_exceptions=0, # keep number of exceptions
        colorize=True, # colorize STDOUT records if possible
        formatter = logging.Formatter('%(asctime)s ' + platform.node() + \
            ' %(levelname)s f:%(filename)s mod:%(module)s fn:%(funcName)s ' + \
            'l:%(lineno)d th:%(threadName)s :: %(message)s'),
        syslog_formatter = None
        )

__data = SimpleNamespace(logger=None)

neotermcolor.set_style('logger:10', color='grey', attrs='bold')
neotermcolor.set_style('logger:20')
neotermcolor.set_style('logger:30', color='yellow')
neotermcolor.set_style('logger:40', color='red')
neotermcolor.set_style('logger:50', color='red', attrs='bold')

neotermcolor.set_style('logger:exception', color='red')


class StdoutHandler(logging.StreamHandler):

    def emit(self, record):
        if not config.stdout_ignore or \
                config.ignore is None or \
                not record.getMessage().startswith(config.ignore):
            super().emit(record)

    def format(self, record):
        r = super().format(record)
        return neotermcolor.colored(r, style='logger:{}'.format(
            record.levelno)) if config.colorize else r


class DummyHandler(logging.StreamHandler):

    def emit(self, record):
        pass


def log_traceback(display=False, use_ignore=False, force=False):
    """
    Log exception traceback

    Args:
        display: display traceback instead of logging
        use_ignore: use ignore symbol for traceback string
        force: force log, even if tracebacks are disabled
    """
    import traceback
    e_msg = traceback.format_exc()
    if (config.tracebacks or force) and not display:
        pfx = config.ignore if use_ignore and config.ignore else ''
        logging.error(pfx + e_msg)
    elif display:
        print(colored(e_msg, style='logger:exception'))
    if config.keep_exceptions:
        with _exception_log_lock:
            e = {'t': time.strftime('%Y-%m-%d %H:%M:%S,%f %z'), 'e': e_msg}
            _exceptions.append(e)
            if len(_exceptions) > config.keep_exceptions:
                del _exceptions[0]


def set_debug(debug=False):
    """
    Set debug mode ON/OFF

    Args:
        debug: True = ON, False = OFF
    """
    level = 10 if debug else config.level
    logging.basicConfig(level=level)
    if __data.logger:
        __data.logger.setLevel(level)


def serialize():
    """
    Get dict with internal data
    """
    with _exception_log_lock:
        return {'exceptions': _exceptions.copy()}


def init(**kwargs):
    """
    Initialize logger

    Args:
        log_file: file to log to
        log_stdout: 0 - do not log, 1 - log, 2 - log auto (if no more log hdlrs)
        syslog: True for /dev/log, socket path or host[:port]
        level: log level (default: 20)
        tracebacks: log tracebacks (default: False)
        ignore: use "ignore" symbol - memory hdlr ignores records starting with
        stdout_ignore: use "ignore" symbol in stdout logger as well
        keep_logmem: keep log records in memory for the specified time (seconds)
        keep_exceptions: keep number of recent exceptions
        colorize: colorize stdout if possible
        formatter: log formatter
        syslog_formatter: if defined, use custom formatter for syslog
    """
    for k, v in kwargs.items():
        if not hasattr(config, k):
            raise AttributeError('Invalid argument: {}'.format(k))
        setattr(config, k, v)

    logging.basicConfig(level=config.level)

    __data.logger = logging.getLogger()
    for h in __data.logger.handlers:
        __data.logger.removeHandler(h)
    has_handler = False
    if config.log_file:
        has_handler = True
        file_handler = logging.handlers.WatchedFileHandler(config.log_file)
        file_handler.setFormatter(config.formatter)
        __data.logger.addHandler(file_handler)
    # TODO: memory handler
    if config.syslog:
        has_handler = True
        if config.syslog is True:
            syslog_addr = '/dev/log'
        elif config.syslog.startswith('/'):
            syslog_addr = config.syslog
        else:
            addr, port = parse_host_port(config.syslog, 514)
            if addr:
                syslog_addr = (addr, port)
            else:
                logging.error('Invalid syslog configuration: {}'.format(
                    config.syslog))
                syslog_addr = None
        if syslog_addr:
            syslog_handler = logging.handlers.SysLogHandler(address=syslog_addr)
            syslog_handler.setFormatter(config.syslog_formatter if config.
                                        syslog_formatter else config.formatter)
            __data.logger.addHandler(syslog_handler)
    if (not has_handler and config.log_stdout == 2) or \
            config.log_stdout is True or config.log_stdout == 1:
        has_handler = True
        stdout_handler = StdoutHandler()
        stdout_handler.setFormatter(config.formatter)
        __data.logger.addHandler(stdout_handler)
    if not has_handler:
        # mute all logs
        __data.logger.addHandler(DummyHandler())
