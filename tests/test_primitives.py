# vim: tabstop=4 shiftwidth=4 softtabstop=4
import unittest2

from util import RoushTestCase


class FactsTests(RoushTestCase):
    base_object = 'primitive'

    def setUp(self):
        self._clean_all()

    def tearDown(self):
        pass
