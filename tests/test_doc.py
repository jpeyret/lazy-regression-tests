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

from lazy_regression_tests.http_validators import HTMLValidationMixin, ResponseHTML


from lazy_regression_tests import LazyMixin

from lazy_regression_tests import ValidationDirective, AutoExp


from lazy_regression_tests.http_validators import CSSValidator

#################################################################
# Pre-defined lazy-testing
#################################################################

from lazy_regression_tests.filters import (
    # a filter class that operates on dictionaries
    DictFilter,
    FilterDirective,
    # works on data, once it has been converted to
    # text and before it gets saved to file or compared
    RegexRemoveSaver,
)

from lazy_regression_tests.http_validators import (
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

from lazy_regression_tests.helper_tst import (
    Helper,
    get_mock_env,
    get_fake_response_from_template,
)

get_fake_html_response = get_fake_response_from_template

di_mock_env = get_mock_env()

verbose = "-v" in sys.argv


DO_SKIPPED_TESTS = False

# pylint: disable=no-member
class LazyMixinBasic(LazyMixin):
    """ base Mixin class for the lazy test framework """

    # 👇 ⚙️ tracks where expectation and received files are saved
    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)

    extension = "html"

    # 👇 ⚙️ Tells the framework what extensions/content to expect
    cls_filters = dict(html=HtmlFilterManager())

    @mock.patch.dict(os.environ, di_mock_env)
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


#################################################################
# PYLINT:
#################################################################
# With this style of Mixin coding where filters and validators
# are composed onto the unittest.TestCase subclasses
# there WILL be many ancestors.  That's the point.
#################################################################

# pylint: disable=too-many-ancestors

#################################################################
# These however are just disabled to make the sample code
# easier to paste into documentation.
#################################################################

# pylint: disable=attribute-defined-outside-init
# pylint: disable=import-outside-toplevel

#################################################################


#  ⚙️   This enables the lazy-test framework     👇
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

    def test_it(self):
        try:
            Test_Features.test_it(self)
        # pragma: no cover pylint: disable=unused-variable
        except (AssertionError,) as e:
            self.assertTrue("Bad" in str(e))


def check_lineitems(testee: "unittest.TestCase", got, validator: "Validator"):
    """
    `got` will be a list of strings here 
    👉keeping this as stand alone function, rather a method of your TestCase
    means it can be used anywhere.  It still behaves just like a test method
    """
    try:
        for igot in got:
            if not igot.endswith("3"):
                testee.assertTrue(igot.startswith("Item"))
    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise


class Test_Features_CustomLineValidation(Test_Features_Regex):
    """ This should pass, we are re-using the CSSValidation lookup for `item`"""

    #   👇
    cls_validators = [ValidationDirective("item", exp=check_lineitems)]  #   👇

    name = "Mr. Rabbit"
    line1 = "Item 1"
    line2 = "Item 2"
    line3 = "Bad line 3"

    def test_it(self):
        Test_Features.test_it(self)


class Test_Turning_ThingsOff(Test_Features):
    """ we don't have a title or a greeting anymore
        and we don't need to filter out the timestamp either
    """

    template = """
<body>
    It is now<span class="timestamp">fake, fixed, timestamp</span>.<br/>
</body>
"""

    def setUp(self):
        # 👇 turn these off to avoid validation errors
        self.set_expectation("title", active=False)
        self.set_expectation("name", active=False)
        self.filters["html"].set_filter("timestamp", active=False)  # 👈 keep it


class Test_404(Test_Features):
    @mock.patch.dict(os.environ, di_mock_env)
    def test_it(self):
        """ if you have a lot of config to access a particular URL
        you don't want to duplicate it all over again to simulate a 
        404.  Yet, your 404 page may not at all have the same contents
        or title.
        """
        try:

            http_response = get_fake_html_response(self)
            response = ResponseHTML(http_response)

            # fake a 404
            response.content = "<div>404, to you, buddy!</div>"
            response.status_code = 404

            # This handles the 404, however, the title and name would error out
            self.set_expectation("status_code", 404)

            # 👇 turn off what you don't need
            constants_keep_on_404 = ["status_code", "content_type"]
            self.check_expectations(
                response=response, lazy_skip_except=constants_keep_on_404
            )

            tmp = self.assert_exp(response.content, "html")

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


#################################################################
# Test JSON and YAML
#################################################################


class Test_JSON_Too(LazyMixinBasic, unittest.TestCase):
    """ just connect it to the appropriate filter manager for 
    the extension type
    """

    from lazy_regression_tests.filters import JsonFilterManager

    cls_filters = dict(json=JsonFilterManager())
    extension = "json"

    exp_fail = "told"

    @mock.patch.dict(os.environ, di_mock_env)
    def test_it(self):
        """ simulate data changes """
        try:
            data = dict(var1="the_same", var2="will_change")
            tmp = self.assert_exp(data, self.extension)
            data.update(var2="told you so")

            if self.exp_fail:
                try:
                    tmp = self.assert_exp(data, self.extension)
                    self.fail(f"should failed with {self.exp_fail}")
                except (AssertionError,) as e:
                    self.assertTrue(
                        str(self.exp_fail) in str(e),
                        f"should have failed with {self.fail} in {e}",
                    )
            else:
                tmp = self.assert_exp(data, self.extension)

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_JSON_Filter(Test_JSON_Too):
    """ let's fix the above error by filtering out the changing key"""

    cls_filters = dict(
        json=FilterDirective(
            "changing",
            # DictFilter work by looking for matching keys in the target dictionary.
            # and then call their value if it's a callable.
            # value=None is the default behavior and just deletes the key in the target
            DictFilter(dict(var2=None), "changing"),
        )
    )


class Test_YAML(Test_JSON_Too):
    """ hey, most of the work was done by the JSON guys already
    """

    from lazy_regression_tests.yaml_validators import YAMLFilter

    extension = "yaml"
    cls_filters = dict(yaml=YAMLFilter())


#################################################################
# Test arbitrary object graphs
#################################################################


class Subvar:
    "dummy class"

    def __init__(self, value):
        """ init """
        self.value = value


class SomethingToTest:
    "dummy class"

    def __init__(self):
        """ init """
        self.var1 = 11
        self.var2 = 12
        self.var4 = dict(FF="Fantastic")


class Test_YAML_Graphs(Test_YAML):
    """ we can look at arbitrary serializable objects 
        For example, if our Order object is always
        intended to have order.customer populated this
        would catch a case where a particular testcase did
        originally have this result, but a latter run
        did not.
    """

    @unittest.expectedFailure
    @mock.patch.dict(os.environ, di_mock_env)
    def test_down_the_rabbit_hole(self):
        """ simulate a changed object graph """
        try:

            from yaml import dump as ydump, safe_load as yload

            somethingtotest = SomethingToTest()
            somethingtotest.var3 = Subvar("3")

            yaml_ = ydump(somethingtotest)

            # probably not a good idea with untrusted data
            data = yload(yaml_)

            somevar = "somevalue"

            self.assert_exp(data, self.extension)
            somethingtotest.added_this = dict(somevar=somevar)
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
