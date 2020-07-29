"""
Extra mods required: sqlalchemy, msgpack (for KVStorage)
"""
import threading
import os
import datetime
from types import SimpleNamespace
from pyaltt2.crypto import gen_random_str
from pyaltt2.res import ResourceStorage
import pyaltt2.json as json
from functools import partial


def format_condition(f, kw=None, fields=None, cond=None):
    """
    Args:
        f: condition filter (dict name/value)
        kw: kwargs query dict
        fields: allowed fields
        cond: initial condition
    Returns:
        tuple cond (string), kw (dict). String can be safely used in SQL query,
        dict should be set as query kwargs
    """
    if kw is None:
        kw = {}
    else:
        kw = kw.copy()
    if fields is None:
        import re
        fmatch = re.compile('^[A-Za-z0-9\._-]*$')
    if cond is None:
        cond = ''
    for k, v in f.items():
        if (fields is None and
                not re.match(fmatch, k)) or (fields is not None and
                                             k not in fields):
            raise ValueError(k)
        eqs = ' is ' if v in (None, True, False) else '='
        if v is None:
            val = 'null'
        elif v is True:
            val = 'true'
        elif v is False:
            val = 'false'
        else:
            key = k.replace('.', '__').replace('-', '__')
            val = f':{key}'
            kw[key] = v
        if cond == '':
            cond = 'where '
        else:
            cond += ' and '
        cond += f'{k}{eqs}{val}'
    return cond, kw


class Database:
    """
    Database wrapper for SQLAlchemy
    """

    _clone_params = ('db', 'db_lock', 'g', 'rq_func')

    def __init__(self, dbconn=None, rq_func=None, **kwargs):
        """
        Args:
            dbconn: database connection string (for SQLite - only file name is
                required)
            rq_func: resource loader function (for query method)
            kwargs: additional engine options (ignored for SQLite)
        """
        if not dbconn:
            return
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
        self._setup()

    def clone(self, **kwargs):
        """
        Clone database object

        Extra kwargs (db, db_lock, g, rq_func) are assigned to object as-is
        """
        o = Database()
        for c in self._clone_params:
            setattr(o, c, kwargs[c] if c in kwargs else getattr(self, c))
        o._setup()
        return o

    def _setup(self):
        self.use_lastrowid = self.db.name in ['sqlite', 'mysql']
        self.use_interval = self.db.name not in ['sqlite', 'mysql']
        self.parse_db_json = self.db.name in ['sqlite', 'mysql']
        self.name = self.db.name

    def __repr__(self):
        return self.db.__repr__()

    def __str__(self):
        return self.db.__str__()

    def _format_result(self, result, json_fields=[]):
        if result is not None:
            result = dict(result)
            if self.parse_db_json:
                for f in json_fields:
                    result[f] = json.loads(result[f])
        return result

    def _format_list(self, result, json_fields=[]):
        if self.parse_db_json and json_fields:
            for row in result:
                for f in json_fields:
                    row[f] = json.loads(row[f])
        return result

    def get_engine(self):
        """
        Get DB engine object
        """
        return self.db

    def list(self, *args, json_fields=[], **kwargs):
        """
        get self.execute result as list of dicts

        Args:
            json_fields: decode json fields if required
            other: passed as-is
        """
        return self._format_list(
            [dict(row) for row in self.execute(*args, **kwargs).fetchall()],
            json_fields=json_fields)

    def qlist(self, *args, json_fields=[], **kwargs):
        """
        get self.query result as list of dicts

        Args:
            json_fields: decode json fields if required
            other: passed as-is
        """
        return self._format_list(
            [dict(row) for row in self.query(*args, **kwargs).fetchall()],
            json_fields=json_fields)

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

    def execute(self, *args, _cr=False, **kwargs):
        """
        Execute SQL query

        Args:
            _cr: check result, raise LookupError if row count is zero
            other: passed to SQLAlchemy connection as-is
        """
        result = self.connect().execute(*args, **kwargs)
        if _cr and result.rowcount == 0:
            raise LookupError
        else:
            return result

    def query(self, q, qargs=[], qkwargs={}, _create=False, *args, **kwargs):
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
        if _create and not self.use_lastrowid:
            q += ' RETURNING id'
        return self.execute(sql(q), *args, **kwargs)

    def create(self, q, *args, **kwargs):
        """
        Execute (usually INSERT) query with self.execute and return row id

        row id must be in "id" field
        """
        if not self.use_lastrowid:
            q += ' RETURNING id'
        result = self.execute(q, *args, **kwargs)
        return result.lastrowid if self.use_lastrowid else result.fetchone().id

    def qcreate(self, q, *args, **kwargs):
        """
        Execute (usually INSERT) query with self.query and return row id

        row id must be in "id" field
        """
        result = self.query(q, _create=True, *args, **kwargs)
        return result.lastrowid if self.use_lastrowid else result.fetchone().id

    def lookup(self, *args, json_fields=[], **kwargs):
        """
        Get single db row, use self.execute

        Args:
            json_fields: decode json fields if required
            other: passed as-is

        Returns:
            single row as a dict
        Raises:
            LookupError: if nothing found
        """
        result = self._format_result(self.execute(*args, **kwargs).fetchone(),
                                     json_fields=json_fields)
        if result:
            return result
        else:
            raise LookupError

    def qlookup(self, *args, json_fields=[], **kwargs):
        """
        Get single db row, use self.query

        Returns:
            single row as a dict
        Raises:
            LookupError: if nothing found
        """
        result = self._format_result(self.query(*args, **kwargs).fetchone(),
                                     json_fields=json_fields)
        if result:
            return result
        else:
            raise LookupError


class KVStorage:
    """
    Simple key-value database storage
    """

    def __init__(self, db, table_name='kv'):
        """
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
            if delete:
                self.delete(key)
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
