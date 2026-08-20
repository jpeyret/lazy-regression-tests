"""
common lazy functionality
"""

import functools
import inspect
import operator
import os
import re
import signal
import sys
import unittest
from abc import abstractmethod
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import Enum
from importlib import import_module
from inspect import signature
from io import StringIO
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
    runtime_checkable,
)

#################################################################
# Dependencies
#################################################################
import pydantic
from pydantic import ConfigDict

import lazy_regression_tests.constants as constants
from lazy_regression_tests._baseutils import (
    DictFormatter,
    Dummy,
    InvalidConfigurationException,
    Subber,
    def_repr,
    fill_template,
)
from lazy_regression_tests._baseutils import (
    oshow as show,
)
from lazy_regression_tests.basics import (
    ALazyRoot,
    Auto,
    AutoExp,
    BFilter,
    ConfigurationException,
    DisableAll,
    ExecInfo,
    ExtAlias,
    MediatedEnvironDict,
    ValidationError,
    get_alias_check_equality,
    get_lazy_logger,
)


def timeout(seconds: float):
    """force a timeout on long-running diffs """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(signal, "SIGALRM"):
                raise RuntimeError("timeout_std requires SIGALRM support")

            def _handle_timeout(signum, frame):
                raise TimeoutError(f"{func.__name__} timed out after {seconds} seconds")

            previous_handler = signal.getsignal(signal.SIGALRM)
            previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL, seconds)
            try:
                return func(*args, **kwargs)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous_handler)
                remaining, interval = previous_timer
                if remaining > 0 or interval > 0:
                    signal.setitimer(signal.ITIMER_REAL, remaining, interval)

        return wrapper

    return decorator


verbose = "-v" in sys.argv
di_ext_provider = {}
undefined = NotImplemented
warning = "\n!!!"

def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"

rpdb = breakpoints = cpdb


#################################################################
# Default validation functions
#################################################################

def _checktypes(got, exp, validator: "Validator"):
    """warn if there was type mismatch"""
    if not isinstance(got, type(exp)):
        if validator:
            selector_msg = f" using {validator.selector=}"
        else:
            selector_msg = ""
        message = f"_checktypes: type mismatch? {selector_msg=}"
        get_lazy_logger().warning(message)


def cpdblazy(*args, **kwargs):
    """conditionally halt on exceptions, activate with `export cpdblazy=1` in bash"""
    return os.getenv("cpdblazy")


class _Control(object):
    """unifies environment and function arguments
    to determine handlers for IOError and AssertionError
    save in the LazyTemp results object as well.
    """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__},options={self.options},env={self.env}"

    def __init__(
        self,
        lazy,
        env: MediatedEnvironDict,
        options,
    ):

        self.lazy = lazy
        self.env = env
        self.options = options

    _save_raw = undefined

    @property
    def save_raw(self):
        """this depend on 2 environmental settings:
        :param lzrt_save_raw_received_data : if it it's set we can do it
        :param lzrt_template_dirname_report : where to put it
        """

        if self._save_raw is undefined:
            res = bool(self.env.get("template_dirname_report"))
            self._save_raw = bool(res and self.env.get("save_raw_received_data"))
        return self._save_raw

    _save_rraw = undefined

    @property
    def save_rraw(self):
        """
        saves Really raw got, before formatting.

        For example if you suspect Beautifulsoup formatting is fixing some html errors that trip
        up the actual page.

        this depend on 2 environmental settings:
        :param lzrt_save_raw_received_data : if it it's set we can do it
        :param lzrt_template_dirname_report : where to put it
        """

        if self._save_rraw is undefined:
            res = bool(self.env.get("template_dirname_report"))
            self._save_rraw = bool(res and self.env.get("save_raw_received_data"))
        return self._save_rraw

    _directive = undefined

    @property
    def directive(self) -> str:
        """
        This value is obtained from the environment variable, type `lzrt_directive`

        To set it on the command line, use standard Unix procedures, i.e. to use baseline behavior:

        `lzrt_directive=baseline pytest ....`
        `lzrt_directive=baseline python ....`

        The directive defines 3 mutually exclusive ways for lazy tests to behave, with an additional
        behavior when it is unset i.e. the default behavior:

        :baseline: this will take any received data, write it to expectations file and return a success
        :nodiff  : a `assertTrue(exp==got)` comparison will be run, rather than an `assertEqual`
        :skip    : lazytesting will not be performed at at all and success is automatic since no asserts
        are run

        default behavior, when unset:

        - `exp` file is loaded and compared to `got` data
        - if the `exp` file is missing:
            - the `got` data is written to both the `exp` and `got` file
            - return success
        """

        if self._directive is undefined:
            res = self._directive = self.env.get("directive", "").strip().lower()
            if res:
                known = {
                    constants.OPT_DIRECTIVE_SKIP,
                    constants.OPT_DIRECTIVE_BASELINE,
                    constants.OPT_DIRECTIVE_NODIFF,
                    constants.OPT_DIRECTIVE_NOASSERT,
                }
                if res not in known:
                    raise ValueError(
                        f" unknown directive {res}.  known directives: {known}"
                    )

        return self._directive

    @property
    def noassert(self):
        return self.directive == constants.OPT_DIRECTIVE_NOASSERT

    def skip(self):
        try:
            return self.directive == constants.OPT_DIRECTIVE_SKIP
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def baseline(self):
        return self.directive == constants.OPT_DIRECTIVE_BASELINE

    def nodiff(self):
        return self.directive == constants.OPT_DIRECTIVE_NODIFF


class LazyTemp:
    """
    This is a reporting datatype that both `assert_same` and `validate` both create on demand,
    as well returning a True or False to be used by the unitest assertion.
    """

    def __repr__(self):
        return "LazyTemp[id=%s]" % (id(self))

    def __init__(self, control, env, testee, provider, vtemp: "ValidatorTemp" = None):
        self.control = control
        self.fnp_exp = self.fnp_got = None
        self.env = env.copy()
        self.message = ""
        self.filtered = Dummy()
        self.testee = testee

        if breakpoints(
            "providerclassname", {"providerclassname": type(provider).__name__}
        ):  # pragma: no cover
            print(f"\n\n!!!providerclassname:{type(provider).__name__}") # debugging
            breakpoint()
            pass

        self.provider = provider
        self.execinfo = ExecInfo()
        self.vtemp = vtemp or self.provider.cls_temp()


class ValidatorTemp:
    "ValidatorMgr options and work area"

    _formatted_got = undefined

    lazytemp: LazyTemp

    errors = {}

    skipshow = ["checker"]
    show = show

    rawdata: Any

    def __repr__(self) -> str:
        "repr"
        return f"{self.__class__.__name__}"

    @property
    def formatted_got(self):
        """filter if needed, then format input data"""
        try:
            if self._formatted_got is undefined:
                # apply filters if not done yet
                # this will also populate self._formatted_got
                if self._filtered is None:
                    _ = self.filtered

                self._formatted_got = self.checker.provider.datain_to_str(
                    self.rawdata, checker=self.checker
                )

            return self._formatted_got

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    _filtered: Optional[Dict[str, Any]] = None

    @property
    def filtered(self):
        """build filtered on the fly, if needed"""
        try:
            if self._filtered is None:
                self._filtered = FilterDict()

                if self.checker.f:
                    self.checker.f.filter(self.data_in)

            return self._filtered
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @filtered.setter
    def filtered(self, di: Dict[str, Any]):
        """update the filtered with new values"""
        try:
            if self._filtered is None:
                self._filtered = FilterDict()

            # not sure why we have to do this, but only one filter pass
            for k, v in di.items():
                if k in self._filtered:
                    continue
                else:
                    self._filtered[k] = v

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    _data_in = undefined

    @property
    def data_in(self):
        return self._data_in

    @data_in.setter
    def data_in(self, value):
        try:
            self.checker.provider.set_data(self.checker, self, value)
            #!!!TODO!!! remove debug
            if value:
                assert self.data_in
                assert self.rawdata
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def __init__(self, checker: "Checker", data_in: Any, **kwargs) -> None:
        "init"
        self.checker = checker
        self.data_in = data_in
        checker.temp = self
        self.__dict__.update(**kwargs)


