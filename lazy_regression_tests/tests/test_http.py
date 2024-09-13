""" Test HTTP"""
# -*- coding: utf-8 -*-
import sys
import unittest
import unittest.mock as mock
import os
import datetime
from pathlib import Path

from typing import Any

#################################################################
# Dependencies
#################################################################
import pytest
from bs4 import element

#################################################################
# re-use v2
#################################################################


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

from lazy_regression_tests.core_assist2 import _LazyMeta

from lazy_regression_tests.tests.helper_tst import get_mock_env
from lazy_regression_tests.constants import OPT_DIRECTIVE_BASELINE


di_mock_env = get_mock_env()
di_mock_env_baseline = di_mock_env.copy()
di_mock_env_baseline.update(lzrt_directive=OPT_DIRECTIVE_BASELINE)

#################################################################


from lazy_regression_tests.utils  import (
    set_cpdb,
    set_rpdb,
    set_breakpoints3,
    ppp,
    first,
    Subber,
)


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

if __name__ == "__main__":
    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints


import lazy_regression_tests.core_assist2 as core_assist2
import lazy_regression_tests.validators as validators
import lazy_regression_tests.filters as filters
from lazy_regression_tests.tests.helper_tst import (
    get_fake_response,
    TData,
    get_fake_response_from_html,
)

# force verbosity flag
verbose = core_assist2.verbose = validators.verbose = True

from lazy_regression_tests.validators_http import (
    validator_html,
    Validator,
    validator_json,
)
from lazy_regression_tests.common import ValidationError


do_test_assertsame = os.getenv("do_test_assertsame")


class Base(unittest.TestCase):
    "base functionality"

    ext: str = "html"

    template = """
        <html><head><title>{{title}}</title></head>
        <body>Hi <span id="name" class="field" >{{ name }}</span>! It is now 
        <span class="timestamp">{{ now }}</span>.
        </body></html>
    """
    name = "Pham Nuwen"
    title = "Greetings"

    def get_cls_tst(self):
        class Testee(unittest.TestCase, metaclass=_LazyMeta):
            title = self.title
            name = self.name
            cls_validators = dict(html=validator_html, http_json=validator_json)

            cls_filters = dict(
                html=[
                    dict(name="timestamp", f=".timestamp"),
                    # dict()
                ],
                http_json=dict(name="timestamp"),
            )

            lazy_filename = Path(__file__).stem

        return Testee

    @mock.patch.dict(os.environ, di_mock_env_baseline)
    def seed(self, data, ext: str = None):
        try:
            try:
                ext = ext or self.ext
                testee = self.cls_tst()
                extlz: core_assist2.Checker = getattr(testee._lz, ext)
                return extlz.assert_same(got=data)

            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                pass

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def get_fake_response(
        self, data={}, status=200, content_type="text/html; charset=utf8"
    ):
        data = Subber(data, dict(name=self.name, title=self.title))
        response = get_fake_response(
            self.template, data=data, status=status, content_type=content_type
        )
        response.html = response.content.decode("UTF-8")

        return response

    def setUp(self):
        "setUp"

        self.response = self.get_fake_response()
        self.cls_tst = self.get_cls_tst()


