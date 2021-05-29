#!/usr/bin/env pytest

from pathlib import Path
import sys
import os
import pytest
import logging
import time

sys.path.insert(0, Path().absolute().parent.as_posix())

import pyaltt2.crypto
import pyaltt2.locker
import pyaltt2.network
import pyaltt2.converters
import pyaltt2.lp
import pyaltt2.json
import pyaltt2.config
import pyaltt2.res
import pyaltt2.db

from types import SimpleNamespace

from functools import partial


def test_cond():
    cond, kw = pyaltt2.db.format_condition({'a': 2, 'b': True, 'c': '99'})
    assert cond == 'where a=:a and b is true and c=:c'
    assert kw == {'a': 2, 'c': '99'}
    cond, kw = pyaltt2.db.format_condition({
        'a': 2,
        'b': True,
        'c': '99'
    },
                                           fields=['a', 'b', 'c'])
    assert cond == 'where a=:a and b is true and c=:c'
    assert kw == {'a': 2, 'c': '99'}
    cond, kw = pyaltt2.db.format_condition({
        'a': 2,
        'b': None,
        'c': '99'
    },
                                           fields=['a', 'b', 'c'],
                                           cond='where z is null')
    assert cond == 'where z is null and a=:a and b is null and c=:c'
    assert kw == {'a': 2, 'c': '99'}
    with pytest.raises(ValueError):
        cond, kw = pyaltt2.db.format_condition({
            'a': 2,
            'b': True,
            'c': '99'
        },
                                               fields=['a', 'b'])
    with pytest.raises(ValueError):
        cond, kw = pyaltt2.db.format_condition({'a;y': 2, 'b': True, 'c': '99'})
    cond, kw = pyaltt2.db.format_condition({'a.x': 2, 'b': True, 'c': '99'})
    assert cond == 'where a.x=:a__x and b is true and c=:c'
    assert kw == {'a__x': 2, 'c': '99'}
    cond, kw = pyaltt2.db.format_condition({
        'a': 2,
        'b': True,
        'c': '99'
    },
                                           fields=['a', 'b', 'c'])
    assert cond == 'where a=:a and b is true and c=:c'
    assert kw == {'a': 2, 'c': '99'}


def test_db():
    try:
        try:
            os.unlink('/tmp/pyaltt2-test.db')
        except FileNotFoundError:
            pass
        db = pyaltt2.db.Database('/tmp/pyaltt2-test.db')
        for t in ['t1', 't2' 'kv']:
            try:
                db.execute(f'DROP TABLE {t}')
            except:
                pass
        db.execute('CREATE TABLE t1 (id INTEGER)')
        db.execute('CREATE TABLE t2 (id INTEGER PRIMARY KEY '
                   'AUTOINCREMENT, name varchar(10))')
        db.execute('INSERT INTO t1 VALUES (2)')
        db.execute('INSERT INTO t1 VALUES (3)')
        assert db.lookup('SELECT * FROM t1 WHERE id=2')['id'] == 2
        with pytest.raises(LookupError):
            db.lookup('SELECT * FROM t1 WHERE id=999')
        db.execute('DELETE FROM t1 WHERE id=999')
        with pytest.raises(LookupError):
            db.execute('DELETE FROM t1 WHERE id=999', _cr=True)
        id1 = db.create("INSERT INTO t2(name) VALUES ('test1')")
        id2 = db.create("INSERT INTO t2(name) VALUES ('test2')")
        assert db.lookup("SELECT * FROM t2 WHERE id=:id",
                         id1)['name'] == 'test1'
        assert db.lookup("SELECT * FROM t2 WHERE id=:id",
                         id2)['name'] == 'test2'
        kv = pyaltt2.db.KVStorage(db=db)
        kv.put('test', 123)
        assert kv.get('test') == 123
        assert kv.get('test', delete=True) == 123
        with pytest.raises(LookupError):
            kv.get('test')
        key = kv.put(value={'a': 2, 'b': 3}, expires=0)
        assert kv.get(key)['a'] == 2
        kv.put(key, {'a': 5, 'b': 8}, expires=0)
        assert kv.get(key)['a'] == 5
        assert kv.get(key)['b'] == 8
        kv.cleanup()
        db.clone()
        with pytest.raises(LookupError):
            kv.get(key)
    finally:
        os.unlink('/tmp/pyaltt2-test.db')


