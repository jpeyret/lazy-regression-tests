""" Django-specific validations"""

import unittest

from django.forms.utils import ErrorDict

from lazy_regression_tests.basics import ValidationError
from lazy_regression_tests.validators import AutoExp, Validator


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


def check_form_errors(data: ErrorDict, testee: unittest.TestCase, validator: Validator):
    """ check Django form errors """
    try:

        exp = validator.exp
        if exp is AutoExp:
            expectations = {}
        else:
            expectations = validator.exp.copy()

        for fieldname, info in data.get_json_data().items():
            got = set([v["code"] for v in info])

            exp = expectations.pop(fieldname, None)
            if exp is None:
                msg = f"{fieldname=} unexpected error(s): {got}"
                raise ValidationError(msg, exp=exp, got=got, validator=validator)

            if isinstance(exp, str):
                exp = set(exp.split())
            else:
                exp = set(exp)

            if exp != got:
                msg = f"{fieldname=} unexpected error(s): {got}"
                raise ValidationError(msg, exp=exp, got=got, validator=validator)

        if expectations:
            msg = f"missing validation errors on fields {expectations.keys()}"
            raise ValidationError(msg, exp=expectations, got=None, validator=validator)

        return 1

    # pragma: no cover 
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise
