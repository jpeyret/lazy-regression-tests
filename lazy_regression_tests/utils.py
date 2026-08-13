
# ruff: disable[F401]
import logging
import pdb
from traceback import print_exc as xp  # 

from lazy_regression_tests._baseutils import (
    DictFormatter,
    Dummy,
    RescueDict,
    Subber,
    debugObject,
    disable_cpdb,
    fill_template,
    first,
    force_verbose,
    getpath,
    nested_dict_get,
    nested_dict_pop,
    ppp,
    set_breakpoints3,
    set_cpdb,
    set_rpdb,
)
from lazy_regression_tests._baseutils import (
    UnavailableLibrary as BaseUnavailableLibrary,
)

logger = logging.getLogger("lazy")

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
