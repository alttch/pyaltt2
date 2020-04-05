"""
Extra mods required: sqlalchemy, msgpack (for KVStorage)
"""
import threading
import os
import datetime
from types import SimpleNamespace
from pyaltt2.crypto import gen_random_str
from pyaltt2.res import ResourceStorage
from functools import partial


class Database:
    """
    Database wrapper for SQLAlchemy
    """

    def __init__(self, dbconn=None, rq_func=None, **kwargs):
        """
        Args:
            dbconn: database connection string (for SQLite - only file name is
                required)
            rq_func: resource loader function (for query method)
            kwargs: additional engine options (ignored for SQLite)
        """
        if not dbconn: return
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

    def clone(self):
        """
        Clone database object
        """
        o = Database()
        o.db = self.db
        o.db_lock = self.db_lock
        o.g = self.g
        o.rq_func = self.rq_func
        return o

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

        """
        return self.connect().execute(*args, **kwargs)

    def query(self, q, qargs=[], qkwargs={}, *args, **kwargs):
        """
        Execute SQL query by resource

        Args:
            q: resource name
            qargs, qkwargs: format query with args/kwargs
            other: passed as-is

        Requires rq_func
        """
        from sqlalchemy import text as sql
        q = self.rq_func(q)
        if qargs or qkwargs:
            q = q.format(*qargs, **qkwargs)
        return self.execute(sql(q), *args, **kwargs)

    def get_engine(self):
        """
        Get DB engine object
        """
        return self.db


class KVStorage:

    def __init__(self, db, table_name='kv'):
        """
        Simple key-value database storage

        Args:
            db: pyaltt2.db.Database
            table_name: storage table name (default: kv)
        """
        from sqlalchemy import (MetaData, Table, VARCHAR, DateTime, LargeBinary,
                                Column)
        if 'mysql' in db.get_engine().name:
            from sqlalchemy.dialects.mysql import DATETIME, LONGBLOB
            DateTime = partial(DATETIME, fsp=6)
            LargeBinary = LONGBLOB
        meta = MetaData()
        self.db = db.clone()
        rs = ResourceStorage(mod='pyaltt2')
        self.db.rq_func = partial(rs.get, resource_subdir='sql', ext='sql')
        self.table_name = table_name
        tbl = Table(table_name,
                    meta,
                    Column('id', VARCHAR(256), nullable=False,
                           primary_key=True),
                    Column('content', LargeBinary, nullable=True),
                    Column('d_expires', DateTime(timezone=True), nullable=True),
                    mysql_engine='InnoDB',
                    mysql_charset='utf8mb4')
        meta.create_all(db.connect(), tables=[tbl])

    def get(self, key, delete=False):
        """
        Get object from key-value storage

        Args:
            key: object key
            delete: delete object after getting
        Raises:
            LookupError: object not found
        """
        from msgpack import loads
        result = self.db.query('kv.get', qargs=[self.table_name],
                               id=key).fetchone()
        if result:
            if delete: self.delete(key)
            return loads(result.content, raw=False)
        else:
            raise LookupError

    def put(self, key=None, value=None, expires=None, override=True):
        """
        Put object to key-value storage

        If no key specified, random 64-char key is generated

        Args:
            key: string key (1-255 chars)
            value: value to put
            expires: expiration either in seconds or datetime.timedelta
            override: replace existing object
        Returns:
            object key
        """
        from msgpack import dumps
        if key is None:
            key = gen_random_str(length=64)
        elif override:
            try:
                self.delete(key)
            except LookupError:
                pass
        value = dumps(value)
        if expires is None:
            self.db.query('kv.put',
                          qargs=[self.table_name],
                          id=key,
                          content=value)
        else:
            d_expires = datetime.datetime.now() + datetime.timedelta(
                seconds=expires) if isinstance(
                    expires, int) else datetime.datetime.now() + expires
            self.db.query('kv.put.expires',
                          qargs=[self.table_name],
                          id=key,
                          content=value,
                          d_expires=d_expires)
        return key

    def delete(self, key):
        """
        Delete object in key-value storage

        Args:
            key: object key
        Raises:
            LookupError: object not found
        """
        if not self.db.query('kv.delete', qargs=[self.table_name],
                             id=key).rowcount:
            raise LookupError

    def cleanup(self):
        """
        Deletes expired objects
        """
        self.db.query('kv.cleanup',
                      qargs=[self.table_name],
                      d=datetime.datetime.now())