class Test_Validation(Base):
    def setUp(self):
        "setUp"
        self.now = datetime.datetime.now()
        super(Test_Validation, self).setUp()

    def custom_name_validation(
        self, values, testee: unittest.TestCase, validator: Validator
    ):
        "custom validation as a method"

        value: element.Tag = first(values)
        self.assertEqual("span", value.name)
        self.assertEqual(self.name, value.text)
        # test css class
        self.assertIn("field", value.attrs["class"])
        return True

    def test_custom_validations(self):
        """test"""
        try:

            testee = self.cls_tst()
            v = testee._lz.html.v

            # adding a CSS lookup
            validate_name = Validator(
                name="name", selector="#name", v=self.custom_name_validation
            )

            def custom_title_validation(
                values: Any, testee: unittest.TestCase, validator: Validator
            ):
                """ custom validation via bs.select"""
                try:

                    self.assertIsInstance(values, list)
                    self.assertEqual(1, len(values))
                    for value in values:
                        testee.assertIsInstance(value, (element.Tag,))

                    value = first(values)

                    testee.assertEqual(testee.title, value.text)

                    return value
                # pragma: no cover pylint: disable=unused-variable
                except (Exception,) as e:
                    if cpdb():
                        breakpoint()
                    raise

            v.validators.append(validate_name)

            v_title = testee._lz.html.validators["title"]
            v_title.v = custom_title_validation

            v(self.response)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_basics(self):
        """test"""
        try:

            testee = self.cls_tst()
            v = testee._lz.html.v

            # adding a CSS lookup
            validate_name = Validator(
                name="name", selector="#name", v=validators.check_equal
            )

            v.validators.append(validate_name)
            self.assertEqual(validator_html.__class__, v.__class__)

            v(self.response)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class Test_Validation2(Test_Validation):
    title = "Hello"
    name = "Ravna"


class Test_Assert_Json(Base):

    ext = "http_json"

    def get_response(self, now: Any = None):
        di = dict(timestamp=(now or datetime.datetime.now()), name="John Henry")

        return get_fake_response_from_html(di, content_type="application/json")

    def setUp(self):
        try:
            self.cls_tst = self.get_cls_tst()
            response = self.get_response(now="at start")
            self.seed(data=response)
            self.testee = self.cls_tst()
            self.testee._testMethodName = self.__class__.__name__.lower()
            self.checker: Checker = self.testee._lz.http_json
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    @unittest.mock.patch.dict(os.environ, di_mock_env)
    def test_404(self):
        "should raise a validation error"
        try:
            response = self.get_response(now="a bit later")
            response.status_code = 404
            with pytest.raises(ValidationError):
                self.checker.v(response)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    @unittest.mock.patch.dict(os.environ, di_mock_env)
    def test_001_basic(self):
        """get response"""
        try:

            testee = self.testee
            checker: core_assist2.Checker = testee._lz.http_json

            response = self.get_response(now="a bit later")
            checker.v(response)
            tmp2 = checker.assert_same(got=response)

            self.assertTrue("timestamp" in str(tmp2._filtered.timestamp))
            self.assertIsInstance(checker.validators.get("status_code"), Validator)

            self.assertIsInstance(
                checker.f.named_filters["timestamp"], filters.DictFilter
            )
            self.assertIsInstance(tmp2.rawdata, dict)

        except (Exception,) as e:

            if verbose:
                checker.show()
                print(e)
            if cpdb():
                breakpoint()
            raise


# @unittest.skipUnless(do_test_assertsame, "set $do_test_assertsame")
class Test_Assert_Same(Base):
    def setUp(self, now=None):
        "setUp"

        self.response = self.get_fake_response(
            data=dict(
                name=self.name, title=self.title, now=now or datetime.datetime.now()
            )
        )
        self.cls_tst = self.get_cls_tst()
        self.seed(data=self.response)

    @unittest.mock.patch.dict(os.environ, di_mock_env)
    def test_001_basic(self):
        """get response"""
        try:

            testee = self.cls_tst()

            lz = testee._lz
            extlz: core_assist2.Checker = lz.html

            v = extlz.v

            response = self.get_fake_response(
                data=dict(name=self.name, title=self.title, now="a bit later")
            )

            tmp = v(response)
            tmp2 = extlz.assert_same(got=response)

            self.assertIs(tmp, tmp2)

            self.assertTrue(
                "timestamp" in str(tmp2._filtered.timestamp),
                "expected :'timestamp' in %s" % (tmp2._filtered.timestamp),
            )

        except (Exception,) as e:
            print(tmp.soup.prettify())
            if cpdb():
                breakpoint()
            raise


if __name__ == "__main__":

    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints

    if "-v" in sys.argv or "--verbose" in sys.argv:
        verbose = core_assist2.verbose = validators.verbose = True
    sys.exit(unittest.main())
