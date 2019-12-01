import threading
import logging

from functools import wraps

class Locker:
    """
    Function locker decorator object
    """

    def __init__(self, mod='', timeout=5, relative=True):
        """
        Args:
            mod: module to report in logs
            timeout: lock timeout (default: 5 sec)
            relative: use thread-relative locking (default: True)
        """
        self.lock = threading.RLock() if relative else threading.Lock()
        self.mod = '' if not mod else mod + '/'
        self.relative = relative
        self.timeout = timeout

    def __call__(self, f):

        @wraps(f)
        def do(*args, **kwargs):
            if not self.lock.acquire(timeout=self.timeout):
                logging.critical('{}{} locking broken'.format(
                    self.mod, f.__name__))
                self.critical()
                return None
            try:
                return f(*args, **kwargs)
            finally:
                self.lock.release()

        return do

    def critical(self):
        """
        Function is called when lock can not be obtained

        Empty by default, override or monkey-patch
        """
        pass
