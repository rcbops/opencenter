#!/usr/bin/env python

from webapp import Thing

if __name__ == '__main__':
    foo = Thing(configfile = 'local.conf', debug = True)
    foo.run()
