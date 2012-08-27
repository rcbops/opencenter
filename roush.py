#!/usr/bin/env python

from webapp import Thing
import wilkerror

if __name__ == '__main__':
    foo = Thing("roush", configfile='local.conf', debug=True)
    wilkerror.setup_errors(foo)
    foo.run()
