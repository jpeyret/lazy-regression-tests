# -*- coding: utf-8 -*-
"""
test lazy-regression-tests
"""

import sys
import os

import unittest

try:
    import unittest.mock as mock
except (ImportError,) as ei:
    import mock  # python 2?

import json
import tempfile


from django.http import HttpResponse

from jinja2 import Template
import datetime

import re


# pylint: disable=unused-import
#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
)

#######################################################
# pylint: enable=unused-import


verbose = "-v" in sys.argv


# pylint: disable=attribute-defined-outside-init

# pylint: disable=missing-function-docstring,missing-class-docstring  #🧨🧨🧨🧨 turn this back on later 🧨🧨🧨🧨

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
from traceback import print_exc as xp  # pylint: disable=unused-import


from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
    fill_template,
    Subber,
    RescueDict,
    Dummy,
    set_breakpoints3,
)

from lazy_regression_tests.utils import InvalidConfigurationException


from lazy_regression_tests.lazy3 import (
    DictValidator,
    ValidationDirective,
    ValidationManager,
    DirectValidator,
    AutoExp,
)


from lazy_regression_tests.lazy3.filters import (
    RegexRemoveSaver,
    DictFilter,
    FilterDirective,
    FilterManager,
    JsonFilterManager,
)

from lazy_regression_tests.lazy3.core import OPT_DIRECTIVE_BASELINE


rescuedict = RescueDict()

import pdb


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


from lazy_regression_tests.lazy3 import LazyMixin

##########################################################
# tests
##########################################################


lzrt_default_t_basename = "%(filename)s %(classname)s %(_testMethodName)s %(lazy_basename_extras)s %(suffix)s %(extension)s"


# dirtemp = tempfile.mkdtemp(prefix="lazy_regression_tests_")


# lzrt_template_dirname = os.path.join(dirtemp, "out")
# lzrt_template_dirname_got = os.path.join(dirtemp, "got")
# lzrt_template_dirname_exp = os.path.join(dirtemp, "exp")
# lzrt_template_dirname_report = os.path.join(dirtemp, "report")


# lzrt_template_basename = lzrt_default_t_basename


# di_mock_env = dict(
#     lzrt_template_dirname=lzrt_template_dirname,
#     lzrt_template_dirname_got=lzrt_template_dirname_got,
#     lzrt_template_dirname_exp=lzrt_template_dirname_exp,
#     lzrt_template_basename=lzrt_template_basename,
#     lzrt_template_dirname_report = lzrt_template_dirname_report,
# )

from lazy_regression_tests.lazy3.helper_tst import *

di_mock_env = get_mock_env()

di_mock_env_baseline = di_mock_env.copy()


di_mock_env_baseline.update(lzrt_directive=OPT_DIRECTIVE_BASELINE)


di_mock_env_no_extras = dict(
    [(k, v.replace("/%(lazy_dirname_extras)s", "")) for k, v in di_mock_env.items()]
)

module_ = "builtins"
module_ = module_ if module_ in sys.modules else "__builtin__"

from lazy_regression_tests.lazy3.http_validators import (
    HtmlFilterManager,
    HTMLValidationMixin,
    ResponseHTML,
    CSSValidator,
    CSSRemoveFilter,
)


def debug_env(self):
    ppp(self.lazy_environ, "lazyenv")