def test_res():
    rs1 = pyaltt2.res.ResourceStorage('./rtest/resources')
    rs2 = pyaltt2.res.ResourceStorage(mod='rtest')
    with pytest.raises(LookupError):
        rs3 = pyaltt2.res.ResourceStorage(mod='rtestxxx')
    for rs in [rs1, rs2]:
        assert rs.get('txt.1', ext='txt') == '1'
        assert rs.get('txt/1', ext='txt') == '1'
        assert rs.get('txt/1.txt') == '1'
        assert rs.get('2', resource_subdir='txt', ext='txt') == '2'
        assert rs.get(
            '3',
            resource_subdir='txt',
        ) == '3'
        assert rs.get('txt.3') == '3'
        assert rs.get('txt.3', mode='rb') == b'3'

        rsql = partial(rs.get, resource_subdir='sql', ext='sql')

        assert rsql('select.select.something').strip() == 'SELECT'
        assert rsql('insert.insert.something').strip() == 'INSERT'
        assert rsql('update.update.something').strip() == 'UPDATE'
        with pytest.raises(LookupError):
            assert rsql('delete.update.something').strip() == 'UPDATE'
        assert rsql('delete.update.something', default='XXX').strip() == 'XXX'


def test_load_config():
    config = pyaltt2.config.load_yaml('test_data/config.yml')
    assert config['data']['test'] == 'value1'
    assert config['data']['test2'] == 123
    SCHEMA = {
        'type': 'object',
        'properties': {
            'data': {
                'type': 'object',
                'properties': {
                    'test': {
                        'type': 'string'
                    },
                    'test2': {
                        'type': 'integer',
                        'minimum': 1
                    }
                },
                'additionalProperties': False,
                'required': ['test', 'test2']
            }
        }
    }
    config = pyaltt2.config.load_yaml('test_data/config.yml', schema=SCHEMA)
    assert config['data']['test'] == 'value1'
    assert config['data']['test2'] == 123
    SCHEMA = {
        'type': 'object',
        'properties': {
            'data': {
                'type': 'object',
                'properties': {
                    'test': {
                        'type': 'string'
                    },
                    'test2': {
                        'type': 'integer',
                        'minimum': 1
                    }
                },
                'additionalProperties': False,
                'required': ['test', 'test2', 'test3']
            }
        }
    }
    from jsonschema.exceptions import ValidationError
    with pytest.raises(ValidationError):
        config = pyaltt2.config.load_yaml('test_data/config.yml', schema=SCHEMA)


def test_choose_file():
    os.environ['TEST_FILE'] = 'test_data/file1'
    os.environ['TEST_FILE_NF'] = 'test_data/filex'
    assert pyaltt2.config.choose_file(
        env='TEST_FILE', choices=['test_data/file2',
                                  'test_data/filex']) == 'test_data/file1'
    with pytest.raises(LookupError):
        pyaltt2.config.choose_file(
            env='TEST_FILE_NF', choices=['test_data/file2', 'test_data/filex'])
    with pytest.raises(LookupError):
        pyaltt2.config.choose_file(
            env='TEST_FILE_NFX',
            choices=['test_data/filexx', 'test_data/filex'])
    assert pyaltt2.config.choose_file(
        env='TEST_FILE_NFX', choices=['test_data/filexx',
                                      'test_data/file2']) == 'test_data/file2'
    assert pyaltt2.config.choose_file(
        choices=['test_data/file1', 'test_data/file2']) == 'test_data/file1'
    with pytest.raises(LookupError):
        pyaltt2.config.choose_file(
            choices=['test_data/filex', 'test_data/filexx'])
    with pytest.raises(LookupError):
        assert pyaltt2.config.choose_file(
            'test_data/filex', choices=['test_data/file1', 'test_data/file2'])
    assert pyaltt2.config.choose_file(
        'test_data/file3', choices=['test_data/file1',
                                    'test_data/file2']) == 'test_data/file3'


