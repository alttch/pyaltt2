"""
Thread-safe SQLAlchemy wrapper
"""
import threading
import os
import sqlalchemy as sa
from types import SimpleNamespace

db_lock = threading.RLock()
g = threading.local()

_d = SimpleNamespace()


def get_list(*args, **kwargs):
    """
    get database result as list of dicts

    arguments are passed as-is to SQLAlchemy execute function
    """
    return [dict(row) for row in get_db().execute(*args, **kwargs).fetchall()]


def get_db():
    """
    Get thread-safe db connection
    """
    with db_lock:
        try:
            g.conn.execute('select 1')
            return g.conn
        except:
            g.conn = _d.db.connect()
            return g.conn


def get_engine():
    """
    Get DB engine object
    """
    return _d.db


def create_engine(dbconn, **kwargs):
    """
    Args:
        dbconn - database connection string (for SQLite - file name is
        allowed)
        kwargs: additional engine options (ignored for SQLite)
    """

    class _ForeignKeysListener(sa.interfaces.PoolListener):

        def connect(self, dbapi_con, con_record):
            try:
                dbapi_con.execute('pragma foreign_keys=ON')
            except:
                pass

    if dbconn.find('://') == -1:
        dbconn = 'sqlite:///' + os.path.expanduser(dbconn)
    if dbconn.startswith('sqlite:///'):
        _d.db = sa.create_engine(dbconn, listeners=[_ForeignKeysListener()])
    else:
        _d.db = sa.create_engine(dbconn, **kwargs)
    return _d.db