# pylint: disable=no-member
class LazyMixinBasic(LazyMixin, unittest.TestCase):

    """
    basic support functionality for the rest of the tests
    similar in fact to how LazyMixin is normally used.

    """

    cls_filters = dict(html=HtmlFilterManager())

    debug_env = debug_env

    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)

    tmp_formatted_data = None

    extension = "txt"

    def setUp(self):
        """not sure why needed, but need to reset the environment
            to make sure mocked values are taken into account
           This is probably due to some too aggressive optimization,
           i.e. we-dont-expect-env-variables to change during a test run
        """

        self.lazy_environ.acquired = False

    def seed(self, exp, extension=None, suffix=""):
        try:
            try:

                extension = extension or self.extension

                self.assert_exp(exp, extension=extension, suffix=suffix)

                fnp_exp = self.lazytemp.fnp_exp
                self.lazytemp = None
            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                fnp_exp = self.lazytemp.fnp_exp
                self.lazytemp = None
            return fnp_exp

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def get(self, url=None, data={}):
        try:

            tmpl = Template(self.template)
            text = tmpl.render(**data)
            # subber = Subber(self)
            # text = tmpl.render(subber )

            return ResponseHTML(HttpResponse(text))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class HTMLBase(HTMLValidationMixin, LazyMixinBasic):
    cls_validators = [ValidationDirective("title", active=False)]
    cls_filters = dict(
        html=FilterDirective(
            "timestamp",
            filter_=CSSRemoveFilter("span.timestamp", "timestamp", scalar=True),
        )
    )


class Test_Basic(HTMLBase):

    template = """
        <html><body>Hi <span id="name" >{{ name }}</span>! It is now <span class="timestamp">{{ now }}</span>.</body></html>
    """

    name = "Mr. Rabbit"

    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_basic(self):
        """get response"""
        try:

            data = dict(name=self.name, now=datetime.datetime.now())

            response = self.get(data=data)

            self.check_expectations(response=response)
            tmp = self.assert_exp(response.content, "html")

            data["now"] = "a bit later"
            response = self.get(data=data)

            tmp = self.assert_exp(response.content, "html")

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_Validation(Test_Basic):

    template = """
        <html><head><title>Greetings<title></head>
        <body>Hi <span id="name" >{{ name }}</span>! It is now 
        <span class="timestamp">{{ now }}</span>.
        </body></html>
    """

    cls_validators = [
        ValidationDirective(
            "name", exp=AutoExp, validator=CSSValidator("#name", "name")
        ),
        # we have a title now
        ValidationDirective("title", active=True, exp=AutoExp),
    ]
    name = "Pham Nuwen"
    title = "Greetings"


class HTMLCheck(HTMLBase):

    fail_on_validate = None
    fail_on_change = None

    extension = "html"

    def get_data(self):
        data = getattr(self, "data", {}) or dict(
            name=self.name, now=datetime.datetime.now()
        )
        return data.copy()

    def get_response(self):
        return self.get(data=self.get_data())

    @mock.patch.dict(os.environ, di_mock_env)
    def test_it(self):
        """get response"""
        try:

            if self.__class__ in (HTMLCheck,):
                return

            response = self.get_response()

            if self.fail_on_validate:
                try:
                    self.check_expectations(response=response)
                # pragma: no cover pylint: disable=unused-variable
                except (AssertionError,) as e:
                    self.assertTrue(str(self.fail_on_validate) in str(e))
                else:
                    self.fail(
                        "should have failed validation with %s"
                        % (self.fail_on_validate)
                    )

            else:
                self.check_expectations(response=response)

            if self.fail_on_change:
                try:
                    tmp = self.assert_exp(response.content, self.extension)
                # pragma: no cover pylint: disable=unused-variable
                except (AssertionError,) as e:
                    self.assertTrue(str(self.fail_on_change) in str(e))
                else:
                    self.fail(
                        "should have failed change checks with %s"
                        % (self.fail_on_change)
                    )

            else:
                tmp = self.assert_exp(response.content, self.extension)

            tmp = self.assert_exp(response.content, "html")

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_ValidationNonScalar(HTMLCheck):
    """
    each <li> is going to be checked against a regex
    """

    name = "Pham"

    template = """
        <html><head><title>Greetings<title></head>
        <body>Hi <span id="name" >{{ name }}</span>! It is now 
        <span class="timestamp">{{ now }}</span>.
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        </body></html>
    """

    cls_validators = [
        #
        ValidationDirective(
            "list", exp=re.compile("Item"), validator=CSSValidator("li")
        )
    ]


