"""
Requires neotermcolor
"""
import logging
import platform
import neotermcolor

from .network import parse_host_port

from types import SimpleNamespace

config = SimpleNamespace(
        log_file=None, # log file to write to
        level=10,
        tracebacks=False, # log exception tracebacks
        ignore=None, # ignore symbol
        stdout_ignore=True, # use ignore symbol for stdout
        colorize=True, # colorize STDOUT records if possible
        formatter = logging.Formatter('%(asctime)s ' + platform.node() + \
            ' %(levelname)s f:%(filename)s mod:%(module)s fn:%(funcName)s ' + \
            'l:%(lineno)d th:%(threadName)s :: %(message)s')
        )

__data = SimpleNamespace(logger=None, log_file_handler=None)


class StdoutHandler(logging.StreamHandler):

    def emit(self, record):
        if not config.stdout_ignore or \
                config.ignore is None or \
                not record.getMessage().startswith(config.ignore):
            super().emit(record)

    def format(self, record):
        if config.colorize:
            r = super().format(record)
            return neotermcolor.colored(r,
                                        style='logger:{}'.format(
                                            record.levelno))
        else:
            return super().format(record)


def log_traceback():
    # TODO
    pass


def set_debug(debug=False):
    # TODO
    pass


def sighandler_hup(signum, frame):
    try:
        if reset():
            logging.info('log file rotated')
    except:
        log_traceback()


def reset(_initial=False):
    if config.log_file:
        try:
            __data.log_file_handler.stream.close()
        except:
            pass
        if not _initial:
            __data.logger.removeHandler(__data.log_file_handler)
        __data.log_file_handler = logging.FileHandler(config.log_file)
        __data.log_file_handler.setFormatter(config.formatter)
        __data.logger.addHandler(__data.log_file_handler)
        return True
    else:
        return False


def init(log_file=None,
         level=30,
         syslog=None,
         keep_logmem=0,
         register_sighup=True):
    """
    """
    logging.basicConfig(level=level)
    config.level = level

    neotermcolor.set_style('logger:10', color='grey', attrs='bold')
    neotermcolor.set_style('logger:20')
    neotermcolor.set_style('logger:30', color='yellow')
    neotermcolor.set_style('logger:40', color='red')
    neotermcolor.set_style('logger:50', color='red', attrs='bold')

    __data.logger = logging.getLogger()
    for h in __data.logger.handlers:
        __data.logger.removeHandler(h)
    if log_file:
        config.log_file = log_file
    if config.log_file:
        reset(_initial=True)
    else:
        __data.log_file_handler = StdoutHandler()
        __data.log_file_handler.setFormatter(config.formatter)
        __data.logger.addHandler(__data.log_file_handler)
    if register_sighup:
        import signal
        signal.signal(signal.SIGHUP, sighandler_hup)
    # TODO: syslog and memory handler
