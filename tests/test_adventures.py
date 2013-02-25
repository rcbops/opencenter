#

from util import OpenCenterTestCase
from util import inject


class AdventuresTests(OpenCenterTestCase):
    base_object = 'adventure'

AdventuresTests = inject(AdventuresTests)
