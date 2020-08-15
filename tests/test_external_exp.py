# -*- coding: utf-8 -*-
"""
test json_schema  - requires `jsonschema`
"""
import pdb
import sys
import json
import unittest


# pylint: disable=unused-import
#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
    Dict,
)

#######################################################
# pylint: enable=unused-import


undefined = NotImplemented
verbose = "-v" in sys.argv


# pylint: disable=attribute-defined-outside-init

# pylint: disable=missing-function-docstring,missing-class-docstring  #🧨🧨🧨🧨 turn this back on later 🧨🧨🧨🧨


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
from traceback import print_exc as xp  # pylint: disable=unused-import


from lazy_regression_tests.helper_tst import get_mock_env
from lazy_regression_tests.filters import DictFilter, FilterDirective
from lazy_regression_tests._baseutils import set_cpdb, ppp
from lazy_regression_tests import NoTstMixin
from lazy_regression_tests import ValidationDirective
from lazy_regression_tests.json_schema_validators import JsonSchemaValidator
from lazy_regression_tests.filters import JsonFilterManager


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


##########################################################
# a Basic JSON Schema validation
##########################################################


# pylint: disable=no-member
class LazyMixinBasic(NoTstMixin):

    """
    bring in basic lazytest behavior 
    not testing with assert_exp however.
    """

    cls_filters = dict(json=JsonFilterManager())
    extension = "json"

    exp_fail = False


class NonTst(LazyMixinBasic):

    data_exp = dict(a=1, b=2)
    data_got = dict(a=1, b=2)

    def __init__(self, mgr):
        self.mgr = mgr

    def do_it(self):
        try:
            self.assert_exp(self.data_got, self.extension, external_exp=self.data_exp)
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_Base(unittest.TestCase):

    class_to_check = NonTst
    exp_equal = undefined

    def check(self):
        "do-nothing"

    def setUp(self):
        self.worker = self.class_to_check(self)
        if self.exp_equal is undefined:
            self.exp_equal = self.worker.data_exp == self.worker.data_got

    def test_it(self):
        """docstring"""
        try:
            self.worker.do_it()
            self.assertEqual(self.exp_equal, self.worker.lazytemp.equal)
            self.check()

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Unequal(NonTst):
    data_got = dict(a=1)


class Test_Unequal(Test_Base):
    class_to_check = Unequal
    exp_equal = False


class UnequalFiltered(Unequal):

    di_varying = dict(b=None)

    cls_filters: "T_FilterParam" = dict(
        json=FilterDirective("changing", DictFilter(di_varying, "changing"))
    )


class EqualFiltered(Unequal):

    data_got = dict(a=1, b=2)

    di_varying = dict(b=None)

    cls_filters: "T_FilterParam" = dict(
        json=FilterDirective("changing", DictFilter(di_varying, "changing"))
    )


class Test_UnequalFiltered(Test_Base):
    class_to_check = UnequalFiltered
    exp_equal = True

    def check(self):
        try:

            di_got = json.loads(self.worker.lazytemp.formatted_got)
            di_exp = json.loads(self.worker.lazytemp.formatted_exp)

            for key in self.worker.di_varying.keys():
                self.assertFalse(key in di_got, f"{key} should have been filtered out ")
                self.assertFalse(key in di_exp, f"{key} should have been filtered out ")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_EqualFiltered(Test_Base):
    class_to_check = EqualFiltered
    exp_equal = True


if __name__ == "__main__":

    cpdb = set_cpdb()

    sys.exit(unittest.main())
