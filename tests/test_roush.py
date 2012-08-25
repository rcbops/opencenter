# vim: tabstop=4 shiftwidth=4 softtabstop=4
import unittest
import webapp

class RoushTestCase(unittest.TestCase):

    def setUp(self):
        # This has to be set to expose tracebacks
        # roush.app.testing = True
        # self.app = roush.app.test_client()
        foo = webapp.Thing("roush", configfile='local.conf', debug = True)
        self.app = foo.test_client()


    def tearDown(self):
        pass

