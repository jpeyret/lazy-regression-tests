"""filters"""
from collections import defaultdict
import re
from typing import Protocol, runtime_checkable, Optional, Dict, Any, Union, List
from abc import abstractmethod
from inspect import signature

from lazy_regression_tests._baseutils import DictFormatter, def_repr

from pydantic import BaseModel, Field, validator, root_validator, Extra

from lazy_regression_tests.common import (
    ConfigurationException,
    TU_NOCATCH,
    LazyTemp,
    ValidatorTemp,
    PAbstractFilterWrapper,
    PTextFilterWrapper,
    Filter,
    BFilter,
    DictFilter,
    FilterMgr,
)


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

undefined = NotImplemented
