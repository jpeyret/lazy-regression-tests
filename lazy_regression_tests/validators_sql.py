from typing import Any, Callable
import lazy_regression_tests.providers as providers
from lazy_regression_tests.common import LazyTemp, ConfigurationException

import sqlparse


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


class SQL_Provider(providers.PAbstractExtProvider):
    """
    formatting is really the only thing needed for sql work, otherwise
    it's essentially a TextExtProvider.
    """

    TYPE_RAW = str

    @classmethod
    def datain_to_str(cls, data: Any, checker: "Checker", temp: LazyTemp = None) -> str:
        """data to str"""
        try:

            if data is None:
                return ""

            if not isinstance(data, str):
                raise ConfigurationException(
                    f"{cls}.unsupported data type {type(data)=}"
                )

            data = sqlparse.format(data, reindent=True, keyword_case="upper")
            return data
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def prep_rawdata(self, checker: "Checker", data: Any) -> Any:
        """convert data if needed"""
        try:

            if data is None:
                return data

            raise ConfigurationException(f"{self}.unsupported data type {type(data)=}")
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


providers.di_ext_provider["sql"] = SQL_Provider()
