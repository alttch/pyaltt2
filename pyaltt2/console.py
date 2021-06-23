import sys
import os


def redirect(stdout=None, stderr=None):
    for dev, v in [(stdout, 'stdout'), (stderr, 'stderr')]:
        s = dev or os.getenv(v.upper())
        if s:
            setattr(sys, v, open(s, 'w'))
