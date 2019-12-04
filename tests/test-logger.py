#!/usr/bin/env python3

from pathlib import Path
import sys
import logging

sys.path.insert(0, Path().absolute().parent.as_posix())

import pyaltt2.logger

log_file = None
# log_file='test.log'

pyaltt2.logger.init(log_file=log_file,
                    level=30,
                    keep_exceptions=10,
                    tracebacks=True)
# pyaltt2.logger.config.colorize=False


def test_logging():
    logging.debug('this is a DEBUG record')
    logging.info('this is an INFO record')
    logging.warning('this is a WARNING record')
    logging.error('this is an ERROR record')
    logging.critical('this is a CRITICAL record')


for i in range(11):
    try:
        raise ValueError('test')
    except:
        pyaltt2.logger.log_traceback()
pyaltt2.logger.set_debug(True)
test_logging()
import os
import signal
pyaltt2.logger.set_debug(False)
os.system('mv test.log test.log.1')
test_logging()
assert len(pyaltt2.logger.serialize()['exceptions']) == 10
print('Completed')
