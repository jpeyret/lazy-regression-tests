import pdb
import json

from traceback import print_exc as xp
from pprint import pprint as xpp

#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
)
from bemyerp.pssystem.typing_ import T_options

# if TYPE_CHECKING:
#    from bemyerp.xxx import yyy

#######################################################


undefined = NotImplemented

#######################################################
# Dependencies
#######################################################


try:
    from jsonschema import validate
# pragma: no cover pylint: disable=unused-variable
except (ImportError,) as e:
    validate = undefined


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


from lazy_regression_tests.utils import first, fill_template, ppp


from lazy_regression_tests.lazy3.validators import Validator


class JsonSchemaValidator(Validator):
    def __init__(self, sourcename: str = "data", cargo=None):
        try:
            self.sourcename = sourcename
            self.cargo = cargo
            assert isinstance(sourcename, str)
            self.selector = None
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def get_value(self, source_):
        return source_

    def check(
        self,
        name: str,
        testee: "LazyMixin",
        exp: dict,
        sources: dict,
        t_message: str = None,
        source_: Any = None,
    ):

        # def check(
        #     self, testee: "LazyMixin", exp: dict, t_message: str = None, source_: Any = None
        # ):
        try:

            igot = None
            # source_ = source_ or self.get_source(testee)
            source_ = source_ or self.get_source(testee, **sources)
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
