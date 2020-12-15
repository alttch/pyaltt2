"""
Requires neotermcolor

neotermcolor styles:

- logger:10 - debug log message
- logger:20 - info log message
- logger:30 - warning log message
- logger:40 - error log message
- logger:50 - critical log message
- logger:exception - exceptions, printed to stdout (w/o logging)

Keeping records in memory requires neotasker library
"""
import logging
import logging.handlers
import platform
import neotermcolor
import threading
import time
import datetime
import types

from .network import parse_host_port

from types import SimpleNamespace

try:
    import rapidjson as json
except:
    import json

DEFAULT_LOG_GET = 100
MAX_LOG_GET = 10000

CLEAN_INTERVAL = 60

_exceptions = []

_log_records = []

_exception_log_lock = threading.RLock()
_log_record_lock = threading.RLock()

logger = logging.getLogger('pyaltt2.logs')

try:
    import pytz
    LOCAL_TZ = pytz.timezone(time.tzname[0])
except:
    logger.warning(
        'Unable to determine local time zone, is pytz module installed?')
    LOCAL_TZ = None


config = SimpleNamespace(
        name='',
        host=platform.node(),
        log_file=None,
        log_stdout=2,
        syslog=None,
        level=20,
        tracebacks=False,
        ignore=None,
        ignore_mods = [],
        stdout_ignore=True,
        keep_logmem=0,
        keep_exceptions=0,
        colorize=True,
        formatter = logging.Formatter('%(asctime)s ' + platform.node() + \
            ' %(levelname)s f:%(filename)s mod:%(module)s fn:%(funcName)s ' + \
            'l:%(lineno)d th:%(threadName)s :: %(message)s'),
        syslog_formatter = None,
        log_json=False,
        syslog_json=False
        )

__data = SimpleNamespace(logger=None, cleaner=None)

neotermcolor.set_style('logger:10', color='grey', attrs='bold')
neotermcolor.set_style('logger:20')
neotermcolor.set_style('logger:30', color='yellow')
neotermcolor.set_style('logger:40', color='red')
neotermcolor.set_style('logger:50', color='red', attrs='bold')

neotermcolor.set_style('logger:exception', color='red')


def _getJSONMessage(self):
    msg = str(self.msg)
    if self.args:
        msg = msg % self.args
    return json.dumps(msg)[1:-1]


class JSysLogHandler(logging.handlers.SysLogHandler):

    def __init__(self, *args, as_json=False, **kwargs):
        self.as_json = as_json
        super().__init__(*args, **kwargs)

    def emit(self, record):
        if self.as_json:
            record.getMessage = types.MethodType(_getJSONMessage, record)
        super().emit(record)


class JWatchedFileHandler(logging.handlers.WatchedFileHandler):

    def __init__(self, *args, as_json=False, **kwargs):
        self.as_json = as_json
        super().__init__(*args, **kwargs)

    def emit(self, record):
        if self.as_json:
            record.getMessage = types.MethodType(_getJSONMessage, record)
        super().emit(record)


class StdoutHandler(logging.StreamHandler):

    def __init__(self, as_json=False):
        self.as_json = as_json
        super().__init__()

    def emit(self, record):
        if not config.stdout_ignore or \
                ((config.ignore is None or \
                    not record.getMessage().startswith(config.ignore)) and \
                    record.module not in config.ignore_mods):
            if self.as_json:
                record.getMessage = types.MethodType(_getJSONMessage, record)
            super().emit(record)

    def format(self, record):
        r = super().format(record)
        return neotermcolor.colored(
            r, style='logger:' + str(record.levelno)) if config.colorize else r


def append(record=None, rd=None, **kwargs):
    """
    Append log record to memory cache

    Args:
        record: log record, or
        rd: log record in dict format
        **kwargs: passed to handle_append as-is
    """
    if record:
        r = {
            't': record.created,
            'msg': record.getMessage(),
            'l': record.levelno,
            'th': record.threadName,
            'mod': record.module,
            'h': config.host,
            'p': config.name
        }
    elif rd:
        r = rd
    else:
        return
    if r['msg'] and (not config.ignore or r['msg'][0] != config.ignore) and \
            r['mod'] not in config.ignore_mods:
        if LOCAL_TZ:
            r['dt'] = datetime.datetime.fromtimestamp(
                r['t']).replace(tzinfo=LOCAL_TZ).isoformat()
        with _log_record_lock:
            _log_records.append(r)
        handle_append(r, **kwargs)


