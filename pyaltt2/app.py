"""
Extra mods required: pyyaml, requests, jsonschema
"""

import os
import signal
import sys
import argparse
import requests
import time
from pathlib import Path
from .config import choose_file, load_yaml
import jsonschema

PROPERTY_MAP_SCHEMA = {
    'type': 'object',
    'properties': {
        'path': {
            'type': 'string'
        },
        'listen': {
            'type': 'string'
        },
        'pid-file': {
            'type': 'string'
        },
        'start-failed-after': {
            'type': 'integer',
            'minimum': 0.1
        },
        'force-stop-after': {
            'type': 'integer',
            'minimum': 0.1
        },
        'launch-debug': {
            'type': 'boolean',
        },
        'extra-options': {
            'type': 'string'
        }
    },
    'additionalProperties': False
}


def manage_gunicorn_app(app,
                        app_dir='.',
                        name=None,
                        version=None,
                        build=None,
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
    cmds = ['start', 'stop', 'restart', 'status', 'launch']
    if version:
        cmds.append('version')
    ap.add_argument('command', choices=cmds)
    ap.add_argument('--config-file',
                    metavar='FILE',
                    help='alternative config file')
    ap.add_argument('-D',
                    '--debug',
                    help='Force debug mode',
                    action='store_true')
    a = ap.parse_args()

    if a.command == 'version':
        print('{}{}{}'.format(name, f' {version}' if version else '',
                              f' {build}' if build else ''))
        sys.exit(0)

    app_env_name = f'{app.upper()}_CONFIG'

    config_file = choose_file(a.config_file,
                              env=app_env_name,
                              choices=[
                                  f'{app_dir}/etc/{app}.yml',
                                  f'/opt/{app}/etc/{app}.yml',
                                  f'/usr/local/etc/{app}.yml'
                              ])
    config = load_yaml(config_file)[app].get('gunicorn', {})
    jsonschema.validate(config, schema=PROPERTY_MAP_SCHEMA)

    pidfile = config.get('pid-file', f'/tmp/{app}.pid')
    api_listen = config.get('listen', f'0.0.0.0:{default_port}')
    api_url = api_listen.replace('0.0.0.0', '127.0.0.1')
    start_failed_after = config.get('start-failed-after', 10)
    force_stop_after = config.get('force-stop-after', 10)
    debug_mode = a.debug
    launch_debug = True if debug_mode else config.get('launch-debug')

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
                    return True
            print('stopped')
            return True
        else:
            return False

    def start_server(launch=False):
        pid = get_app_pid()
        if pid and get_app_status(pid):
            print(f'{name} is already running')
        else:
            if not launch: printfl(f'Starting {name}...', end='')
            xopts = config.get('extra-options', '')
            if xopts and launch:
                import re
                xopts = re.sub(r'--log-file .* ', '', xopts + ' ') + ' '
                xopts = f' {xopts} '.replace(' --log-syslog ', ' ')
            code = os.system(
                ('{gunicorn} {daemon} -e {config_env} --pid {pidfile}'
                 ' -b {api_listen} {xopts} {debug} {app_class}').format(
                     gunicorn=os.getenv('GUNICORN',
                                        config.get('path', 'gunicorn')),
                     daemon='' if launch else '-D',
                     config_env=f'{app_env_name}={config_file}',
                     pidfile=pidfile,
                     api_listen=api_listen,
                     xopts=xopts,
                     debug='--log-level DEBUG' if
                     (launch and launch_debug) or debug_mode else '',
                     app_class=app_class))
            if code:
                if not launch: print(f'FAILED ({code})')
                return False
            elif not launch:
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
            else:
                return True

    def restart_server():
        if stop_server():
            time.sleep(1)
        return start_server()

    if a.command == 'start':
        sys.exit(0 if start_server() else 1)
    if a.command == 'launch':
        sys.exit(0 if start_server(launch=True) else 1)
    elif a.command == 'stop':
        stop_server()
        sys.exit(0)
    elif a.command == 'restart':
        sys.exit(0 if restart_server() else 1)
    elif a.command == 'status':
        sys.exit(0 if status() else 1)