def test_config_value():
    config = {'somedata': {'somekey': 123}}
    assert pyaltt2.config.config_value(config=config,
                                       config_path='/somedata/somekey') == 123
    assert pyaltt2.config.config_value(config=config,
                                       config_path='/somedata/somekey',
                                       to_str=True) == '123'
    with pytest.raises(LookupError):
        pyaltt2.config.config_value(config=config,
                                    config_path='/somedata/somekey2')
    os.environ['TEST_VALUE'] = '456'
    os.environ['TEST_VALUE_F'] = './test_data/file1'
    os.environ['TEST_VALUE_NF'] = './test_data/filex'
    assert pyaltt2.config.config_value(env='TEST_VALUE2',
                                       config=config,
                                       config_path='/somedata/somekey') == 123
    assert pyaltt2.config.config_value(env='TEST_VALUE',
                                       config=config,
                                       config_path='/somedata/somekey') == '456'
    assert pyaltt2.config.config_value(env='TEST_VALUE2',
                                       config=config,
                                       config_path='/somedata/somekey2',
                                       default='xxx') == 'xxx'
    assert pyaltt2.config.config_value(env='TEST_VALUE_F',
                                       config=config,
                                       config_path='/somedata/somekey2',
                                       default='xxx') == '1'
    with pytest.raises(LookupError):
        pyaltt2.config.config_value(env='TEST_VALUE_NF',
                                    config=config,
                                    config_path='/somedata/somekey2',
                                    default='xxx')
    assert pyaltt2.config.config_value(env='TEST_VALUE_F',
                                       read_file=None,
                                       config=config,
                                       config_path='/somedata/somekey2',
                                       default='xxx') == './test_data/file1'
    pyaltt2.config.config_value(env='TEST_VALUE_F',
                                config=config,
                                in_place=True,
                                config_path='/somedata/somekey2',
                                default='xxx')
    assert config['somedata']['somekey2'] == '1'


def test_config():
    cfg = pyaltt2.config.Config({
        'a': 2,
        'b': {
            'c': '123'
        },
        'd': {
            'x': {
                'y': 'aaa'
            }
        }
    })
    for path, value in [('a', 2), ('b/c', '123'), ('d/x/y', 'aaa')]:
        assert cfg.get_value(path=path) == value
        assert cfg.get(path) == value
    with pytest.raises(LookupError):
        assert cfg.get('xxx')
    assert cfg.get('xxx', 123) == 123


def test_crypto_gen_random_str():

    s1 = pyaltt2.crypto.gen_random_str()
    s2 = pyaltt2.crypto.gen_random_str()
    s3 = pyaltt2.crypto.gen_random_str(length=16)

    assert s1 != s2
    assert len(s1) == 32
    assert len(s2) == 32
    assert len(s3) == 16


def test_crypto_encrypt_decrypt():

    private_key = 'mysecretkey1234567'
    value = 'hello, I am string'

    import hashlib

    keyhash256 = hashlib.sha256(private_key.encode()).digest()
    keyhash512 = hashlib.sha512(private_key.encode()).digest()

    for use_key_hash in (False, True):

        for use_hmac, e in zip((False, True, 'hmackey'),
                               (UnicodeDecodeError, ValueError, ValueError)):

            if use_key_hash:
                key = keyhash512 if use_hmac is True else keyhash256
            else:
                key = private_key

            enc = pyaltt2.crypto.encrypt(value.encode(),
                                         key,
                                         key_is_hash=use_key_hash,
                                         hmac_key=use_hmac)
            assert isinstance(enc, str)
            assert pyaltt2.crypto.decrypt(enc,
                                          key,
                                          key_is_hash=use_key_hash,
                                          hmac_key=use_hmac).decode() == value
            try:
                assert pyaltt2.crypto.decrypt(enc, '123').decode() != value
            except e:
                pass

            enc = pyaltt2.crypto.encrypt(value.encode(),
                                         key,
                                         key_is_hash=use_key_hash,
                                         hmac_key=use_hmac,
                                         b64=False)
            assert isinstance(enc, bytes)
            assert pyaltt2.crypto.decrypt(enc,
                                          key,
                                          key_is_hash=use_key_hash,
                                          hmac_key=use_hmac,
                                          b64=False).decode() == value
            try:
                assert pyaltt2.crypto.decrypt(
                    enc, '123', key_is_hash=False, hmac_key=use_hmac,
                    b64=False).decode() != value
            except e:
                pass


def test_crypto_rioja():

    private_key = 'mysecretkey1234567'
    value = 'hello, I am string'

    rj = pyaltt2.crypto.Rioja(private_key)
    rj2 = pyaltt2.crypto.Rioja('123')

    enc = rj.encrypt(value)
    assert isinstance(enc, str)
    assert rj.decrypt(enc).decode() == value
    try:
        assert rj2.decrypt(enc).decode() != value
    except ValueError:
        pass

    enc = rj.encrypt(value.encode(), b64=False)
    assert isinstance(enc, bytes)
    assert rj.decrypt(enc, b64=False).decode() == value
    try:
        assert rj2.decrypt(enc, b64=False).decode() != value
    except ValueError:
        pass


