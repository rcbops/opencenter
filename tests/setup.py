# vim: tabstop=4 shiftwidth=4 softtabstop=4
import unittest
from db.database import init_db
import webapp


class RoushTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        foo = webapp.Thing("roush", configfile='local.conf', debug=True)
        init_db(foo.config['database_uri'])
        cls.app = foo.test_client()
        try:
            print "Setting up testcase (%s) ... " % (cls.__name__),
            if hasattr(cls, "setup") and callable(cls.setup):
                cls.setup()
            print "ok"
        except:
            print "fail"
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            print "Tearing down testcase (%s) ... " % (cls.__name__),
            if hasattr(cls, "cleanup") and callable(cls.cleanup):
                cls.cleanup()
            print "ok"
        except:
            print "fail"
            raise
