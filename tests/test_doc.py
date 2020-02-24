# -*- coding: utf-8 -*-
"""
test lazy-regression-tests
"""
import sys
import os

import unittest

import pdb

try:
    import unittest.mock as mock
except (ImportError,) as ei:
    import mock  # python 2?


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


from lazy_regression_tests._baseutils import set_cpdb

rpdb = breakpoints = cpdb

from lazy_regression_tests.lazy3.http_validators import HTMLValidationMixin

from lazy_regression_tests.lazy3.http_validators import ResponseHTML


from lazy_regression_tests.lazy3.filters import CSSRemoveFilter

from lazy_regression_tests.lazy3.helper_tst import Helper, get_mock_env

di_mock_env = get_mock_env()

from lazy_regression_tests.lazy3 import LazyMixin

from lazy_regression_tests.lazy3 import (
    DictValidator,
    ValidationDirective,
    ValidationManager,
    DirectValidator,
    AutoExp,
)

from lazy_regression_tests.lazy3.http_validators import (
    HtmlFilterManager,
    HTMLValidationMixin,
    ResponseHTML,
    CSSValidator,
)

from lazy_regression_tests.lazy3.filters import (
    RegexRemoveSaver,
    DictFilter,
    FilterDirective,
    FilterManager,
    JsonFilterManager,
)

from lazy_regression_tests.lazy3.http_validators import HtmlFilterManager


# pylint: disable=no-member
class LazyMixinBasic(LazyMixin, unittest.TestCase):

    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)

    extension = "html"
    cls_filters = dict(html=HtmlFilterManager())

    # @mock.patch.dict(os.environ, di_mock_env)
    def test_it(self):
        """get response"""
        try:
            if self.__class__ in (LazyMixinBasic,):
                return

            # this is a pretend server, could have been the Django test server for example
            http_response = self.get_raw_response()

            response = ResponseHTML(http_response)
            self.check_expectations(response=response)
            tmp = self.assert_exp(response.content, self.extension)

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


filter_variables = [
    FilterDirective(
        "timestamp", filter_=CSSRemoveFilter("span.timestamp", "timestamp", scalar=True)
    ),
    FilterDirective("csrf", filter_=RegexRemoveSaver("csrf_token", "csrf_token")),
]


class Test_Features(Helper, LazyMixinBasic):

    name = "Mr. Rabbit"
    line1 = "Item 1"
    line2 = "Item 2"
    line3 = "Item 3"

    xcls_filters = dict(html=filter_variables)

    cls_validators = [
        ValidationDirective("title", exp="Your order"),
        ValidationDirective("name", exp=AutoExp, validator=CSSValidator("#name")),
    ]

    template = """
<title>Your order</title>
<script>
const csrf_token = '{{csrf}}';
</script>
<body>
    Hi&nbsp;<span id="name">{{ name }}</span>&nbsp;!<br/> 
    It is now<span class="timestamp">{{ timestamp }}</span>.<br/>
    Your order is:
    <ul>
        <li>{{line1}}</li>
        <li>{{line2}}</li>
        <li>{{line3}}</li>
    </ul>
</body>
    """


if __name__ == "__main__":

    cpdb = set_cpdb()
    rc = 0
    try:
        rc = unittest.main()
    finally:
        sys.exit(rc)