def nested_get(data: Any, selector: str) -> Any:
    """return a nested dictionary lookup or undefined"""
    try:
        parts = selector.split(".")
        for part in parts:
            if isinstance(data, Mapping):
                data = data.get(part, undefined)
            else:
                data = getattr(data, part, undefined)
            if data is undefined:
                return data
        return data

    # pragma: no cover
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise

    # pragma: no cover
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


@runtime_checkable
class PAbstractExtProvider(Protocol):
    """
    provides services to the FilterMgr that are specific to its extension
    - vetting RawFilters data_in
    - <data>_to_str services
    - dump services

    This class is STRONGLY predicated on being stateless and shared accross validators and filters,
    it doesn't store any data, it just processes data in the Checkers and Temps

    Also supports subclassing for re-use: a `yaml` and a `json` provider will both
    reuse `DictProvider` functionality.
    """

    extension: str
    cls_temp = ValidatorTemp

    TYPE_RAW: Any
    text_based: bool = True

    #  - rename to differentiate
    def check_equal(
        self, testee: unittest.TestCase, validator: "Validator", exp, got
    ) -> bool:
        """check if exp can be considered equal"""
        try:
            if isinstance(got, (list, set)) and isinstance(exp, (list, set)):
                got = set(got)
                exp = set(exp)

            return exp == got
            # return 1

        # pragma: no cover
        except (AssertionError,) as e: # noqa F841
            raise

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    #  - modify to pass in Checker, in order to access ValidatorMgr.config...
    def assert_equal(
        self,
        checker: "Checker",
        testee: unittest.TestCase,
        exp,
        got,
        message=None,
        list_to_set=True,
    ) -> bool:
        """check if exp can be considered equal"""
        try:
            if (
                list_to_set
                and isinstance(got, (list, set))
                and isinstance(exp, (list, set))
            ):
                got = set(got)
                exp = set(exp)

            testee.assertEqual(exp, got, message)
            return True

        # pragma: no cover
        except (AssertionError,) as e: # noqa F841
            raise

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    @abstractmethod
    def prep_rawdata(self, checker: "Checker", data: Any) -> Any:
        """convert data if needed"""

    def strip(self, data: str | Any) -> str | Any:
        if isinstance(data, str):
            return data.strip()
        return data

    def adjust_value_for_validation(
        self,
        checker: "Checker",
        validator: "Validator",
        fn: Callable,
        value: Any,
        exc: Exception = None,
    ):
        """try to adjust for arbitrary validator functions"""
        try:
            raise NotImplementedError()
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def set_data(self, checker: "Checker", temp: ValidatorTemp, value: Any):
        """set data on the temp but format to raw as needed"""
        try:
            if isinstance(value, self.TYPE_RAW):
                temp.rawdata = value
            else:
                temp.rawdata = self.prep_rawdata(checker, value)

            temp.__dict__["_data_in"] = value
            return
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def get_temp(self, checker: "Checker", data_in: Any, **kwargs) -> ValidatorTemp:
        """return temp work"""
        try:
            try:
                hash_ = hash(self.datain_to_str(data_in, checker))
            # pragma: no cover
            except (TypeError,) as e: # noqa F841
                hash_ = hash(f"{id(data_in)}")

            if checker.data_hash == hash_ and checker.temp:
                return checker.temp

            checker.data_hash = hash_

            return self.cls_temp(checker=checker, data_in=data_in, **kwargs)
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def get_filtered_as_str(self, checker: "Checker"):
        """return a string represention of filtered data either for output or
        further processing by TextFilters"""
        try:
            res = checker.provider.datain_to_str(checker.temp.rawdata, checker)
            return res
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    filter_class: BFilter

    def build_filter(self, v_in: Any) -> BFilter:
        "build filter"
        try:
            filter_class = getattr(self, "filter_class", Filter)

            if isinstance(v_in, dict):
                filter2 = filter_class(**v_in)
            elif isinstance(v_in, str):
                filter2 = filter_class(f=v_in)
            else:
                raise NotImplementedError(f"unsupported {v_in}")

            return filter2

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @classmethod
    @abstractmethod
    def datain_to_str(
        cls, data: Any, checker: "Checker", temp: "LazyTemp" = None
    ) -> str:
        """converts data to string.  note:  strip() before return"""

    def select_by_string(
        self,
        validator: "Validator",
        data_in: Any,
        testee: Any,
        selector: str,
        temp: Any,
        rawdata: Any,
    ):
        """select data by string selector"""
        try:
            if isinstance(data_in, Mapping):
                data = data_in
                if "." not in selector:
                    try:
                        res = data[selector]
                        return res
                    except (KeyError,) as e: # noqa F841
                        msg = f"""
{validator.mgr.ext}.{repr(self)}. select_by_string : {e}:
Known keys : {list(data.keys())}"""
                        raise ConfigurationException(msg)
                else:
                    path = ""
                    for part in selector.split("."):
                        path += f".{part}"
                        try:
                            data = data[part]
                        except (KeyError,) as e: # noqa F841
                            msg = f"{repr(self)} : {e}:  {path=} Known keys : {list(data.keys())}"
                            raise ConfigurationException(msg)

                    res = data
                    return res

            else:
                if "." in selector:
                    data = nested_get(data_in, selector)
                    return data
                try:
                    data = getattr(data_in, selector)
                except (AttributeError,) as e: # noqa F841
                    msg = f"{repr(self)} : {e}:  Known fields : {list(vars(data_in).keys())}"
                    raise ConfigurationException(msg)

            return data
        # pragma: no cover
        except (ConfigurationException,) as e: # noqa F841
            if cpdb() and e.allow_cpdb():
                breakpoint()
                pass

            raise
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def prep(self, tmp: Any, data: Any):
        return data

    def write(self, fnp: str | Path, data: str, header: Any = None):
        pa = Path(fnp)

        with pa.open("w") as fo:
            if header:
                fo.write(header)
            fo.write(data)

    def read(self, fnp: str | Path) -> Any:
        pa = Path(fnp)

        with pa.open() as fi:
            res = fi.read()
        return res


def parse_pydantic_validation_error(src):
    """extract some validation error info"""
    try:
        errors = getattr(src, "errors", None)
        if not errors:
            src = src._excinfo[1]
            errors = getattr(src, "errors", None)

        if not errors:
            raise NotImplementedError()

        res = {v["loc"][0]: v for v in errors()}
        return res
    # pragma: no cover
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


#################################################################
# For testing validators
#################################################################


TU_NOCATCH = (
    AssertionError,
    ConfigurationException,
    pydantic.ValidationError,
    ValidationError,
)

TU_DEBUG_NOCATCH = tuple()


def get_immediate_raises(debug: bool) -> Tuple[Exception]:
    """these exceptions are getting thrown back to the caller without debug/cpdb"""
    return TU_DEBUG_NOCATCH if debug else TU_NOCATCH


