import sys
import os


def redirect(stdout=None, stderr=None):
    for dev, v, st in [(stdout, 'STDOUT', sys.stdout),
                       (stderr, 'STDERR', sys.stderr)]:
        s = dev or os.getenv(v)
        if s:
            st = open(s, 'w')
