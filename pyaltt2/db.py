"""
Thread-safe SQLAlchemy wrapper

Extra mods required: sqlalchemy
"""
import threading
import os
from types import SimpleNamespace


class Database:

    def __init__(self, dbconn, rq_func=None, **kwargs):
        """
        Args:
            dbconn - database connection string (for SQLite - file name is
            allowed)
            rq_func: resource loader function (for query method)
            kwargs: additional engine options (ignored for SQLite)
        """
        import sqlalchemy as sa

        class _ForeignKeysListener(sa.interfaces.PoolListener):

            def connect(self, dbapi_con, con_record):
                try:
                    dbapi_con.execute('pragma foreign_keys=ON')
                except:
                    pass

        self.db_lock = threading.RLock()
        self.g = threading.local()
        self.rq_func = rq_func
        if dbconn.find('://') == -1:
            dbconn = 'sqlite:///' + os.path.expanduser(dbconn)
        if dbconn.startswith('sqlite:///'):
            self.db = sa.create_engine(dbconn,
                                       listeners=[_ForeignKeysListener()])
        else:
            self.db = sa.create_engine(dbconn, **kwargs)

    def get_list(self, *args, **kwargs):
        """
        get database result as list of dicts

        arguments are passed as-is to SQLAlchemy execute function
        """
        return [dict(row) for row in self.execute(*args, **kwargs).fetchall()]

    def connect(self):
        """
        Get thread-safe db connection
        """
        with self.db_lock:
            try:
                self.g.conn.execute('select 1')
                return self.g.conn
            except:
                self.g.conn = self.db.connect()
                return self.g.conn

    def execute(self, *args, **kwargs):
        """
        Execute SQL query

        Arguments are passed as-is

        Requires rq_func
        """
        return self.connect().execute(*args, **kwargs)

    def query(self, q, *args, **kwargs):
        from sqlalchemy import text as sql
        return self.execute(sql(self.rq_func(q)), *args, **kwargs)

    def get_engine(self):
        """
        Get DB engine object
        """
        return self.db