class FilterDict(dict):
    "hack attribute access"

    def __init__(self, *args, **kwargs):
        "init"
        super(FilterDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def __missing__(self, attrname):
        "list known keys"
        msg = f"unknown filter item `{attrname}`.  known {list(self.__dict__.keys())}"
        raise KeyError(msg)

    def __getattr__(self, attrname):
        "access dict"
        return self[attrname]


#################################################################
# Filter building blocks
#################################################################


@runtime_checkable
class PAbstractFilterWrapper(Protocol):
    "wrapper for protocol"

    __repr__ = def_repr

    def __eq__(self, other):
        """see notes on hash"""
        return self.func == other.func

    def __hash__(self):
        """hash whatever is in self.func
        be careful : the hash here is consider the "pivot point"
        to support updating Filters in succession.

        classA.filterX

        gets _updated_ by

        classB(A).filterY if their hash match.  This allow updating `Filter.active`
        for example, turning a filter on an off in subclasses.

        for that to happen, hash(filterY) needs to == hash(filterX)

        see build_filters_for_class `di.__setitem__(filter2, filter2)`

        This will probably evolve over time, but carefully!
        """
        return hash((self.func))


class PTextFilterWrapper(PAbstractFilterWrapper):
    "wrapper for protocol"

    @abstractmethod
    def match(self, line: str) -> bool:
        """takes a str and returns a bool on match or not"""


class RegexSubstitFilter(BFilter):
    """replaces line contents using regex.sub, if there is a match
    does not cause filtering however, because `filter`'s holdback is always
    False
    """

    f: str
    replace: str
    patre: Any = None
    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    def __init__(self, **kwargs):
        try:
            super().__init__(**kwargs)
            self.patre = re.compile(self.f)
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def filter(self, line: str) -> (bool, str):
        """
        returns
        holdback: False
        line    : transform if the regex was a match

        note:  if the line is usually expected NOT to match
        it is faster to test and then sub on a match.
        """
        try:
            hit = self.patre.search(line)

            if not hit:
                return False, line
            else:
                line2 = self.patre.sub(self.replace, line)
                return False, line2

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


def _check_function_has_one_parameter(v_in: Callable) -> bool:
    """check this function will work with 1 positional parameter"""

    count = 0
    for param in signature(v_in).parameters.values():
        pkind = param.kind

        # standard parameters
        if pkind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
            if param.default is param.empty or not count:
                # first positional or any w.o. default
                count += 1
            else:
                # positionals following will have also defaults
                break

        # BREAK as we know we are done with positionals once we hit these...
        elif pkind == param.VAR_POSITIONAL:
            # but first, we'll count it as a positional if its the first...
            count = 1 if count == 0 else count
            break
        elif pkind in (param.KEYWORD_ONLY, param.VAR_KEYWORD):
            break
        else:
            # shouldn't happen, but...
            raise TypeError(f" unknown {pkind}")

    return count == 1


class Filter(BFilter):
    """text filter"""

    # the filter proper
    f: PTextFilterWrapper

    @pydantic.validator("f", pre=True)
    def build_filter(cls, v_in, values) -> PAbstractFilterWrapper:
        """prep the filter wrapper"""
        try:
            if isinstance(v_in, str):
                v = re.compile(v_in).search
                values["label"] = f"regex.{v_in}"
                return RegexFilterWrapper(v)
            if callable(v_in):
                if not _check_function_has_one_parameter(v_in):
                    raise ValueError(
                        f"""
                                     unsupported {v_in=}. A filter function takes one, and only one, parameter.
                                     `f(a)`     is OK
                                     `f(*args)` is OK
                                     `f()`      is BAD
                                     `f(a,b)`   is BAD
                                     """
                    )

                # TODO: test that a string would work in first parameters, test a bool-capable result
                if not values.get("label"):
                    values["label"] = v_in.__name__
                return TextFilterWrapper(v_in)

            elif isinstance(v_in, BFilter):
                values["label"] = v_in.label
                return v_in.f

            elif isinstance(v_in, PAbstractFilterWrapper):
                return v_in

            raise ValueError(f"unsupported {v_in=}")
        # pragma: no cover
        except (ValueError,) as e: # noqa F841
            pass
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def filter(self, line: str) -> (bool, str):
        """
        returns
        - holdback : bool whether a line should be filtered out
        - line     : (potentially modified in other subclasses)
        """
        if not self.invert:
            res = self.f.match(line)
            if isinstance(res, bool):
                # return the flag and the original line
                return res, line

            # keep a modified line, if provided
            return (res[0], res[1])
        else:
            res = self.f.match(line)
            if isinstance(res, tuple):
                return (not res[0], res[1])

            # return the inversion of the flag and the original line
            return not res, line

    @pydantic.model_validator(mode="after")  # type: ignore
    def _init(self):

        try:
            if self.f is None:
                name = self.name
                if name:
                    name = f".{name}"

                msg = f"{type(self).__name__}{name} could not determine `f` filter for {self}"
                raise ConfigurationException(msg)

            return self
        # pragma: no cover
        except (ConfigurationException,) as e: # noqa F841
            raise
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


class TextFilterWrapper(PTextFilterWrapper):
    "concrete filter"

    def match(self, line: str) -> bool | tuple[bool, str]:
        "does a line match the filter?"

        res = self.func(line)
        if isinstance(res, tuple):
            return res


        return bool(res)

    def __init__(self, func):
        "init"
        self.func = func


class RegexFilterWrapper(TextFilterWrapper):
    """same as TextFilterWrapper, just name different. func is regex.search"""


class RawFilter(Filter):
    """ancestor of `raw` (non-text) filters"""

    raw: bool = True
    f: Any = None
    scalar: bool = False

    @abstractmethod
    def filter(self, vtemp: ValidatorTemp) -> Any:
        """mutate data in place"""


class PDictFilterWrapper(PAbstractFilterWrapper):
    "protocol wrapper"

    @abstractmethod
    def apply(self, data: dict) -> None:
        """mutate a dict in place"""


class DictFilterWrapper(PDictFilterWrapper):
    """wraps dict filtering"""

    def __init__(
        self, di_filt: dict, formatter: Optional[DictFormatter] = None
    ) -> None:

        self.di_filt = di_filt
        self.formatter = formatter or DictFormatter()

        # for hash comparison
        self.func = repr(di_filt.items())

    def apply(self, data: dict) -> Dict[str, Any]:
        """
        mutate dict in place for filtering. return is a dict of
        filtered items by filter name
        """
        try:
            filtered: Dict[str, Any] = {}
            self.formatter.process(
                data, di_formatter=self.di_filt, in_place=True, keep=filtered
            )
            return filtered
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


class DictFilter(RawFilter):
    """filter dictionaries"""

    # the filter proper
    f: Union[dict, PDictFilterWrapper]

    @pydantic.validator("f")
    def build_filter(cls, v_in: Any, values: Dict[str, Any]):
        """prep the filter wrapper"""
        try:
            if isinstance(v_in, PDictFilterWrapper):
                return v_in
            if isinstance(v_in, dict):
                formatter = DictFilterWrapper(v_in)
                return formatter
            raise ValueError(f"unsupported {v_in=}")

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @pydantic.model_validator(mode="after")
    def _init(self):
        """root validator, make sure everything is good, esp `f` filter attribute"""
        try:
            if self.f is None:
                di = {self.name: None}
                f = DictFilterWrapper(di)
                self.f = f

            return self
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def filter(self, data: Union[ValidatorTemp, dict]) -> dict:
        """apply filter and return filtered-out items in a dict"""
        try:
            if not isinstance(data, dict):
                data = data.rawdata
            out = self.f.apply(data)
            return out
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


class _HelperFilterMgr:
    """various lookups and functions, kept out of Pydantic code"""

    __repr__ = def_repr

    def __init__(self, mgr: Optional["FilterMgr"] = None):
        "init"
        self.mgr = mgr

    _named = undefined

    mgr: Optional["FilterMgr"]

    @property
    def named_filters(self) -> Dict[str, BFilter]:
        "return filters that have names"
        if not self.mgr:
            return {}

        if self._named is undefined:
            self._named = {f.name: f for f in self.mgr.filters if f.name}
        return self._named


class FilterMgr(pydantic.BaseModel):
    """chains all the filters for a given extension"""

    ext: str
    filters: List[BFilter] = pydantic.Field(default_factory=list)
    tmp_filtered: Any = None
    tmp_raw: Any = None
    h: _HelperFilterMgr = pydantic.Field(default_factory=_HelperFilterMgr)
    checker: Optional["Checker"] = None

    alias: Optional[str] = None

    @property
    def provider(self) -> PAbstractExtProvider:
        """get Provider"""
        return di_ext_provider[self.alias or self.ext]

    def clone(self):
        """clone a FilterMgr"""
        f2 = self.copy(deep=True, exclude={"checker", "h"})
        f2.checker = None
        f2.h = _HelperFilterMgr(mgr=f2)
        return f2

    @property
    def named_filters(self) -> Dict[str, BFilter]:
        return self.h.named_filters

    model_config = ConfigDict(arbitrary_types_allowed=True, extra=pydantic.Extra.forbid)

    def filter(self, data_in: Any = None) -> str:
        """filter data and return as string representation"""
        try:
            if data_in:
                temp = self.checker.provider.get_temp(
                    checker=self.checker, data_in=data_in
                )
            else:
                temp = self.checker.provider.get_temp(
                    checker=self.checker, data_in=data_in
                )

            assert temp is self.checker.temp, f"{temp=} <> {self.checker.temp=}"

            di_hit = defaultdict(list)
            filters = [filter_ for filter_ in self.filters if filter_.active]

            if not isinstance(temp.rawdata, str):
                rfilters: List[RawFilter] = [filter for filter in filters if filter.raw]
                for filter_ in rfilters:
                    filtered = filter_.filter(temp)
                    if filter_.name:
                        if filter_.scalar:
                            di_hit[filter_.name] = filtered
                        else:
                            di_hit[filter_.name].append(filtered)
                data4textfilter = self.checker.provider.get_filtered_as_str(
                    self.checker
                )

            else:
                data4textfilter = self.checker.provider.get_filtered_as_str(
                    self.checker
                )

            # operate on TextFilters
            tfilters = [filter for filter in filters if not filter.raw]
            if tfilters:
                lines_in = data4textfilter.splitlines()
                lines = []
                for line in lines_in:
                    for filter_ in tfilters:
                        # There are 2 varieties of filters.
                        # The more common type "holds back" lines and puts them into temp.filtered
                        # substitution filters instead format the line, typically to remove or substit something.
                        holdback, line = filter_.filter(line)
                        if holdback:
                            if filter_.name:
                                di_hit[filter_.name].append(line)
                            break
                    else:
                        lines.append(line)

                temp.filtered = di_hit
                res = temp._formatted_got = "\n".join(lines).strip()

                return res
            else:
                temp.filtered = di_hit
                temp._formatted_got = res = data4textfilter.strip()
                return res
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    __call__ = filter

    def __add__(self, value_in):
        """add a validator"""
        try:
            value = None
            if isinstance(value_in, dict):
                value = Filter(**value_in)
            elif isinstance(value_in, Filter):
                value = value_in.copy()

            if value:
                self.filters.append(value)
            else:
                raise ConfigurationException(
                    f"{self.__class__}: could not add Filter from {value_in=}"
                )
            return self

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def show(self, nesting="", file=None):
        "for debugging"
        try:
            file = file or StringIO()
            indent = nesting + "  "
            for f in self.filters:
                f.show(file=file, nesting=indent)
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


#################################################################
# Assert_same
#################################################################


@dataclass
class Checker:
    # howto- hide dataclass field for less noisy debugs
    _lz: ALazyRoot = dataclass_field(repr=False)
    f: FilterMgr
    v: "ValidatorMgr"
    ext: str

    temp: Optional[ValidatorTemp] = None

    lazy_environ = MediatedEnvironDict()

    data_hash: int = 0

    alias: Optional[str] = None

    ENVIRONMENT_VARNAME_ROOT = constants.ENVIRONMENT_VARNAME_ROOT

    def __post_init__(self):
        """link itself to its filters/validators"""
        try:
            alias_v = alias_f = None

            if self.f:
                alias_f = self.f.alias
            else:
                self.f = FilterMgr(ext=self.ext, alias=self.alias)
            self.f.checker = self

            if self.v:
                alias_v = self.v.alias
                self.v.checker = self
            else:
                self.v = ValidatorMgr(checker=self, ext=self.ext, alias=self.alias)

            #  - what about here, to link in the config... we do have its ValidatorMgr...

            self.alias = get_alias_check_equality([alias_f, alias_v])

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @property
    def filters(self):
        return self.f.filters

    @property
    def provider(self) -> PAbstractExtProvider:
        """get Provider"""
        return di_ext_provider[self.alias or self.ext]

    def show(self, file: Any = None, nesting="", showtemp=False):
        """for debugging"""
        try:
            file = file or StringIO()

            indent = nesting + "  "
            if self.f:
                self.f.show(file=file, nesting=indent)

            if self.v:
                self.v.show(nesting=indent, file=file)

            if showtemp and self.temp:
                self.temp.show(nesting=indent, file=file)
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @property
    def validators(self):
        return {val.name: val for val in self.v.validators}

    def get_temp(self, data_in):
        if not self.temp:
            self.temp = self.provider.get_temp(checker=self, data_in=data_in)
        return self.temp

    def assert_same(
        self,
        got: Any,
        suffix: str = "",
        external_exp: Any = undefined,
        reset: bool = False,
        filter_: bool = True,
        **kwargs,
    ):
        """is the data same as the last time?"""
        try:
            if reset:
                self.temp = None

            self.get_temp(data_in=got)

            checker = SameAssertor(checker=self)

            self._lazycheck(
                got, checker=checker, suffix=suffix, filter_=filter_, **kwargs
            )
            return self.temp

        except (AssertionError,) as e: # noqa F841
            # we want to raise a new exception, minus all the info about finding diffs and formatting error
            # messages which is... what lazydiff does

            new_exc = AssertionError(str(e))

            # capture fnp_exp, fnp_got which are used to launch `diff` commands as required
            di = {name: getattr(e, name, None) for name in ["fnp_exp", "fnp_got"]}
            new_exc.__dict__.update(**di)

            # https://docs.python.org/3.3/whatsnew/3.3.html#pep-409-suppressing-exception-context
            # howto- https://stackoverflow.com/a/17092033 - suppress causal exception
            raise new_exc from None
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def _lazycheck(
        self,
        got: Any,
        checker: "SameAssertor",
        suffix: str = "",
        external_exp: Any = undefined,
        metadata_header: str = None,
        lazy_save_got: bool = True,
        lazy_save_exp: bool = True,
        filter_: bool = True,
        **kwargs,
    ) -> LazyTemp:
        try:

            self.lazy_save_got = lazy_save_got
            self.lazy_save_exp = lazy_save_exp
            env = self.lazy_environ
            if not self.lazy_environ.acquired:
                env.clear()
                env.acquire(self.ENVIRONMENT_VARNAME_ROOT)

            self._lazy_control = control = _Control(self, env, checker)


            # only create the lazy temp the first time.
            tmp = self.lazytemp = getattr(self, "lazytemp", None) or LazyTemp(
                control, env, self, provider=self.provider, vtemp=self.temp
            )

            # the environment requests that no diffing or writing take place
            # typically indicated by setting environment variable `lzrt_directive=skip`
            if control.skip():
                return tmp

            # calculate the paths of the exp/got files
            #
            testee = self._lz.testee

            # Issue.011.eval.tabulator
            tmp.fnp_got = fnp_got = checker.get_fnp_save(
                exp_got="got", suffix=suffix, testee=testee, control=control
            )

            tmp.fnp_exp = fnp_exp = checker.get_fnp_save(
                exp_got="exp", suffix=suffix, testee=testee, control=control
            )


            if breakpoints("_lazycheck", {"always": 1}):  # pragma: no cover
                print("\n\n!!!Checker.lazycheck") # debugging
                breakpoint()
                pass

            checker.write_raw(
                provider=self.provider,
                suffix=suffix,
                testee=testee,
                control=control,
                got=got,
            )

            # linefeeds have a tendency to creep in sometimes
            if filter_:
                formatted_got = self.temp.formatted_got
            else:
                formatted_got = checker.checker.provider.datain_to_str(
                    got, checker.checker
                )

            formatted_got = self.provider.strip(formatted_got)


            # at this point, we want to write the received, formatted, data regardless
            if self.lazy_save_got:

                self.provider.write(fnp_got, formatted_got)

            # the newly received data is to be taken as our expectations
            # typically indicated by setting environment variable `lzrt_directive=baseline`
            if control.baseline() and self.lazy_save_exp:

                header = None
                if metadata_header:
                    if isinstance(metadata_header, list):
                        metadata_header = "\n".join(metadata_header)
                    else:
                        metadata_header = str(metadata_header)
                    header = f"""{metadata_header.strip()}
{constants.LAZY_HEADER_SEPARATOR}
"""

                self.provider.write(fnp_exp, formatted_got, header)

                return tmp

            # the environment requests that no diffing or writing take place
            # typically indicated by setting environment variable `lzrt_directive=skip`
            if control.noassert:
                return tmp

            if external_exp is undefined:
                try:
                    exp = self.provider.read(fnp_exp)
                    exp = self.provider.strip(exp)

                    if isinstance(exp, str) and constants.LAZY_HEADER_SEPARATOR in exp:
                        exp = exp.split(constants.LAZY_HEADER_SEPARATOR)[1].strip()

                except (IOError,):
                    # we just want to write the received data as our expectation
                    tmp.execinfo.ioerror_exp = fnp_exp
                    tmp.message = message = "no check because IOError on %s" % (fnp_exp)
                    if self.lazy_save_got:
                        self.provider.write(fnp_exp, formatted_got)
                    return tmp
            else:
                raise NotImplementedError()
                exp = checker.format(tmp, external_exp, None).rstrip()

            # the environment requests only equality is checked, without trying to show details
            # typically indicated by setting environment variable `lzrt_directive=nodiff`
            # this may be desired if the differences could cause timeouts with `assertEqual`
            if control.nodiff():
                tmp.message = message = "exp and got are not equal but diffing disabled"
                if exp != formatted_got:
                    raise testee.fail(message)

            try:
                # supports a timeout mechanism, if the module is available
                self.assertEqualTimed(testee, exp, formatted_got, tmp=tmp, **kwargs)
            except (TimeoutError,) as _e:  # pragma: no cover # noqa F841
                tmp.message = message = (
                    "exp and got are not equal but comparison timed out after %s seconds"
                    % (constants.TIMEOUT_MAXTIME_TO_ALLOW)
                )
                testee.fail(message)

            return self.lazytemp

        except (AssertionError,) as exc: # noqa F841
            for attrname in "fnp_exp fnp_got".split():
                v = getattr(tmp, attrname, undefined)

                if v is not undefined:
                    setattr(exc, attrname, v)

            raise
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


    @timeout(constants.TIMEOUT_MAXTIME_TO_ALLOW)
    def assertEqualTimed(self, testee, exp, got, tmp: LazyTemp, message=None):
        """ comparisons will automatically times out after %s seconds""" % (
            constants.TIMEOUT_MAXTIME_TO_ALLOW
        )

        try:
            self.provider.assert_equal(self, testee, exp, got, message)
        except (AssertionError,) as e: # noqa F841
            raise self.format_assertion_message(e, tmp, testee)
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


    def format_assertion_message(self, ori, tmp: LazyTemp, testee):
        """message thrown on assert_same failures"""


        message = f"""

!!!Regressions found:

Expected contents are in file:
  {tmp.fnp_exp}

Received contents are in file:
  {tmp.fnp_got}

Original exception:
 {ori}

!!!
"""
        exc = ori.__class__(message)
        return exc


#################################################################
# providers
#################################################################


class TextExtProvider(PAbstractExtProvider):
    """support text data"""

    extension = "txt"

    TYPE_RAW = str

    def prep_rawdata(self, checker: "Checker", data: Any) -> Any:
        """convert data if needed"""
        try:
            raise NotImplementedError()
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @classmethod
    def datain_to_str(cls, data: str, checker: "Checker", temp: LazyTemp = None) -> str:
        try:
            if not isinstance(data, str):
                raise ConfigurationException(f"""
data type {type(data)} not supported by {cls.__name__} which supports strings.
known extensions for testcase: {','.join(checker._lz.extensions)}""")
            return data.strip()
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


DEFAULT_PROVIDER = TextExtProvider()

#################################################################
# validators
#################################################################


@runtime_checkable
class ValidatorCheck(Protocol):
    "wrapper for protocol"

    def __repr__(self) -> str:
        "repr"
        return f"{self.__class__.__name__}"

    @abstractmethod
    def is_valid(
        self, value: Any, testee: Any, validator: Any, debug: bool = False
    ) -> bool:
        """run assertion against value"""


class FunctionCheck(ValidatorCheck):
    """basic unit of validation:  calls a wrapped function"""

    def __repr__(self):

        f = self.f

        try:
            sign = inspect.signature(f)
        # pragma: no cover
        except (TypeError,) as e: # noqa F841
            sign = ""

        f_msg = f"{f.__module__}.{f.__name__} {sign}"

        return f"{self.__class__.__name__}:{f_msg}"

    def __eq__(self, o: object) -> bool:
        return self.f == getattr(o, "f", undefined)

    def __hash__(self):
        return hash(self.f)

    def __init__(self, f: Callable) -> None:
        """init"""

        if not callable(f):
            raise ConfigurationException(f"{f=} is not callable")

        self.f = f

    def is_valid(self, value: Any, testee, validator: "Validator") -> bool:
        """
        check if the validation function return True or raises
        AssertionError

        functions with a signature of `(data:Any, testee: unittest.TestCase, validator: Validator)`
        are assumed successful if they dont raise AssertionError/ValidationErrors

        """
        try:
            di = {}

            implicit_res = is_custom_checker(self.f)

            sign = inspect.signature(self.f)
            di_param = dict(sign.parameters)
            di = {}
            if "testee" in di_param:
                di["testee"] = testee
            if "validator" in di_param:
                di["validator"] = validator

            try:
                #  - modify to pass in Checker, in order to access ValidatorMgr.config...
                res = bool(self.f(value, **di))

                # assume custom checkers
                # would have raised an Assertion/ValidationError
                if implicit_res:
                    return implicit_res
                else:
                    if not res:
                        raise ValidationError(
                            validator.name, validator=validator, got=value
                        )

            # pragma: no cover
            except (TypeError,) as e: # noqa F841
                checker = validator.mgr.checker
                value2 = checker.provider.adjust_value_for_validation(
                    checker=checker, validator=self, fn=self.f, value=value, exc=e
                )

                if isinstance(value2, list):
                    res = all([bool(self.f(v, **di)) for v in value2])
                else:
                    res = bool(self.f(value2, **di))

            if not res:
                if implicit_res:
                    return implicit_res
                raise ValidationError(validator.name, validator=validator, got=value2)

            return res
        # pragma: no cover
        except (AssertionError, ConfigurationException) as e: # noqa F841
            raise
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


class Options(pydantic.BaseModel):
    validate_with_validator: bool = False
    validate_with_testee: bool = False


DEFAULT_OPTIONS = Options()

seen = set()


class Validator(pydantic.BaseModel):
    """the core validation mechanism"""

    # name needs to exist right away, rest can be added later
    name: str

    active: Optional[bool] = True
    selector: Optional[Any] = None
    exp: Optional[Any] = None
    v: Optional[ValidatorCheck] = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.name}"

    def __str__(self):
        return f"{self.__class__.__name__}:{str(self.__dict__)}"

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    @pydantic.field_validator("selector")
    @classmethod
    def build_selector(cls, v: Any, info: pydantic.ValidationInfo):

        try:
            try:
                specials = v in Selectors
            except (TypeError,) as e: # noqa F841
                specials = False

            if specials:
                # take the validator's own name as the attribute name
                if v == Selectors.name:
                    return info.data["name"]
                else:
                    raise NotImplementedError(f"{v}")

            return v

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @pydantic.field_validator("v", mode="before")
    @classmethod
    def build_validator(cls, value, info: pydantic.ValidationInfo):
        """prep the validator wrapper"""
        try:
            if value in S_VALIDATIONS:
                return FunctionCheck(f=value)
            if callable(value):
                return FunctionCheck(f=value)
            elif isinstance(value, ValidatorCheck):
                return value
            elif isinstance(value, str) and "." in value:
                modpath, name = value.rsplit(".", maxsplit=1)
                module_ = import_module(modpath)
                value = getattr(module_, name)
                if not isinstance(value, FunctionCheck):
                    value = FunctionCheck(value)

            elif value:
                raise NotImplementedError(f"{cls}.build:value:?")

            return value
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @pydantic.model_validator(mode="before")
    @classmethod
    def pause_for_debug(cls, data: Any) -> Any:
        try:
            name = data.get("name")
            selector = data.get("selector")
            lookup = (cls, name, selector, "ante")

            if (
                breakpoints("pause_for_debug", {"name": name}) and lookup not in seen
            ):  # pragma: no cover
                print(f"\n\n!!!{cls}.pause_for_debug:{name=} {selector=}") # debugging
                seen.add(lookup)
                breakpoint()
                pass

            return data
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @pydantic.model_validator(mode="after")
    @classmethod
    def pause_for_debug_post(cls, data: Any, **kwargs) -> Any:
        try:
            name = data.name

            selector = data.selector

            lookup = (cls, name, selector, "post")

            if (
                breakpoints("pause_for_debug_post", {"name": name})
                and lookup not in seen
            ):  # pragma: no cover
                print(f"\n\n!!!{cls}.pause_for_debug:{name=} {selector=}") # debugging
                seen.add(lookup)
                breakpoint()
                pass

            return data
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def extend(self, val: Union[None, "Validator", Dict[str, Any]] = None, **kwargs):
        try:
            di_update = {}

            if isinstance(val, Validator):
                di = {}
                for k, v in val.dict().items():
                    if k == "name":
                        continue
                    elif k == "options":
                        if v == DEFAULT_OPTIONS:
                            continue
                    elif v is None:
                        continue

                    di[k] = v

                di_update.update(**di)

            di_update.update(**kwargs)

            if not di_update:
                raise ConfigurationException(f" {self}.extend: no values to update")

            dupe = self.copy(deep=True, update=di_update)

            return dupe

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    show = show


