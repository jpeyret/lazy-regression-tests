""" support jsonschema based validations 

see https://pypi.org/project/jsonschema/

This is still somewhat experimental

"""

#################################################################
# debugging support
#################################################################
# pylint: disable=unused-import

import pdb

from traceback import print_exc as xp
from pprint import pprint as xpp

from lazy_regression_tests._baseutils import first, ppp, getpath


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
    import jsonschema.exceptions
# pragma: no cover pylint: disable=unused-variable
except (ImportError,) as e:

    class Foo:
        """dummy class"""

    # this will throw an InvalidConfigurationError on any access to ydump
    # telling you to install yaml
    from .common import UnavailableLibrary

    ValidationError = Exception

    jsonschema = Foo
    jsonschema.exceptions = Foo
    jsonschema.exceptions.ValidationError = NotImplementedError

    validate = UnavailableLibrary(name=Foo.__module__, missing="jsonschema")


undefined = NotImplemented


from lazy_regression_tests.validators import DictValidator


class JsonSchemaValidator(DictValidator):
    """
    This is still somewhat experimental
   Implements jsonchema based validations 
    """

    def __init__(self, sourcename: str = "data", selector: str = None, cargo=None):
        """ init """
        try:
            self.sourcename = sourcename
            self.cargo = cargo
            assert isinstance(sourcename, (str, None.__class__))
            self.selector = selector
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def get_value(self, source_):

        if self.selector is None:
            return source_
        else:
            return getpath(source_, self.selector)

    def check(self, name: str, testee: "LazyMixin", exp: dict, sources: dict):
        """ validate using the schema """

        try:

            igot = None
            source_ = self.get_source(testee, **sources)
            got = self.get_value(source_)

            if not isinstance(got, list):
                got = [got]

            for igot in got:
                try:
                    validate(instance=igot, schema=exp)
                # pragma: no cover pylint: disable=unused-variable
                except (jsonschema.exceptions.ValidationError,) as e:
                    testee.fail(e)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                ppp(exp, "schema")
                ppp(igot, "igot")

                pdb.set_trace()
            raise
