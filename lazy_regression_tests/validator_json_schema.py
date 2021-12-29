"support for https://json-schema.org/ validation"

from typing import Any
import unittest
from lazy_regression_tests2.common import Validator, ValidationError
from lazy_regression_tests2.basics import ConfigurationException, Auto

from collections.abc import Mapping

#################################################################
# Dependencies
#################################################################
import jsonschema


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

        # breakpoint() #🛑
        pass

        for got in data:
            try:
                jsonschema.validate(instance=got, schema=exp)
            except (jsonschema.exceptions.ValidationError,) as e:
                raise ValidationError(msg=str(e), validator=validator, exp=exp, got=got)
    # pragma: no cover
    except (ValidationError,):
        raise
    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            breakpoint()
        raise


NAME_VALIDATOR = "validate_schema"

json_schema_validator = Validator(
    name=NAME_VALIDATOR, v=validate_json_schema, selector=Auto, active=True
)