def custom_checker(data: Any, testee: unittest.TestCase, validator: Validator) -> None:
    """only to callibrate signature check"""


def custom_checker_wo_none(data: Any, testee: unittest.TestCase, validator: Validator):
    """only to callibrate signature check"""


_callibration_signatures = (
    repr(inspect.signature(custom_checker)),
    repr(inspect.signature(custom_checker_wo_none)),
)


def is_custom_checker(f: Any) -> bool:
    """check signature for a match"""
    try:
        if not callable(f):
            return False

        return repr(inspect.signature(f)) in _callibration_signatures

    # pragma: no cover
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


class ValidatorMgr(pydantic.BaseModel):
    """chains all the validators for a given extension"""

    ext: str
    validators: List[Validator] = pydantic.Field(default_factory=list)
    testee: Optional[unittest.TestCase] = None
    temp: Optional[Any] = None

    checker: Any = None

    alias: Optional[str] = None

    #  - we may want it, but it's probably gonna have to come in via `ExtAlias`
    config: dict[str, Any] | None = None


    def __sub__(self, value_in):
        """logically delete a validator by setting active to False"""
        try:
            try:
                if isinstance(value_in, str):
                    tgt = value_in
                elif isinstance(value_in, dict):
                    tgt = value_in["name"]
                else:
                    raise NotImplementedError()
            except (KeyError, NotImplementedError) as e: # noqa F841
                raise ConfigurationException(
                    f"you need to pass in the name of the validator you wish to delete, not {value_in}"
                )

            di = {v.name: v for v in self.validators}

            try:
                di[tgt].active = False
            except (KeyError,) as e: # noqa F841
                raise ConfigurationException(
                    f"unknown validator {tgt}. known:{'/'.join(di.keys())}"
                )

            return self

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def __add__(self, value_in):
        """add a validator"""
        try:
            value = None
            if isinstance(value_in, dict):
                value = Validator(**value_in)
            elif isinstance(value, Validator):
                value = value_in.copy()

            if value:
                self.validators.append(value)
            else:
                raise ConfigurationException(
                    f"{self.__class__}: could not add validator from {value_in=}"
                )

            return self

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @property
    def provider(self) -> PAbstractExtProvider:
        """get Provider"""
        try:
            lookup = self.alias or self.ext
            return di_ext_provider[lookup]
        # pragma: no cover
        except (KeyError,) as e: # noqa F841
            raise ConfigurationException(f"""
{self.__class__}.provider() {lookup=} not found for {self.ext=} {self.alias=}.
known provider extensions/aliases: {list(di_ext_provider.keys())}""")

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _check_skip(
        self, v, skips: Sequence[str | Any | re.Pattern] | re.Pattern | str | None
    ) -> bool:
        """check if the validator should be skipped"""
        try:
            if not skips:
                return False
            if not isinstance(skips, Sequence):
                skips = [skips]
            for skip in skips:
                if isinstance(skip, str):
                    if v.name == skip:
                        return True
                elif isinstance(skip, re.Pattern):
                    if skip.match(v.name):
                        return True

            return False
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def assert_valid(
        self,
        data,
        debug=False,
        skips: Sequence[str | Any | re.Pattern] | re.Pattern | str | None = None,
    ):
        """runs the validations"""
        try:
            tu_raise = (
                (
                    AssertionError,
                    ConfigurationException,
                    pydantic.ValidationError,
                )
                if not debug
                else tuple()
            )

            self.temp = self.provider.get_temp(checker=self.checker, data_in=data)
            if "noassert" in os.getenv("lzrt_directive", ""):
                return self.temp

            rawdata = self.temp.rawdata

            actuals: List[ActualValidator] = []
            for val in self.validators:
                if not val.active:
                    continue
                if skips and self._check_skip(val, skips):
                    continue

                actual = ActualValidator(mgr=self, **val.model_dump())
                actuals.append(actual)

            for val in actuals:
                if not val.active:
                    continue
                # modify to pass in Checker, in order to access ValidatorMgr.config...
                # `self.checker` ought to do it...
                valid = val.assert_valid(self.testee, rawdata, data)
                if not valid:
                    raise ValidationError(f"{val.name}", validator=val)

            return self.temp

        # pragma: no cover
        except tu_raise as e: # noqa F841
            raise

        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    __call__ = assert_valid

    def extend(self, *adds, ext: str = None, alias: str = None) -> "ValidatorMgr":
        """returns a new ValidationMgr with additional configuration"""
        try:
            # TODO:  delete debug code
            after_val = replacer = add = None


            dupe = self.copy(deep=True)

            after_val = {v.name: v for v in dupe.validators}

            li_add = []
            flatten_to_validators_dicts(li_add, adds)

            add = None

            for add in li_add:
                replacer = None
                is_dict = isinstance(add, dict)
                if is_dict:
                    try:
                        name = add["name"]
                    except (KeyError,) as e: # noqa F841
                        raise ConfigurationException(f"{add} doesn't have a `name`")

                else:
                    try:
                        name = add.name
                    except (AttributeError,) as e: # noqa F841
                        raise ConfigurationException(f"{add} doesn't have a `name`")

                ante = after_val.get(name)
                if ante:
                    if is_dict:
                        replacer = ante.copy(update=add)
                    elif isinstance(add, Validator):
                        replacer = ante.extend(add)
                    else:
                        raise ConfigurationException(f"unhandled {ante=} {add=}")
                else:
                    if is_dict:
                        replacer = Validator(**add)
                    elif isinstance(add, Validator):
                        replacer = add
                    else:
                        raise ConfigurationException(f"unhandled {ante=} {add=}")

                if replacer is None:
                    raise ConfigurationException(
                        f"\nante={repr(ante)}\nadd={repr(add)} not handled correctly"
                    )

                after_val[name] = replacer

            ext = ext or dupe.ext
            alias = alias or dupe.alias

            # allows for more specialized classes than ValidatorMgr
            res = self.__class__(
                ext=ext, alias=alias, validators=list(after_val.values())
            )

            return res

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def show(self, nesting="", file=None, header: Any = None):
        "do-nothing !!!TODELETE!!!"