class Test_ValidationNonScalarFail(Test_ValidationNonScalar):
    """
    the regex will fail
    """

    fail_on_validate = "Not Item"

    cls_validators = [ValidationDirective("list", exp=re.compile("Not Item"))]


class Test_ValidationFailLine3(Test_ValidationNonScalar):

    cls_validators = [
        #
        ValidationDirective(
            "list", exp=re.compile("Item"), validator=CSSValidator("li"), active=True
        )
    ]

    name = "Ezr Vinh"
    line3 = "Line3"

    data = dict(line1="Item 11", line2="Item 12", line3=line3, name=name, now="today")

    fail_on_validate = "Line3"

    template = """
        <html><head><title>Greetings</title></head>
        <body>Hi <span id="name" >{{ name }}</span>! It is now 
        <span class="timestamp">{{ now }}</span>.
        <ul>
            <li>{{line1}}</li>
            <li>{{line2}}</li>
            <li>{{line3}}</li>
        </ul>
        </body></html>
    """


class Helper(HTMLValidationMixin, HelperHTML, CheckitMixin):
    """ just some boiler plate code to assist in testing 
        No Lazy-related features on bases yet
    """

    extension = "html"


class Test_Features(Helper, LazyMixinBasic):

    name = "Mr. Rabbit"
    line1 = "Item 1"
    line2 = "Item 2"
    line3 = "Item 3"

    template = """
<title>Greetings</title>
<script>
const csrf_token = '{{csrf}}';
</script>
<body>
    Hi&nbsp;<span id="name">{{ name }}</span>&nbsp;! 
    It is now<span class="timestamp">{{ timestamp }}</span>.
    Your order is:
    <ul>
        <li>{{line1}}</li>
        <li>{{line2}}</li>
        <li>{{line3}}</li>
    </ul>
</body>
    """

    cls_validators = [
        ValidationDirective("title", exp="Greetings"),
        ValidationDirective("name", exp=AutoExp, validator=CSSValidator("#name")),
    ]

    cls_filters = dict(
        html=[
            FilterDirective(
                "timestamp",
                filter_=CSSRemoveFilter("span.timestamp", "timestamp", scalar=True),
            ),
            FilterDirective(
                "csrf", filter_=RegexRemoveSaver("csrf_token", "csrf_token")
            ),
        ]
    )


class Test_Validation_Fail(HTMLBase):

    cls_validators = [
        ValidationDirective(
            "name", exp=AutoExp, validator=CSSValidator("#name", "name")
        ),
        # we have a title now
        ValidationDirective("title", active=True, exp=AutoExp),
    ]

    template = """
        <html><head><title>Greetings<title></head><body>Hi <span id="name" >{{ name }}?</span>! It is now <span class="timestamp">{{ now }}</span>.</body></html>
    """

    title = "Greetings"
    name = "Robert Gu"

    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_fail_name(self):
        """get response"""
        try:

            data = dict(name="Woodcarver", now=datetime.datetime.now())

            response = self.get(data=data)

            try:
                self.check_expectations(response=response)
                self.fail("should have failed name validation")
            except (AssertionError,) as e:
                for text in ["name", "Gu", "Woodcarver"]:
                    self.assertTrue(text in str(e))

            tmp = self.assert_exp(response.content, "html")

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_002_fail_title(self):
        """get response"""
        try:

            data = dict(name=self.name, now=datetime.datetime.now())

            self.template = self.template.replace("Greetings", "Bonjour")
            response = self.get(data=data)

            try:
                self.check_expectations(response=response)
                self.fail("should have failed title validation")
            except (AssertionError,) as e:
                for text in ["title"]:
                    self.assertTrue(text in str(e))

            tmp = self.assert_exp(response.content, "html")

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


if __name__ == "__main__":

    cpdb = set_cpdb()

    sys.exit(unittest.main())
