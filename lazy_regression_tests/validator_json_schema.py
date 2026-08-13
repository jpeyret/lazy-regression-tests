"support for https://json-schema.org/ validation"

import unittest
from collections.abc import Mapping
from typing import Any

#################################################################
# Dependencies
#################################################################
import jsonschema

from lazy_regression_tests.basics import Auto, ConfigurationException
from lazy_regression_tests.common import ValidationError, Validator


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


def validate_json_schema(data: Any, testee: unittest.TestCase, validator: Validator):
    """ validate json data using """
    try:

        exp: Mapping = validator.exp
        if not isinstance(exp, Mapping):
            raise ConfigurationException(
                f"{validator.name} :\n  `validator.exp` needs to be a {Mapping}.\n  received:{exp}[{type(exp)}]"
            )

        if not isinstance(data, (list, dict)):
            data = validator.mgr.temp.rawdata

        if not isinstance(data, list):
            data = [data]

        pass

        for got in data:
            try:
                jsonschema.validate(instance=got, schema=exp)
            except (jsonschema.exceptions.ValidationError,) as e: # noqa F841
                raise ValidationError(msg=str(e), validator=validator, exp=exp, got=got)
    # pragma: no cover
    except (ValidationError,):
        raise
    # pragma: no cover 
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


NAME_VALIDATOR = "validate_schema"

json_schema_validator = Validator(
    name=NAME_VALIDATOR, v=validate_json_schema, selector=Auto, active=True
)