#################################################################
# assert_same
#################################################################


class SameAssertor:
    """v4 SameChecker"""

    T_FILENAME = (
        "%(filename)s %(classname)s %(_testMethodName)s %(suffix)s %(lazy_extension)s"
    )

    def __init__(self, checker: "Checker"):
        self.checker = checker

    def __repr__(self):
        return "%s[%s]" % (self.__class__.__name__, self.checker.ext)

    def get_fnp_save(
        self,
        testee: Any,
        exp_got: str,
        control: _Control,
        suffix: str | None = "",
        basename_prefix: str = "",
    ) -> Path:
        """get the save path"""

        try:
            if suffix is None:
                suffix = ""

            subber = Subber(
                # testee,
                {
                    "_testMethodName": testee._testMethodName,
                    "lazy_extension": self.checker.ext,
                    "filename": testee.lazy_filename,
                    "suffix": suffix,
                    "classname": testee.__class__.__name__,
                    "exp_got": exp_got,
                },
                self,
                testee,
                # the lower priority the TestCase instance the less probability
                # of name clashes
                # self,
            )

            # calculating the directory path
            t_dirname = self._lazy_get_t_dirname(exp_got, subber, control, testee)

            if t_dirname is None:
                return None

            _litd = t_dirname.split(os.path.sep)
            _litd = self._handle_dirname_extras(_litd, testee)
            _lid = ["/"] + [fill_template(t_, subber) for t_ in _litd]
            dirname = os.path.join(*_lid)

            #################################################################
            # calculating the filename
            #################################################################

            if not basename_prefix:
                t_basename = self.T_FILENAME
            else:
                if not basename_prefix.endswith("."):
                    basename_prefix += "."
                t_basename = basename_prefix + self.T_FILENAME

            _litb = t_basename.split()
            _lib = [fill_template(t_, subber) for t_ in _litb]
            basename = ".".join([i_ for i_ in _lib if i_])
            basename = basename.replace(" ", "_")
            basename = basename.replace("/", "_")

            # add provider extension, as in `settings.json`
            alias = self.checker.alias
            if alias:
                basename = f"{basename}.{alias}"

            if not os.path.isdir(dirname):
                os.makedirs(dirname)

            return Path(os.path.join(dirname, basename))

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def write_raw(
        self, provider: PAbstractExtProvider, suffix, testee, control, got
    ):  #
        """
        where do we save the raw received data,
        after formatting, but before filtering ?
        """


        try:
            if not control.env.get("save_raw_received_data"):
                return

            #  - route some of this to checker.provider

            fnp = self.get_fnp_save(
                testee=testee, exp_got="report", control=control, suffix=suffix
            )

            got2 = self.checker.temp.rawdata or got
            if provider.text_based:
                got2 = str(got2)

            provider.write(fnp, got2)

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def _lazy_get_t_dirname(self, exp_got, subber, control, testee):
        """get the template for the directory names where to save files"""
        try:
            env_name = dict(
                exp="template_dirname_exp",
                got="template_dirname_got",
                report="template_dirname_report",
            )[exp_got]
            dirname = subber.get("dirname") or control.env.get(env_name)

            if dirname is None:
                if exp_got in ("exp", "got"):
                    raise InvalidConfigurationException(
                        "could not get output directory for %s in %s"
                        % (exp_got, control.env)
                    )
                return None

            dirname2 = os.path.join(
                dirname, testee.lazy_filename, subber.get("classname")
            )

            return dirname2

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def _handle_dirname_extras(self, _litd, testee):
        """allows injection of extra instance-set attributes into the directory hierarchies
        The intent of `lazy_dirname_extras` is to partition tests by other attributes, like say
        a site name or a test database name.
        given `lazy_dirname_extras = "site"` and `self.site = 'example.com'`
        .
        └── <myclass>
            ├── example.com
            │   └── <get_basename>.<myclass>.<_testMethodName>.txt
        """

        try:

            dirname_extras = getattr(testee, "lazy_dirname_extras", "")
            if not dirname_extras:
                return _litd

            if isinstance(dirname_extras, list):
                dirname_extras = " ".join(dirname_extras)
            if dirname_extras:
                # expand something like "foo, bar" into [..."%(foo)s", "%(bar)s"...]
                li_replace = [
                    "%%(%s)s" % (attrname) for attrname in dirname_extras.split()
                ]

                _litd.extend(li_replace)

            return _litd

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


