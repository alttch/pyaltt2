import os
import signal
import sys
import argparse
import time
from pathlib import Path
import yaml


def manage_gunicorn_app(app,
                        app_dir='.',
                        name=None,
                        default_port=8081,
                        app_class=None,
                        api_uri='/'):
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
        name = app
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
    start_failed_after = config.get('start-failed-after', 10)
    force_stop_after = config.get('force-stop-after', 10)

    def get_app_pid():
        if os.path.exists(pidfile):
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

    def status():
        pid = get_app_pid()
        if pid and get_app_status(pid):
            print(f'{name} is running. API: http://{api_listen}{api_uri}')
            return True
        print(f'{name} is not running')
        return False

    def stop_server():
        pid = get_app_pid()
        if pid and get_app_status(pid):
            printfl(f'Stopping {name}...', end='')
            os.kill(pid, signal.SIGTERM)
            c = 0
            while os.path.exists(pidfile):
                time.sleep(1)
                printfl('.', end='')
                c += 1
                if c > force_stop_after:
                    os.kill(pid, signal.SIGKILL)
                    print('KILLED')
            print('stopped')

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
                while not os.path.isfile(pidfile):
                    c += 1
                    time.sleep(1)
                    printfl('.', end='')
                    if c > start_failed_after:
                        print('FAILED')
                        return False
                print('started')
                return True
