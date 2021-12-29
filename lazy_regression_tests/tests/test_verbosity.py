""" 
Test verbose flag 
Do not test generic lazy behavior here, only the verbose-dependent debug code
"""
# -*- coding: utf-8 -*-
import sys
import unittest
import os

#################################################################
# Dependencies
#################################################################
import pytest

from bemyerp.lib._baseutils import set_cpdb, set_rpdb, set_breakpoints3


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

if __name__ == "__main__":
    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints

print(f"\n\n\n{os.getcwd()=}\n\n\n")

import lazy_regression_tests2.core_assist2 as core_assist2
import lazy_regression_tests2.validators as validators
from lazy_regression_tests2.tests.helper_tst import TData

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
        checker = testee.lz.dict
        v = checker.v
        with pytest.raises(validators.ValidationError) as tmp:
            v(data)


if __name__ == "__main__":
    sys.exit(unittest.main())