class Selectors(str, Enum):
    """some basic selector approaches"""

    # use Validator.name as the selector
    # ex: status_code will result in getattr(data, "status_code")
    # just as if Validator(name=status_code, selector="status_code")
    name = "name"


#  - assertEqual on a variable, not the whole data
def check_equal(
    data: Any,
    testee: unittest.TestCase,
    validator: "Validator",
    exp: Optional[Any] = None,
) -> bool:
    """check testee.exp == data"""

    try:
        exp = exp or validator.exp

        if breakpoints("lazy", {"validator": validator.name}):  # pragma: no cover
            print(f"\n\n!!!validator:{validator.name}")  # debugging
            breakpoint()
            pass

        if exp is AutoExp:
            exp = exp.get_exp(validator, testee)

        if not isinstance(data, type(exp)):
            #  - this is the old-style assertEqual applied to a variable, not the entire data p
            provider_check_equal = validator.mgr.provider.check_equal
            if provider_check_equal:
                pass
                #  - modify to pass in Checker, in order to access ValidatorMgr.config...
                res = provider_check_equal(
                    testee=testee, validator=validator, exp=exp, got=data
                )
                if not res:
                    msg = f"{validator.name}\nexp\n{exp}\n!=\ngot\n{str(data):60.60}\n"
                    raise ValidationError(msg, validator=validator, got=data)
                return res

        res = data == exp
        if not res and verbose:
            _checktypes(data, exp, validator)

        if not res:
            if isinstance(exp, Enum):
                s_exp = f"{str(exp._value_):60.60}"
            else:
                s_exp = f"{str(exp):60.60}"

            msg = f"{validator.name}\nexp\n{s_exp}\n!=\ngot\n{str(data):60.60}\n"
            raise ValidationError(msg, validator=validator, got=data)

        return res
    # pragma: no cover
    except ConfigurationException as e: # noqa F841
        e.got = data
        raise
    except ValidationError as e: # noqa F841
        if os.getenv("cpdb"):
            breakpoint()
            pass

        raise
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


