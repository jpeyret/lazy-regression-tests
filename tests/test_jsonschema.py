# -*- coding: utf-8 -*-
"""
test json_schema  - requires `jsonschema`
"""
import pdb
import sys

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
)

#######################################################
# pylint: enable=unused-import


verbose = "-v" in sys.argv


# pylint: disable=attribute-defined-outside-init

# pylint: disable=missing-function-docstring,missing-class-docstring  #🧨🧨🧨🧨 turn this back on later 🧨🧨🧨🧨


from lazy_regression_tests.helper_tst import get_mock_env


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
from traceback import print_exc as xp  # pylint: disable=unused-import


from lazy_regression_tests._baseutils import set_cpdb


from lazy_regression_tests import LazyMixin

from lazy_regression_tests import ValidationDirective


from lazy_regression_tests.json_schema_validators import JsonSchemaValidator
from lazy_regression_tests.filters import JsonFilterManager


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


##########################################################
# a Basic JSON Schema validation
##########################################################

valid_auth_display = {
    "type": "object",
    "properties": {
        "authorizedactions": {"type": "integer"},
        "displayonly": {"type": "integer"},
    },
    "required": ["authorizedactions", "displayonly"],
}


# pylint: disable=no-member
class LazyMixinBasic(LazyMixin):

    """
    bring in basic lazytest behavior 
    not testing with assert_exp however.
    """

    data = dict(authorizedactions=3, displayonly=0)

    cls_filters = dict(json=JsonFilterManager())
    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)

    extension = "json"

    exp_fail = False

    def test_it(self):
        """ call the validations

        - if exp_fail is set, 
          -  make sure you get an AssertionError 
          -  and that `exp_fail` appears in the assertion error message

        - otherwise behave as usual, i.e. fail on an assertion error

        """
        try:
            data = self.data.copy()

            if not self.exp_fail:
                self.check_expectations(data=data)
            else:
                try:
                    self.check_expectations(data=data)
                    self.fail(f"expected {self.exp_fail}")
                # pragma: no cover pylint: disable=unused-variable
                except (AssertionError,) as e:
                    self.assertTrue(
                        str(self.exp_fail) in str(e), f"expected {self.exp_fail} in {e}"
                    )

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_AuthDisplay(LazyMixinBasic, unittest.TestCase):

    data = dict(authorizedactions=3, displayonly=0)

    cls_validators = [
        ValidationDirective(
            "valid1",
            exp=valid_auth_display,
            validator=JsonSchemaValidator(),
            active=True,
        )
    ]


class Test_AuthDisplayBad(Test_AuthDisplay):

    displayonly = "XXX"
    data = dict(authorizedactions=3, displayonly=displayonly)
    exp_fail = displayonly


valid_carrots = {
    "type": "object",
    "properties": {"carrots": {"type": "integer"}},
    "required": ["carrots"],
}


class Test_MultiChecks(Test_AuthDisplay, unittest.TestCase):

    cls_validators = [
        ValidationDirective(
            "valid_self",
            exp=valid_carrots,
            validator=JsonSchemaValidator(sourcename=None, selector="pantry.veggies"),
            active=True,
        )
    ]

    def setUp(self):
        self.pantry = dict(veggies=dict(carrots=5))


class Test_MultiCheckFail(Test_MultiChecks):

    displayonly = "XXX"
    data = dict(authorizedactions=3, displayonly=displayonly)
    exp_fail = displayonly


if __name__ == "__main__":

    cpdb = set_cpdb()

    sys.exit(unittest.main())
