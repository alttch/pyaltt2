#!/usr/bin/env pytest

from pathlib import Path
import sys
import pytest
import logging

sys.path.insert(0, Path().absolute().parent.as_posix())

import pyaltt2.crypto
import pyaltt2.locker
import pyaltt2.network
import pyaltt2.converters
import pyaltt2.lp
import pyaltt2.json

from types import SimpleNamespace


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

    assert pyaltt2.network.netacl_match('127.0.0.1', acl)
    assert pyaltt2.network.netacl_match('10.2.3.4', acl)
    assert pyaltt2.network.netacl_match('192.168.1.4', acl)
    assert pyaltt2.network.netacl_match('10.55.1.4', acl)
    assert pyaltt2.network.netacl_match('127.0.0.2', acl) is False
    assert pyaltt2.network.netacl_match('1.2.3.4', acl) is False
    assert pyaltt2.network.netacl_match('10.2.3.5', acl) is False
    assert pyaltt2.network.netacl_match('192.168.2.1', acl) is False
    assert pyaltt2.network.netacl_match('10.56.1.2', acl) is False


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
    with pytest.raises(ValueError):
        assert pyaltt2.converters.safe_int('0xFZ')


def test_parse_date():
    from datetime import datetime
    d = datetime.now()
    ts = d.timestamp()
    test_data = [(d, d), (ts, d), (3001, datetime(1970, 1, 1, 0, 50, 1)),
                 ('2019-11-22', datetime(2019, 11, 22))]
    for t in test_data:
        assert pyaltt2.converters.parse_date(t[0],
                                             return_timestamp=False) == t[1]
    test_data = [(d, ts), (ts, ts), (3001, 3001)]
    for t in test_data:
        assert pyaltt2.converters.parse_date(t[0]) == t[1]


test_parse_date()


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
        if isinstance(s, str): s = '-' + s.strip()
        else: s = -1 * s
        assert pyaltt2.converters.parse_number(s) == -1 * v


def test_parse_func_str():
    test_data = [{
        'raw': 'myfunc()',
        'fname': 'myfunc'
    }, {
        'raw': 'myfunc(1,2,3)',
        'fname': 'myfunc',
        'args': (1, 2, 3)
    }, {
        'raw': 'myfunc("test")',
        'fname': 'myfunc',
        'args': ('test',)
    }, {
        'raw': '@myfunc("test")',
        'fname': '@myfunc',
        'args': ('test',)
    }, {
        'raw': 'myfunc(\'tes"t\')',
        'fname': 'myfunc',
        'args': ('tes"t',)
    }, {
        'raw': 'myfunc(\'test\')',
        'fname': 'myfunc',
        'args': ('test',)
    }, {
        'raw': 'myfunc("test", 123.45)',
        'fname': 'myfunc',
        'args': ('test', 123.45)
    }, {
        'raw': 'myfunc(123.45, \'test\')',
        'fname': 'myfunc',
        'args': (123.45, 'test')
    }, {
        'raw': 'myfunc("test", 123,value=123,name="xxx")',
        'fname': 'myfunc',
        'args': ('test', 123),
        'kwargs': {
            'name': 'xxx',
            'value': 123
        }
    }, {
        'raw': 'myfunc(\'test\', 123,value=123,name=\'xxx\')  ',
        'fname': 'myfunc',
        'args': ('test', 123),
        'kwargs': {
            'name': 'xxx',
            'value': 123
        }
    }, {
        'raw': 'myfunc(\'test\', 123,value=123,name="xxx")',
        'fname': 'myfunc',
        'args': ('test', 123),
        'kwargs': {
            'name': 'xxx',
            'value': 123
        }
    }, {
        'raw': 'myfunc(test, 123,value=123, name=xxx)',
        'fname': 'myfunc',
        'args': ('test', 123),
        'kwargs': {
            'name': 'xxx',
            'value': 123
        },
        'auto_quote': True,
    }, {
        'raw': 'my_func("test", 123,value=123,name=\'x"xx\')',
        'fname': 'my_func',
        'args': ('test', 123),
        'kwargs': {
            'name': 'x"xx',
            'value': 123
        }
    }, {
        'raw': 'myfunc("test", 123,value=123.45,name="xxx")',
        'fname': 'myfunc',
        'args': ('test', 123),
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
            assert len(t.get('args', ())) == len(args)
            assert len(t.get('kwargs', {})) == len(kwargs)
            assert t.get('args', ()) == args
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