def check_exp_in_data(
    data: Any,
    testee: unittest.TestCase,
    validator: "Validator",
    exp: Optional[Any] = None,
) -> bool:
    """check data in testee.exp"""
    try:
        exp = exp or validator.exp

        if type(exp) is type(AutoExp) and issubclass(exp, AutoExp):
            exp = exp.get_exp(validator, testee)

        elif callable(exp):
            exp = exp()

        res = exp in data

        if not res:
            msg = f"{validator.name}: {str(exp)} not in {data}"
            raise ValidationError(msg, validator=validator, got=data)

        return res
    # pragma: no cover
    except (ValidationError,):
        raise
    # pragma: no cover
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


def check_in(
    data: Any,
    testee: unittest.TestCase,
    validator: "Validator",
    exp: Optional[Any] = None,
) -> bool:
    """check data in testee.exp"""
    try:
        exp = exp or validator.exp
        res = data in exp

        if not res:
            msg = f"{validator.name}: {str(data)} not in {exp}"
            raise ValidationError(msg, validator=validator, got=data)

        return res

    # pragma: no cover
    except (ValidationError,):
        raise

    # pragma: no cover
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


def check_not_in(data, testee, validator):
    """check data not in testee.exp"""
    return data not in validator.exp


S_VALIDATIONS = set([check_equal, check_in, check_not_in])


