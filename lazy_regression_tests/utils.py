import re
import os
import difflib
from collections import deque, namedtuple
from functools import partial


import pdb

from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
    fill_template,
    Subber,
    RescueDict,
    nested_dict_get,
    nested_dict_pop,
    first,
    getpath,
    DictFormatter,
    UnavailableLibrary as BaseUnavailableLibrary,
)


from traceback import print_exc as xp  # pylint: disable=unused-import

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

undefined = NotImplemented


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


class InvalidConfigurationException(ValueError):
    """ indicates that some configuration is missing or invalid """

    def __init__(self, msg, *args, **kwargs):

        new_message = f"""
❌⚙️❌⚙️❌⚙️❌

{msg}

❌⚙️❌⚙️❌⚙️❌
"""
        super(InvalidConfigurationException, self).__init__(
            new_message, *args, **kwargs
        )


class UnavailableLibrary(BaseUnavailableLibrary):
    """ exception with message detailing what was not installed 
        with emoji banner 
    """

    exception_cls = InvalidConfigurationException

    def __getattr__(self, *args, **kwargs):
        """ throw errors on any access """
        raise self.exception_cls(self)

    # and reroute call
    __call__ = __getattr__
