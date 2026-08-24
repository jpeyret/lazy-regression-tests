"""
Test verbose flag
Do not test generic lazy behavior here, only the verbose-dependent debug code
"""
# -*- coding: utf-8 -*-
import sys
import unittest

import lazy_regression_tests.core_assist2 as core_assist2
import lazy_regression_tests.validators as validators

#################################################################
# Dependencies
#################################################################
import pytest
from lazy_regression_tests.tests.helper_tst import TData
from lazy_regression_tests.utils import set_breakpoints3, set_cpdb, set_rpdb


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

if __name__ == "__main__":
    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints


# force verbosity flag
verbose = core_assist2.verbose = validators.verbose = True


class Test_Verbose(unittest.TestCase):
    " test verbose == True code"

    def test_type_fail(self):
        "test a exp/got type fail"

        class Tester(metaclass=core_assist2._LazyMeta):
            "test"
            cls_validators = dict(
                dict=[
                    dict(
                        name="status_code",
                        exp=200,
                        v=validators.check_equal,
                        selector=validators.Selectors.name,
                    )
                ]
            )

        testee = Tester()
        data = TData(status_code="200")
        checker = testee._lz.dict
        v = checker.v
        with pytest.raises(validators.ValidationError) as _tmp:
            v(data)


if __name__ == "__main__":
    sys.exit(unittest.main())
