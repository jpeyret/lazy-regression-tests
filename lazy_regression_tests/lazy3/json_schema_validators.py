""" support jsonschema based validations 

see https://pypi.org/project/jsonschema/
"""

#################################################################
# debugging support
#################################################################
# pylint: disable=unused-import

import pdb

from traceback import print_exc as xp
from pprint import pprint as xpp

from lazy_regression_tests.utils import first, ppp


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

#######################################################
# and Typing...
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
)

#######################################################


# pylint: enable=unused-import


#######################################################
# Dependencies
#######################################################


try:
    from jsonschema import validate
# pragma: no cover pylint: disable=unused-variable
except (ImportError,) as e:

    class Foo:
        """dummy class"""

    # this will throw an InvalidConfigurationError on any access to ydump
    # telling you to install yaml
    from .common import UnavailableLibrary

    validate = UnavailableLibrary(name=Foo.__module__, missing="jsonschema")


undefined = NotImplemented


from lazy_regression_tests.lazy3.validators import DictValidator


class JsonSchemaValidator(DictValidator):
    """ implements jsonchema based validations """

    # def __init__(self, sourcename: str = "data", cargo=None):
    #     """ init """
    #     try:
    #         self.sourcename = sourcename
    #         self.cargo = cargo
    #         assert isinstance(sourcename, str)
    #         self.selector = None
    #     except (
    #         Exception,
    #     ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
    #         if cpdb():
    #             pdb.set_trace()
    #         raise

    # def get_value(self, source_):
    #     return source_

    def check(self, name: str, testee: "LazyMixin", exp: dict, sources: dict):

        # def check(
        #     self, testee: "LazyMixin", exp: dict, t_message: str = None, source_: Any = None
        # ):
        try:

            igot = None
            source_ = self.get_source(testee, **sources)
            got = self.get_value(source_)

            if not isinstance(got, list):
                got = [got]

            for igot in got:
                validate(instance=igot, schema=exp)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                ppp(exp, "schema")
                ppp(igot, "igot")

                pdb.set_trace()
            raise
