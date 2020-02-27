# -*- coding: utf-8 -*-
"""
test lazy-regression-tests for json_schema
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


di_mock_env = get_mock_env()

di_mock_env_baseline = di_mock_env.copy()
di_mock_env_baseline.update(lzrt_directive=OPT_DIRECTIVE_BASELINE)

module_ = "builtins"
module_ = module_ if module_ in sys.modules else "__builtin__"

# pylint: disable=no-member
class LazyMixinBasic(LazyMixin):

    """
    """

    cls_filters = dict(json=JsonFilterManager())
    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)

    extension = "json"


class Base(LazyMixinBasic, unittest.TestCase):
    def test_it(self):
        """test it"""
        try:
            raise NotImplementedError("test_it(%s)" % (locals()))
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


if __name__ == "__main__":

    cpdb = set_cpdb()

    sys.exit(unittest.main())
