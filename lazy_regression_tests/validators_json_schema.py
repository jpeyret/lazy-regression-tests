i  ######################################################
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

from traceback import print_exc as xp

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
undefined = Ellipsis

verbose = "-v" in sys.argv

# just to track regexes
tmp = re.compile("")
regex_class = tmp.__class__


def breakpoints(*args, **kwargs):
    return False


import pdb


def cpdb(**kwds: "Any") -> bool:  # pragma: no cover
    return cpdb.enabled  # type : ignore


cpdb.enabled = False  # type : ignore


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

    def __init__(self, selector, schema, scalar=False):
        try:
            super(JsonSchemaValidator, self).__init__(selector)

            if isinstance(schema, dict):
                self.schema = schema
            elif isinstance(schema, str):
                if ":" in schema:
                    try:
                        self.schema = json.loads(schema)
                    except (ValueError,) as e:  # pragma: no cover
                        if cpdb():
                            pdb.set_trace()
                        raise
                else:
                    with open(schema) as fi:
                        self.schema = json.load(fi)

            self.exp = self.schema
        except (Exception,) as e:  # pragma: no cover
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

            for igot in got:
                validate(instance=igot, schema=self.schema)

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                ppp(self.schema, "schema")
                ppp(igot, "igot")

                pdb.set_trace()
            raise
