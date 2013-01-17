# vim: tabstop=4 shiftwidth=4 softtabstop=4
import unittest2

from util import RoushTestCase
from util import inject


class PrimitiveTests(RoushTestCase):
    base_object = 'primitive'

    def __init__(self, *args, **kwargs):
        super(PrimitiveTests, self).__init__(*args, **kwargs)

    def setUp(self):
        self.logger.error('argh')
        self._clean_all()

    def tearDown(self):
        self._clean_table('primitives')


PrimitiveTests = inject(PrimitiveTests)
