#

from util import RoushTestCase
from util import inject


class AdventuresTests(RoushTestCase):
    base_object = 'adventure'

AdventuresTests = inject(AdventuresTests)