def test_crypto_signature():
    content = 'test'
    content2 = 'test2'
    with open('./keys/private.pem', 'rb') as fh:
        pkey = fh.read()
    with open('./keys/public.pem', 'rb') as fh:
        pubkey = fh.read()
    signature = pyaltt2.crypto.sign(content, pkey)
    pyaltt2.crypto.verify_signature(content, signature, pubkey)
    with pytest.raises(Exception):
        pyaltt2.crypto.verify_signature(content2, signature, pubkey)
    with pytest.raises(Exception):
        pyaltt2.crypto.verify_signature(content2, signature)
    pyaltt2.crypto.default_public_key = pubkey
    pyaltt2.crypto.verify_signature(content, signature)
    with pytest.raises(Exception):
        pyaltt2.crypto.verify_signature(content2, signature)


def test_locker():
    mylock = pyaltt2.locker.Locker(mod='test', timeout=0.1, relative=False)
    result = SimpleNamespace(critical_called=False)

    def mycritical():
        result.critical_called = True

    mylock.critical = mycritical

    @mylock
    def myfunc():
        pass

    for i in range(10):
        myfunc()
    assert mylock.lock.acquire()

    l = logging.getLogger().level

    logging.basicConfig(level=100)
    myfunc()
    logging.basicConfig(level=l)

    assert result.critical_called

    mylock.lock.release()

    myfunc()


def test_parse_host_port():
    host, port = pyaltt2.network.parse_host_port('127.0.0.1:8080')
    assert host == '127.0.0.1'
    assert port == 8080

    host, port = pyaltt2.network.parse_host_port('127.0.0.1')
    assert host == '127.0.0.1'
    assert port == 0

    host, port = pyaltt2.network.parse_host_port('127.0.0.1', default_port=80)
    assert host == '127.0.0.1'
    assert port == 80

    with pytest.raises(ValueError):
        host, port = pyaltt2.network.parse_host_port('127.0.0.1:xxx')


def test_netacl_match():
    from netaddr import IPNetwork

    hosts = ['127.0.0.1', '10.2.3.4/32', '192.168.1.0/24', '10.55.0.0/16']
    acl = [IPNetwork(h) for h in hosts]

    assert pyaltt2.network.netacl_match('127.0.0.1', acl) is True
    assert pyaltt2.network.netacl_match('10.2.3.4', acl) is True
    assert pyaltt2.network.netacl_match('192.168.1.4', acl) is True
    assert pyaltt2.network.netacl_match('10.55.1.4', acl) is True
    assert pyaltt2.network.netacl_match('127.0.0.2', acl) is False
    assert pyaltt2.network.netacl_match('1.2.3.4', acl) is False
    assert pyaltt2.network.netacl_match('10.2.3.5', acl) is False
    assert pyaltt2.network.netacl_match('192.168.2.1', acl) is False
    assert pyaltt2.network.netacl_match('10.56.1.2', acl) is False


def test_netacl_generate():
    hosts = ['127.0.0.1', '10.2.3.4/32', '192.168.1.0/24', '10.55.0.0/16']

    assert pyaltt2.network.generate_netacl([]) == []
    assert pyaltt2.network.generate_netacl([], default=None) is None

    acl = pyaltt2.network.generate_netacl(hosts)

    assert pyaltt2.network.netacl_match('127.0.0.1', acl) is True
    assert pyaltt2.network.netacl_match('10.2.3.4', acl) is True
    assert pyaltt2.network.netacl_match('192.168.1.4', acl) is True
    assert pyaltt2.network.netacl_match('10.55.1.4', acl) is True
    assert pyaltt2.network.netacl_match('127.0.0.2', acl) is False
    assert pyaltt2.network.netacl_match('1.2.3.4', acl) is False
    assert pyaltt2.network.netacl_match('10.2.3.5', acl) is False
    assert pyaltt2.network.netacl_match('192.168.2.1', acl) is False
    assert pyaltt2.network.netacl_match('10.56.1.2', acl) is False

    acl = pyaltt2.network.generate_netacl(hosts[0])
    assert pyaltt2.network.netacl_match('127.0.0.1', acl) is True
    assert pyaltt2.network.netacl_match('10.2.3.4', acl) is False
    assert pyaltt2.network.netacl_match('127.0.0.2', acl) is False


