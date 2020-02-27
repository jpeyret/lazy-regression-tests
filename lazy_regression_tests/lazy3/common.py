""" this file provides common functionality and constants to the others 
    
    DO NOT import anything lazy in it other than utils/baseutils otherwise
    there is a strong chance for circular import issues.

"""

import pdb

import sys

verbose = "-v" in sys.argv

undefined = NotImplemented

OPT_DIRECTIVE_SKIP = "skip"
OPT_DIRECTIVE_BASELINE = "baseline"
OPT_DIRECTIVE_NODIFF = "nodiff"

from lazy_regression_tests.utils import (
    InvalidConfigurationException,
    ppp,
    UnavailableLibrary,
)


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


def format_assertion_error(
    testee: "TestCase", assert_exc: AssertionError, validator=None, name: str = None
):
    """ enhance AssertionError's message, if possible """

    try:
        new_message = f"""

❌❌❌❌❌❌❌

Validation failure @ {name} [{validator}]:

{assert_exc}

❌❌❌❌❌❌❌
"""

        assert_exc.args = (new_message,)

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise assert_exc
