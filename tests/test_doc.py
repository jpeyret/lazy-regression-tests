# -*- coding: utf-8 -*-
"""
test lazy-regression-tests
"""
import sys
import os
import re

import unittest

import pdb


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


from lazy_regression_tests._baseutils import set_cpdb, ppp

rpdb = breakpoints = cpdb

from lazy_regression_tests.lazy3.http_validators import (
    HTMLValidationMixin,
    ResponseHTML,
)


from lazy_regression_tests.lazy3 import LazyMixin

from lazy_regression_tests.lazy3 import ValidationDirective, AutoExp


from lazy_regression_tests.lazy3.http_validators import CSSValidator

#################################################################
# Pre-defined lazy-testing
#################################################################

from lazy_regression_tests.lazy3.filters import (
    FilterDirective,
    # takes effect
    RegexRemoveSaver,
)

from lazy_regression_tests.lazy3.http_validators import (
    # provides save-to-file, load-from-file functionality
    # and calls BeautifulSoup to get a DOM
    HtmlFilterManager,
    # operates on a BeautifulSoup DOM, using standard CSS
    # selectors
    CSSRemoveFilter,
)


#################################################################
# These aren't really objects-under-test, they're used to
# simulate a Django-style HTMLResponse.
#################################################################

from lazy_regression_tests.lazy3.helper_tst import (
    Helper,
    get_mock_env,
    get_fake_html_response,
)

di_mock_env = get_mock_env()


DO_SKIPPED_TESTS = False

# pylint: disable=no-member
class LazyMixinBasic(LazyMixin):
    """ base Mixin class for the lazy test framework """

    # 👇 ⚙️ tracks where expectation and received files are saved
    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)

    extension = "html"

    # 👇 ⚙️ Tells the framework what extensions/content to expect
    cls_filters = dict(html=HtmlFilterManager())

    def test_it(self):
        """ fetch data, run validations, regression test """
        try:

            # this is a pretend server, could have been the Django test server for example
            # could be `requests` against a real site
            # anything returning an HTML response would do
            http_response = get_fake_html_response(self)

            # 👇 lazy-testing, in 3 lines of code 👇

            # ResponseHTML "adapts" the standard http_response by tracking attributes
            # like content_type, status_code, headers...
            response = ResponseHTML(http_response)

            # Check validation such as content_type and status code
            self.check_expectations(response=response)

            # Regression test - did we get the same contents as the last time?
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


@unittest.skipUnless(
    DO_SKIPPED_TESTS,
    "flagging this as expectedFailure causes Unexpected success on its subclass",
)
@unittest.expectedFailure
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


class Test_Features_CustomLineValidation(Test_Features_Regex):
    """ This should pass, we are re-using the CSSValidation lookup for `item`"""

    #   👇
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

    # the template used to generate the fake html
    # 🧨 we're missing a title, the greeting and there is no
    # good reason to be aggressive about the timestamp, or the csrf

    template = """
<body>
    It is now<span class="timestamp">fake, fixed, timestamp</span>.<br/>
</body>
"""

    def test_it(self):
        """ fetch data, run validations, regression test """
        try:

            # 👇 turn these off to avoid validation errors
            self.set_expectation("title", active=False)
            self.set_expectation("name", active=False)
            self.filters["html"].set_filter("timestamp", active=False)

            http_response = get_fake_html_response(self)
            response = ResponseHTML(http_response)

            self.check_expectations(response=response)
            tmp = self.assert_exp(response.content, "html")

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


# pylint: disable=import-outside-toplevel


@unittest.expectedFailure
class Test_JSON_Too(LazyMixinBasic, unittest.TestCase):
    """ just connect it to the appropriate filter manager for 
    the extension type
    """

    from lazy_regression_tests.lazy3.filters import JsonFilterManager

    cls_filters = dict(json=JsonFilterManager())
    extension = "json"

    def test_it(self):
        """ fetch data, run validations, regression test """
        try:
            data = dict(var1="the_same", var2="will_change")
            tmp = self.assert_exp(data, self.extension)
            data.update(var2="told you so")
            tmp = self.assert_exp(data, self.extension)
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_YAML(Test_JSON_Too):
    """ hey, most of the work was done by the JSON guys already
    """

    from lazy_regression_tests.lazy3.yaml_validators import YAMLFilter

    extension = "yaml"
    cls_filters = dict(yaml=YAMLFilter())


# pylint: enable=import-outside-toplevel


class Subvar:
    def __init__(self, value):
        self.value = value


class SomethingToTest:
    def __init__(self):
        self.var1 = 11
        self.var2 = 12
        self.var4 = dict(FF="Fantastic")


class Test_YAML_Graphs(Test_YAML):
    @unittest.expectedFailure
    def test_down_the_rabbit_hole(self):
        """ fetch data, run validations, regression test """
        try:
            from yaml import dump as ydump, load as yload

            somethingtotest = SomethingToTest()
            somethingtotest.var3 = Subvar("3")

            yaml_ = ydump(somethingtotest)

            # probably not a good idea with untrusted data
            data = yload(yaml_)

            self.assert_exp(data, self.extension)
            somethingtotest.added_this = dict(somevar="somevalue")
            somethingtotest.var3.value = "3++"

            yaml_ = ydump(somethingtotest)

            # probably not a good idea with untrusted data
            data = yload(yaml_)
            self.assert_exp(data, self.extension)

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


if __name__ == "__main__":

    cpdb = set_cpdb()
    rc = 0
    try:
        rc = unittest.main()
    finally:
        sys.exit(rc)
