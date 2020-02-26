# -*- coding: utf-8 -*-
"""
test lazy-regression-tests
"""
import sys
import os
import re

import unittest

import pdb

try:
    import unittest.mock as mock
except (ImportError,) as ei:
    import mock  # python 2?


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


from lazy_regression_tests._baseutils import set_cpdb, ppp

rpdb = breakpoints = cpdb

from lazy_regression_tests.lazy3.http_validators import HTMLValidationMixin

from lazy_regression_tests.lazy3.http_validators import ResponseHTML


from lazy_regression_tests.lazy3.filters import CSSRemoveFilter

from lazy_regression_tests.lazy3.helper_tst import (
    Helper,
    get_mock_env,
    get_fake_html_response,
)

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
class LazyMixinBasic(LazyMixin):
    """ base Mixin class for the lazy test framework """

    # 👇 ⚙️ tracks where expectation and received files are saved
    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)

    extension = "html"

    # 👇 ⚙️ Tells the framework what extensions/content to expect
    cls_filters = dict(html=HtmlFilterManager())

    def test_it(self, data={}):
        """ fetch data, run validations, regression test """
        try:

            # this is a pretend server, could have been the Django test server for example
            # could be `requests` against a real site
            # anything returning an HTML response would do
            http_response = get_fake_html_response(self, data=data)

            # 👇 lazy-testing, in 3 lines of code 👇

            # ResponseHTML "adapts" the standard http_response by tracking attributes
            # like content_type, status_code, headers...
            response = ResponseHTML(http_response)

            # response.status_code = 404
            # pdb.set_trace()
            # self.validationmgr.debug()
            # pdb.set_trace()

            # Check validation such as content_type and status code
            self.check_expectations(response=response)

            # Regression test - does the received data match expectations?
            tmp = self.assert_exp(response.content, "html")

            # 👆 lazy-testing 👆

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


# 👇⚙️This enables the lazy-test framework
class Test_Features(Helper, HTMLValidationMixin, LazyMixinBasic, unittest.TestCase):
    """ this is the test we are running here """

    cls_filters = dict(html=filter_variables)  # 👈 This is how we add the filters

    name = "Mr. Rabbit"
    line1 = "Item 1"
    line2 = "Item 2"
    line3 = "Item 3"

    # 👇 setting up the validations
    cls_validators = [
        ValidationDirective("title", exp="Your order"),
        ValidationDirective("name", exp=AutoExp, validator=CSSValidator("#name")),
    ]

    # the template used to generate the fake html
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
        <li class="orderline">{{line1}}</li>
        <li class="orderline">{{line2}}</li>
        <li class="orderline">{{line3}}</li>
    </ul>
</body>
    """


# @unittest.skipUnless(False, "this is an intentional failure")
class Test_Features_Regex(Test_Features):
    """ This should fail """

    cls_validators = [  # 👇                      #👇
        ValidationDirective(
            "item", exp=re.compile("^Item"), validator=CSSValidator("li.orderline")
        )
    ]

    name = "Mr. Rabbit"
    line1 = "Item 1"
    line2 = "Item 2"
    line3 = "Bad line 3"


class Test_Features_CustomLineValidation(Test_Features_Regex):
    """ This should pass, we are re-using the CSSValidation lookup for `item`"""

    #   👇
    def check_lineitems(testee: "unittest.TestCase", got, validator: "Validator"):
        """
        `got` will be a list of strings here 
        """
        try:
            for igot in got:
                if not igot.endswith("3"):
                    testee.assertTrue(igot.startswith("Item"))
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            raise

    cls_validators = [ValidationDirective("item", exp=check_lineitems)]  #   👇

    name = "Mr. Rabbit"
    line1 = "Item 1"
    line2 = "Item 2"
    line3 = "Bad line 3"


class Test_Turning_ThingsOff(Test_Features):
    """ we don't have a title or a greeting anymore
        and we don't need to filter out the timestamp either
        as it is fixed.
    """

    def test_it(self, data={}):
        """ fetch data, run validations, regression test """
        try:

            self.set_expectation("title", active=False)
            self.set_expectation("name", active=False)

            self.filters["html"].set_filter("timestamp", active=False)
            http_response = get_fake_html_response(self, data=data)
            response = ResponseHTML(http_response)

            pdb.set_trace()

            filter_ = self.filters["html"]
            ppp(filter_, filter_)

            filter_.debug(self)

            timefilter = filter_.filters.get("timestamp")

            ppp(timefilter, timefilter)

            self.check_expectations(response=response)
            tmp = self.assert_exp(response.content, "html")

            # 👆 lazy-testing 👆

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    # the template used to generate the fake html
    template = """
<body>
    It is now<span class="timestamp">fake, fixed, timestamp</span>.<br/>
</body>
"""


if __name__ == "__main__":

    cpdb = set_cpdb()
    rc = 0
    try:
        rc = unittest.main()
    finally:
        sys.exit(rc)
