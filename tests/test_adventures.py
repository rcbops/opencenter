# vim: tabstop=4 shiftwidth=4 softtabstop=4
from util import _test_request_returns, _test_seed_data_request_returns
from util import inject
from util import OpenCenterTestCase


class AdventuresTests(OpenCenterTestCase):
    base_object = 'adventure'


def build_tests():
    ats = inject(AdventuresTests)

    test = lambda self: _test_request_returns(
        self, 'post', '/%s/1/execute' % self._pluralize(self.base_object),
        {}, 400)
    test.__name__ = 'test_adventure_execute_no_node_returns_400'
    setattr(ats, test.__name__, test)

    test = lambda self: _test_seed_data_request_returns(
        self, 'post', '/%s/1/execute' % self._pluralize(self.base_object),
        {'node': 9999999}, 404, {self.base_object: 1})
    test.__name__ = 'test_adventure_execute_non_existant_node_returns_404'
    setattr(ats, test.__name__, test)

    test = lambda self: _test_seed_data_request_returns(
        self, 'post', '/%s/999999/execute' % self._pluralize(self.base_object),
        {'node': 1}, 404, {'node': 1})
    test.__name__ = 'test_adventure_execute_non_existant_adventure_returns_404'
    setattr(ats, test.__name__, test)

    return ats

AdventuresTests = build_tests()