def handle_append(rd, **kwargs):
    """
    Called after record is appended

    Args:
        rd: log record in dict format
        **kwargs: got from append as-is
    """


def get(level=0, t=0, n=None):
    """
    Get recent log records

    Args:
        level: minimal log level
        t: get entries for the recent t seconds
        n: max number of log records (default: 100)
    """
    lr = []
    if n is None:
        n = DEFAULT_LOG_GET
    if n > MAX_LOG_GET:
        n = MAX_LOG_GET
    t = time.time() - t if t else 0
    ll = 0 if level is None else level
    with _log_record_lock:
        recs = reversed(_log_records)
    for r in recs:
        if r['t'] > t and r['l'] >= ll:
            lr.append(r)
            if len(lr) >= n:
                break
    return list(reversed(lr))


async def clean(**kwargs):
    """
    Clean obsolete log records from memory

    Usually executed from log cleaner worker (see "start")
    """
    logger.debug('Cleaning logs')
    with _log_record_lock:
        recs = _log_records.copy()
    for l in recs:
        if time.time() - l['t'] > config.keep_logmem:
            with _log_record_lock:
                try:
                    _log_records.remove(l)
                except:
                    log_traceback()


class MemoryLogHandler(logging.Handler):

    def emit(self, record):
        append(record)


class DummyHandler(logging.StreamHandler):

    def emit(self, record):
        pass


def log_traceback(display=False, use_ignore=False, force=False, e=None):
    """
    Log exception traceback

    Args:
        display: display traceback instead of logging
        use_ignore: use ignore symbol for traceback string
        force: force log, even if tracebacks are disabled
        e: exception or exc_info to log (optional)
    """
    import traceback
    if e is None:
        e_msg = traceback.format_exc()
    elif isinstance(e, tuple):
        e_msg = ''.join(traceback.format_exception(*e))
    else:
        e_msg = str(e)
    if (config.tracebacks or force) and not display:
        pfx = config.ignore if use_ignore and config.ignore else ''
        logging.error(pfx + e_msg)
    elif display:
        print(neotermcolor.colored(e_msg, style='logger:exception'))
    if config.keep_exceptions:
        with _exception_log_lock:
            e = {
                't': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f'),
                'e': e_msg
            }
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
        name: software product name
        host: custom host name
        log_file: file to log to
        log_stdout: 0 - do not log, 1 - log, 2 - log auto (if no more log hdlrs)
        syslog: True for /dev/log, socket path or host[:port]
        level: log level (default: 20)
        tracebacks: log tracebacks (default: False)
        ignore: use "ignore" symbol - memory hdlr ignores records starting with
        ignore_mods: list of modules to ignore
        stdout_ignore: use "ignore" symbol in stdout logger as well
        keep_logmem: keep log records in memory for the specified time (seconds)
        keep_exceptions: keep number of recent exceptions
        colorize: colorize stdout if possible
        formatter: log formatter
        syslog_formatter: if defined, use custom formatter for syslog
        log_json: true/false
        syslog_json: true/false
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
        handler = JWatchedFileHandler(config.log_file, as_json=config.log_json)
        handler.setFormatter(config.formatter)
        __data.logger.addHandler(handler)
    if config.keep_logmem:
        handler = MemoryLogHandler()
        __data.logger.addHandler(handler)
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
            handler = JSysLogHandler(address=syslog_addr,
                                     as_json=config.syslog_json)
            handler.setFormatter(config.syslog_formatter if config.
                                 syslog_formatter else config.formatter)
            __data.logger.addHandler(handler)
    if (not has_handler and config.log_stdout == 2) or \
            config.log_stdout is True or config.log_stdout == 1:
        has_handler = True
        handler = StdoutHandler(as_json=config.log_json)
        handler.setFormatter(config.formatter)
        __data.logger.addHandler(handler)
    if not has_handler:
        # mute all logs
        __data.logger.addHandler(DummyHandler())


def start(loop=None):
    """
    Start log cleaner

    Requires neotasker module, task supervisor must be started before

    Args:
        loop: neotasker async loop to execute cleaner worker in
    """
    import neotasker
    __data.cleaner = neotasker.BackgroundIntervalWorker(
        name='pyaltt2:logs:cleaner', delay=CLEAN_INTERVAL, loop=loop)
    __data.cleaner.run = clean
    __data.cleaner.start()


def stop():
    """
    Optional method to stop log cleaner
    """
    if __data.cleaner:
        __data.cleaner.stop()
