# load#####################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
)

from operator import attrgetter
import sys
import re
import os
import json

from traceback import print_exc as xp  # pylint: disable=unused-import

#######################################################
# Dependencies
#######################################################

from jsonschema import validate

try:
    from loguru import logger
except (ImportErrro,) as e:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)


#######################################################
# constants
#######################################################
undefined = NotImplemented

verbose = "-v" in sys.argv

# just to track regexes
tmp = re.compile("")
regex_class = tmp.__class__


def breakpoints(*args, **kwargs):
    return False


import pdb


def cpdb(*args, **kwargs):
    "disabled"


def rpdb() -> bool:  # pragma: no cover
    return bool(cache.get("rpdb_enabled") or getattr("rpdb", "enabled", False))


rpdb.enabled = False  # type : ignore


from lazy_regression_tests.utils import first, fill_template, ppp

from lazy_regression_tests.validators import (
    Validator,
    nested_dict_get,
    JsonValidator,
    DictValidator,
)

# /Users/jluc/kds2/py2/bemyerp/pssecurity/schema/sql_acl_rows.json


class JsonSchemaValidator(JsonValidator):
    sourcename = "json"

    def __init__(self, selector, scalar=False):
        try:
            super(JsonSchemaValidator, self).__init__(selector)

            # self.exp = self.schema
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def load_schema(self, exp):
        try:

            if isinstance(exp, dict):
                self.schema = exp
            elif isinstance(exp, str):
                if ":" in exp:
                    try:
                        self.schema = json.loads(exp)
                    except (ValueError,) as e:  # pragma: no cover
                        if cpdb():
                            pdb.set_trace()
                        raise
                else:
                    with open(exp) as fi:
                        self.schema = json.load(fi)

            return self.schema

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def check(
        self, testee: "LazyMixin", exp: Any, t_message: str = None, source_: Any = None
    ):
        try:

            igot = None
            source_ = source_ or self.get_source(testee)
            got = self.get_value(source_)

            if not isinstance(got, list):
                got = [got]

            schema = self.load_schema(exp)

            for igot in got:
                validate(instance=igot, schema=schema)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                ppp(self.schema, "schema")
                ppp(igot, "igot")

                pdb.set_trace()
            raise
