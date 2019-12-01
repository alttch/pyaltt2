#!/usr/bin/env pytest

from pathlib import Path
import sys
import pytest
import logging

sys.path.insert(0, Path().absolute().parent.as_posix())

import pyaltt2.crypto
import pyaltt2.locker
import pyaltt2.network
import pyaltt2.parsers
import pyaltt2.nlp

from types import SimpleNamespace


def test_crypto_gen_random_str():

    s1 = pyaltt2.crypto.gen_random_str()
    s2 = pyaltt2.crypto.gen_random_str()
    s3 = pyaltt2.crypto.gen_random_str(length=16)

    assert s1 != s2
    assert len(s1) == 64
    assert len(s2) == 64
    assert len(s3) == 16


def test_crypto_encrypt_decrypt():

    key = 'mysecretkey'
    value = 'hello, I am string'

    enc = pyaltt2.crypto.encrypt(value.encode(), key)
    assert isinstance(enc, str)
    assert pyaltt2.crypto.decrypt(enc, key).decode() == value
    try:
        assert pyaltt2.crypto.decrypt(enc, '123').decode() != value
    except UnicodeDecodeError:
        pass

    enc = pyaltt2.crypto.encrypt(value.encode(), key, encode=False)
    assert isinstance(enc, bytes)
    assert pyaltt2.crypto.decrypt(enc, key, decode=False).decode() == value
    try:
        assert pyaltt2.crypto.decrypt(enc, '123',
                                      decode=False).decode() != value
    except UnicodeDecodeError:
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
    assert pyaltt2.parsers.val_to_boolean(1) is True
    assert pyaltt2.parsers.val_to_boolean(0) is False
    assert pyaltt2.parsers.val_to_boolean(None) is None
    for s in ['True', 'true', 'Yes', 'on', 'y']:
        assert pyaltt2.parsers.val_to_boolean(s) is True
    for s in ['False', 'false', 'no', 'OFF', 'n']:
        assert pyaltt2.parsers.val_to_boolean(s) is False
    for s in ['Falsex', 'falsex', 'ano', 'xOFF', 'z']:
        with pytest.raises(ValueError):
            assert pyaltt2.parsers.val_to_boolean(s)


def test_safe_int():
    assert pyaltt2.parsers.safe_int(20) == 20
    assert pyaltt2.parsers.safe_int('20') == 20
    assert pyaltt2.parsers.safe_int('0xFF') == 255
    with pytest.raises(ValueError):
        assert pyaltt2.parsers.safe_int('0xFZ')


def test_parse_func_str():
    test_data = [
        {
            'raw': 'myfunc()',
            'fname': 'myfunc'
        },
        {
            'raw': 'myfunc(1,2,3)',
            'fname': 'myfunc',
            'args': [1, 2, 3]
        },
        {
            'raw': 'myfunc(test)',
            'fname': 'myfunc',
            'args': ['test']
        },
        # TODO: broken
        # {
        # 'raw': 'myfunc("test")',
        # 'fname': 'myfunc',
        # 'args': ['test']
        # },
        # TODO: broken, fix later
        # {
        # 'raw': 'myfunc(\'tes"t\')',
        # 'fname': 'myfunc',
        # 'args': ['tes"t']
        # },
        # TODO: broken
        # {
        # 'raw': 'myfunc(\'test\')',
        # 'fname': 'myfunc',
        # 'args': ['test']
        # },
        {
            'raw': 'myfunc(test, 123.45)',
            'fname': 'myfunc',
            'args': ['test', 123.45]
        },
        # TODO: broken
        # {
        # 'raw': 'myfunc(123.45, test)',
        # 'fname': 'myfunc',
        # 'args': [123.45, 'test']
        # },
        {
            'raw': 'myfunc(test, 123,value=123,name=xxx)',
            'fname': 'myfunc',
            'args': ['test', 123],
            'kwargs': {
                'name': 'xxx',
                'value': 123
            }
        },
        {
            'raw': 'myfunc(test, 123,value=123,name=\'xxx\')',
            'fname': 'myfunc',
            'args': ['test', 123],
            'kwargs': {
                'name': 'xxx',
                'value': 123
            }
        },
        {
            'raw': 'myfunc(test, 123,value=123,name="xxx")',
            'fname': 'myfunc',
            'args': ['test', 123],
            'kwargs': {
                'name': 'xxx',
                'value': 123
            }
        },
        {
            'raw': 'myfunc(test, 123,value=123,name=\'x"xx\')',
            'fname': 'myfunc',
            'args': ['test', 123],
            'kwargs': {
                'name': 'x"xx',
                'value': 123
            }
        },
        # TODO: broken
        # {
        # 'raw': 'myfunc(test, 123,value=123.45,name=xxx)',
        # 'fname': 'myfunc',
        # 'args': ['test', 123],
        # 'kwargs': {
        # 'name': 'xxx',
        # 'value': 123.45
        # }
        # },
        {
            'raw': 'myfunctest, 123,value=123,name="xxx")',
            'raises': True
        },
        {
            'raw': 'myfunc(test, 123,value=123,name="xxx"',
            'raises': True
        },
        # TODO: broken, fix later
        # {
            # 'raw': 'myfunc(test, 123,value=123,name=["xxx")',
            # 'raises': True
        # },
    ]

    for t in test_data:
        if t.get('raises'):
            with pytest.raises(ValueError):
                pyaltt2.nlp.parse_func_str(t['raw'])
        else:
            fname, args, kwargs = pyaltt2.nlp.parse_func_str(t['raw'])
            assert t['fname'] == fname
            assert len(t.get('args', [])) == len(args)
            assert len(t.get('kwargs', {})) == len(kwargs)
            assert t.get('args', []) == args
            for k, v in t.get('kwargs', {}).items():
                assert kwargs[k] == v
