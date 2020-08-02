#!/usr/bin/env python3

from pathlib import Path
import sys
import logging
import time
from neotasker import task_supervisor

task_supervisor.start()
task_supervisor.create_aloop('cleaners')

sys.path.insert(0, Path().absolute().parent.as_posix())

import pyaltt2.logs

pyaltt2.logs.CLEAN_INTERVAL = 0.5

log_file = None
# log_file='test.log'

pyaltt2.logs.init(name=__file__,
                  log_file=log_file,
                  level=30,
                  keep_logmem=2,
                  keep_exceptions=10,
                  tracebacks=True)
# pyaltt2.logs.config.colorize=False

pyaltt2.logs.start(loop='cleaners')


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
        pyaltt2.logs.log_traceback()
pyaltt2.logs.set_debug(True)
test_logging()
import os
import signal
pyaltt2.logs.set_debug(False)
os.system('mv test.log test.log.1')
test_logging()
assert len(pyaltt2.logs.serialize()['exceptions']) == 10
print('Completed')
from pprint import pprint
pyaltt2.logs.set_debug(True)
for a in range(5):
    pprint(pyaltt2.logs.get(level=10))
    time.sleep(1)
# pyaltt2.logs.stop()
task_supervisor.stop()