def test_val_to_boolean():
    assert pyaltt2.converters.val_to_boolean(True) is True
    assert pyaltt2.converters.val_to_boolean(False) is False
    assert pyaltt2.converters.val_to_boolean(None) is None
    assert pyaltt2.converters.val_to_boolean(1) is True
    assert pyaltt2.converters.val_to_boolean(0) is False
    for s in ['True', 'true', 'Yes', 'on', 'y']:
        assert pyaltt2.converters.val_to_boolean(s) is True
    for s in ['False', 'false', 'no', 'OFF', 'n']:
        assert pyaltt2.converters.val_to_boolean(s) is False
    for s in ['Falsex', 'falsex', 'ano', 'xOFF', 'z']:
        with pytest.raises(ValueError):
            assert pyaltt2.converters.val_to_boolean(s)


def test_safe_int():
    assert pyaltt2.converters.safe_int(20) == 20
    assert pyaltt2.converters.safe_int('20') == 20
    assert pyaltt2.converters.safe_int('0xFF') == 255
    assert pyaltt2.converters.safe_int('0b11101') == 29
    with pytest.raises(ValueError):
        assert pyaltt2.converters.safe_int('0xFZ')
        assert pyaltt2.converters.safe_int('0b12345')


def test_parse_date():
    from datetime import datetime
    import pytz
    d = datetime.now()
    ts = d.timestamp()
    test_data = [(d, d), (ts, d), (3001, datetime.fromtimestamp(3001)),
                 ('2019-11-22', datetime(2019, 11, 22))]
    for t in test_data:
        assert pyaltt2.converters.parse_date(t[0],
                                             return_timestamp=False) == t[1]
    test_data = [(d, ts), (ts, ts), (3001, 3001)]
    for t in test_data:
        assert pyaltt2.converters.parse_date(t[0]) == t[1]
    assert pyaltt2.converters.parse_date(
        time.time(), return_timestamp=False).date() == datetime.now().date()
    assert pyaltt2.converters.parse_date(
        time.time() * 1000, return_timestamp=False,
        ms=True).date() == datetime.now().date()


def test_parse_number():
    test_data = [(12345, 12345), (123.45, 123.45), ('123.45', 123.45),
                 (' 123 456.78', 123456.78), ('123 456.789', 123456.789),
                 (' 123,456,789.222', 123456789.222),
                 ('123.456.789,222', 123456789.222),
                 ('123456789,22', 123456789.22)]

    for d in test_data:
        s = d[0]
        v = d[1]
        assert pyaltt2.converters.parse_number(s) == v
        if isinstance(s, str):
            s = '-' + s.strip()
        else:
            s = -1 * s
        assert pyaltt2.converters.parse_number(s) == -1 * v