def _flatten_from_string(li: List[Union[Validator, dict]], values: str):
    """
    this is shorthand for activating/deactivating individual validators
    `foo -bar` =>
    - dict(name="foo") #active is implied
    - dict(name="bar, active=False)

    """

    try:
        for v in values.split():
            if v.startswith("-"):
                li.append(dict(name=v.lstrip("-"), active=False))
            else:
                li.append(dict(name=v))

    # pragma: no cover
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


def flatten_to_validators_dicts(
    li: List[Union[Validator, dict]],
    values: Union[List, ValidatorMgr, Validator, Dict[str, Any], str],
):
    """flatten nested one or more Validator ValidatorMgr dict to a list of Validator, dict"""

    try:
        if isinstance(values, (list, tuple)):
            [
                flatten_to_validators_dicts(li, v)
                for v in values
                if not isinstance(v, ExtAlias)
            ]
        elif isinstance(values, (Validator, dict)):
            li.append(values)
        elif isinstance(values, ExtAlias):
            return
        elif values is DisableAll:
            li.append(values)

        elif isinstance(values, ValidatorMgr):
            [flatten_to_validators_dicts(li, v) for v in values.validators]

        elif isinstance(values, str):
            _flatten_from_string(li, values)

        else:
            raise ConfigurationException(
                f"flatten_to_validators_dicts:unsupported {values=} "
            )

    # pragma: no cover
    except (Exception,) as e: # noqa F841
        if cpdb():
            breakpoint()
        raise


CHECK_EQUALITY = FunctionCheck(check_equal)


class ActualValidator(Validator):
    """before each validation, active Validators are copied to ActualValidators
    which check that the configuration can be used (for example, active implies a `v`
    validation function has been provided)
    """

    name: str
    mgr: ValidatorMgr
    selector: Union[None, Any, Callable] = None
    exp: Any = None
    v: ValidatorCheck
    error: str = ""

    @pydantic.field_validator("v", mode="before")
    @classmethod
    def build_validator(cls, value: Any, info: pydantic.ValidationInfo):

        try:
            if not value:
                value = CHECK_EQUALITY

            return value
        # pragma: no cover
        except (ConfigurationException,) as e: # noqa F841
            raise

        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @pydantic.model_validator(mode="after")
    def _init(self):
        try:
            selector = self.selector
            if selector is None:
                self.selector = self.name

            exp = self.exp
            if exp is None:
                self.exp = AutoExp
            return self

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def assert_valid(
        self, testee: Any, rawdata: Any, data_in: Any, debug: Optional[bool] = False
    ):
        """run self.v.is_valid() against part or all of data_in"""

        tu_raises = get_immediate_raises(debug)
        try:
            selector = self.selector

            # if a selector has been been provided, call it to extract
            # the data from compound data
            if selector:
                kwargs = dict(
                    testee=testee,
                    validator=self,
                    data_in=data_in,
                    temp=self.mgr.temp,
                    rawdata=rawdata,
                )

                if isinstance(selector, (operator.itemgetter, operator.attrgetter)):
                    data = selector(data_in)

                if type(selector) is type and issubclass(selector, Auto):
                    data = data_in
                elif selector is select_by_provider:
                    data = select_by_provider(**kwargs)
                elif callable(selector):
                    if type(selector) in (operator.itemgetter, operator.attrgetter):
                        data = selector(data_in)
                    else:
                        data = selector(**kwargs)
                elif isinstance(selector, str):
                    prefix_filter = ".filtered."
                    if selector.startswith(prefix_filter):
                        selector2 = selector.removeprefix(prefix_filter)
                        data = self.mgr.temp.filtered.get(selector2)
                    else:
                        # is it a direct attribute?
                        value = getattr(data_in, selector, undefined)
                        if value is not undefined:
                            data = value
                        else:
                            kwargs["selector"] = selector
                            data = self.mgr.provider.select_by_string(**kwargs)
                else:
                    raise NotImplementedError(f"unsupported {type(selector)=}")
            else:
                data = data_in
            #  - modify to pass in Checker, in order to access ValidatorMgr.config...
            valid = self.v.is_valid(data, testee=testee, validator=self)
            return valid
        except tu_raises as e: # noqa F841
            raise
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


def select_by_provider(
    validator: "Validator",
    testee: unittest.TestCase,
    data_in: Any,
    attrname: Optional[str] = None,
    **kwargs,
):
    "have the provider select"

    attrname = attrname or validator.name
    f_data = getattr(validator.mgr.provider, attrname)
    data = f_data(data_in)
    return data


def select_by_name(validator: "Validator"):
    raise NotImplementedError()


_S_SELECTORS = set([select_by_name, select_by_provider])
