"""
Extra mods required: pyyaml, requests
"""

import os
import signal
import sys
import argparse
import requests
import time
from pathlib import Path
import yaml


def manage_gunicorn_app(app,
                        app_dir='.',
                        name=None,
                        default_port=8081,
                        app_class=None,
                        api_uri='/',
                        health_check_uri='/ping'):
    """
    Manage gunicorn-based apps

    Args:
        app: app code
        app_dir: app directory
        name: app name
        default_port: app default listen port
        app_class: launch class for app
        api_uri: app API uri
    """

    def printfl(*args, **kwargs):
        print(*args, **kwargs)
        sys.stdout.flush()

    os.chdir(app_dir)
    if name is None:
        name = app.capitalize()
    if app_class is None:
        app_class = f'{app}.server:app'
    ap = argparse.ArgumentParser()
    ap.add_argument('command',
                    choices=['start', 'stop', 'restart', 'status', 'launch'])
    ap.add_argument('--config-file',
                    metavar='FILE',
                    help='alternative config file')
    a = ap.parse_args()

    if a.config_file:
        fname = a.config_file
    else:
        fname = os.environ.get(f'{app.upper()}_CONFIG')
    if not fname or not Path(fname).exists():
        fname = f'{app_dir}/etc/{app}.yml'
    if not Path(fname).exists():
        fname = f'/opt/{app}/etc/{app}.yml'
    with open(fname) as fh:
        config = yaml.load(fh.read())[app]
    pidfile = config.get('pid-file', f'/tmp/{app}.pid')
    api_listen = config.get('api-listen', f'0.0.0.0:{default_port}')
    api_url = api_listen.replace('0.0.0.0', '127.0.0.1')
    start_failed_after = config.get('start-failed-after', 10)
    force_stop_after = config.get('force-stop-after', 10)

    def get_app_pid():
        if Path(pidfile).exists():
            with open(pidfile) as fh:
                return int(fh.read())
        else:
            return None

    def get_app_status(pid):
        try:
            os.kill(pid, 0)
            return True
        except:
            return False

    def health_check():
        try:
            r = requests.get(f'http://{api_url}{health_check_uri}')
            if not r.ok:
                raise RuntimeError
            return True
        except:
            return False

    def status():
        pid = get_app_pid()
        if pid and get_app_status(pid):
            if health_check():
                print(f'{name} is running. API: http://{api_listen}{api_uri}')
            else:
                print(f'{name} is dead')
            return False
        print(f'{name} is not running')
        return False

    def stop_server():
        pid = get_app_pid()
        if pid and get_app_status(pid):
            printfl(f'Stopping {name}...', end='')
            os.kill(pid, signal.SIGTERM)
            c = 0
            while Path(pidfile).exists():
                time.sleep(1)
                printfl('.', end='')
                c += 1
                if c > force_stop_after:
                    os.kill(pid, signal.SIGKILL)
                    print('KILLED')
            print('stopped')
            return True
        else:
            return False

    def start_server():
        pid = get_app_pid()
        if pid and get_app_status(pid):
            print(f'{name} is already running')
        else:
            printfl(f'Starting {name}...', end='')
            code = os.system('{} -D --pid {} -b {} {} {}'.format(
                config.get('gunicorn', 'gunicorn3'), pidfile, api_listen,
                config.get('extra-gunicorn-options', ''), app_class))
            if code:
                print(f'FAILED ({code})')
                return False
            else:
                c = 0
                while not Path(pidfile).exists() or not health_check():
                    c += 1
                    time.sleep(1)
                    printfl('.', end='')
                    if c > start_failed_after:
                        print('FAILED')
                        return False
                print('started')
                return True

    def restart_server():
        if stop_server():
            time.sleep(1)
        return start_server()

    if a.command == 'start':
        sys.exit(0 if start_server() else 1)
    elif a.command == 'stop':
        stop_server()
        sys.exit(0)
    elif a.command == 'restart':
        sys.exit(0 if restart_server() else 1)
    elif a.command == 'status':
        sys.exit(0 if status() else 1)