def test_parse_func_str():
    test_data = [{
        'raw': 'myfunc()',
        'fname': 'myfunc'
    }, {
        'raw': 'myfunc(1,2,3)',
        'fname': 'myfunc',
        'args': [1, 2, 3]
    }, {
        'raw': 'myfunc("test")',
        'fname': 'myfunc',
        'args': ['test']
    }, {
        'raw': '@myfunc("test")',
        'fname': '@myfunc',
        'args': ['test']
    }, {
        'raw': 'myfunc(\'tes"t\')',
        'fname': 'myfunc',
        'args': ['tes"t']
    }, {
        'raw': 'myfunc(\'test\')',
        'fname': 'myfunc',
        'args': ['test']
    }, {
        'raw': 'myfunc("test", 123.45)',
        'fname': 'myfunc',
        'args': ['test', 123.45]
    }, {
        'raw': 'myfunc(123.45, \'test\')',
        'fname': 'myfunc',
        'args': [123.45, 'test']
    }, {
        'raw': 'myfunc("test", 123,value=123'
               ',name="xxx", arr=[1,2,3], arr2=["a","b","c"])',
        'fname': 'myfunc',
        'args': ['test', 123],
        'kwargs': {
            'name': 'xxx',
            'value': 123,
            'arr': [1, 2, 3],
            'arr2': ['a', 'b', 'c']
        }
    }, {
        'raw': 'myfunc("test", 123,'
               'value'
               '=123,name="xxx", arr=[1,2,3], arr2=[a,b,c])',
        'fname': 'myfunc',
        'args': ['test', 123],
        'kwargs': {
            'name': 'xxx',
            'value': 123,
            'arr': [1, 2, 3],
            'arr2': ['a', 'b', 'c']
        },
        'auto_quote': True
    }, {
        'raw': 'myfunc(\'test\', 123,value=123,name=\'xxx\')  ',
        'fname': 'myfunc',
        'args': ['test', 123],
        'kwargs': {
            'name': 'xxx',
            'value': 123
        }
    }, {
        'raw': 'myfunc(\'test\', 123,value=123,name="xxx")',
        'fname': 'myfunc',
        'args': ['test', 123],
        'kwargs': {
            'name': 'xxx',
            'value': 123
        }
    }, {
        'raw': '@myfunc(test, 12a,value=zz10, name=xxx)',
        'fname': '@myfunc',
        'args': ['test', '12a'],
        'kwargs': {
            'name': 'xxx',
            'value': 'zz10'
        },
        'auto_quote': True,
    }, {
        'raw': 'myfunc(test, 123,value=123, name=xxx)',
        'fname': 'myfunc',
        'args': ['test', 123],
        'kwargs': {
            'name': 'xxx',
            'value': 123
        },
        'auto_quote': True,
    }, {
        'raw': 'my_func("test", 123,value=123,name=\'x"xx\')',
        'fname': 'my_func',
        'args': ['test', 123],
        'kwargs': {
            'name': 'x"xx',
            'value': 123
        }
    }, {
        'raw': 'myfunc("test", 123,value=123.45,name="xxx")',
        'fname': 'myfunc',
        'args': ['test', 123],
        'kwargs': {
            'name': 'xxx',
            'value': 123.45
        }
    }, {
        'raw': 'myfunctest(os.system("ls"),value=123,name="xxx")',
        'raises': True
    }, {
        'raw': 'myfunctest(123,value=os.system("ls"),name="xxx")',
        'raises': True
    }, {
        'raw': 'myfunctest, 123,value=123,name="xxx")',
        'raises': True
    }, {
        'raw': 'myfunc("test", 123,value=123,name="xxx"',
        'raises': True
    }, {
        'raw': 'myfunc("test", 123,value=123,name=["xxx")',
        'raises': True
    }, {
        'raw': 'my func("test", 123,value=123,name=["xxx")',
        'raises': True
    }, {
        'raw': 'my"func("test", 123,value=123,name=["xxx")',
        'raises': True
    }, {
        'raw': 'myfunc(123); import sys',
        'raises': True
    }]

    for t in test_data:
        if t.get('raises'):
            with pytest.raises(ValueError):
                pyaltt2.lp.parse_func_str(t['raw'],
                                          auto_quote=t.get('auto_quote'))
        else:
            fname, args, kwargs = pyaltt2.lp.parse_func_str(
                t['raw'], auto_quote=t.get('auto_quote'))
            assert t['fname'] == fname
            assert len(t.get('args', [])) == len(args)
            assert len(t.get('kwargs', {})) == len(kwargs)
            assert t.get('args', []) == args
            for k, v in t.get('kwargs', {}).items():
                assert kwargs[k] == v


def test_merge_dict():
    d1 = {'a': 2, 'b': 3, 'c': {'test': True}}
    d2 = {'a': 3, 'c': {'test2': True}}
    d3 = {'x': 9, 'b': 3, 'c': {'test3': True}}
    merged = pyaltt2.converters.merge_dict(d1, d2, d3)
    assert merged['a'] == 3
    assert merged['b'] == 3
    assert merged['c']['test']
    assert merged['c']['test2']
    assert merged['c']['test3']
    assert merged['x'] == 9


def test_json():
    data = {'a': 2, 'b': 3, 'c': [1, 2, 3, 'test']}
    u = pyaltt2.json.dumps(data, unpicklable=True)
    d = pyaltt2.json.dumps(data, pretty=True)
    d2 = pyaltt2.json.dumps(data, pretty=False)
    pyaltt2.json.jprint(data)


def test_mq_topic_match():
    topics = [('#', 'some/test/topic', True),
              ('some/test/topic', 'some/test', False),
              ('some/test', 'some/test/topic', False),
              ('some/test/topic', 'some/test/topic', True),
              ('some/+/topic', 'some/test/topic', True),
              ('some/+/+', 'some/test/topic', True),
              ('some/+', 'some/test/topic', False),
              ('some/+/#', 'some/test/topic', True),
              ('some/#', 'some/test/topic', True),
              ('+/+/+/#', 'some/test/topic', False),
              ('+/+/#', 'some/test/topic', True)]

    for t in topics:
        assert pyaltt2.converters.mq_topic_match(t[1], t[0]) is t[2]
