"""filters.  this basically aggregates imports from elsewhere"""

# ruff: disable[F401]
import re
from abc import abstractmethod
from collections import defaultdict
from inspect import signature
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

from pydantic import BaseModel, Extra, Field, root_validator, validator

from lazy_regression_tests._baseutils import DictFormatter, def_repr
from lazy_regression_tests.common import (
    TU_NOCATCH,
    BFilter,
    ConfigurationException,
    DictFilter,
    Filter,
    FilterMgr,
    LazyTemp,
    PAbstractFilterWrapper,
    PTextFilterWrapper,
    ValidatorTemp,
)


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"

rpdb = breakpoints = cpdb
undefined = NotImplemented
