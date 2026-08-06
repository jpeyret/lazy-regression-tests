"""
basic building blocks that do not reference each other
used to offload common.py
"""
from typing import Optional, Callable, Any, List, Tuple, cast
import os
import json
import sys
from pathlib import Path


#################################################################
# Dependencies
#################################################################
import pydantic
from pydantic import ConfigDict


from lazy_regression_tests._baseutils import oshow as show, Subber, ppp, format_url
import lazy_regression_tests.constants as constants


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


verbose = constants.verbose

undefined = constants.undefined

# 🎫004.lazy.052.polars_diffing
class ExtAlias(pydantic.BaseModel):
    """allows uncoupling name from extension provider

    for example, with:
    cls_filters = dict(
        settings = [ExtAlias(alias="json"), dict(name="objectvalue01")]
    )

    checker from lz.settings will be using `JsonExtProvider` despite being named `settings`

    if absent, name drives ExtProvider

    """

    alias: str
    config: dict[str, Any] | None = None

    @classmethod
    def is_instance(cls, v):
        return isinstance(v, cls)


class ExecInfo:
    "track error info"

    def __init__(self):
        "init"
        self.ioerror_exp = self.ioerror_got = None


class MediatedEnvironDict(dict):
    """reads prefixed environment variables
    `rootname` allows user to define the variable's prefix
    i.e. change from `lzrt_` to something else if there is a
    conflict
    LZRT_OPT_DIRECTIVE could be MYLAZY_OPT_DIRECTIVE
    """

    def __init__(self, acquired=False, **kwds):
        """init"""
        self.acquired = acquired
        super(MediatedEnvironDict, self).__init__(**kwds)

    def acquire(self, rootname: str):
        """read prefixed environment variables"""

        if self.acquired:
            return

        len_root = len(rootname)
        for k, value in os.environ.items():
            if k.startswith(rootname):
                k2 = k[len_root:]
                self[k2] = value

        self.acquired = True


class BFilter(pydantic.BaseModel):
    """the core filtering mechanism
    Note:  its primary concept is that the `f` - filtering function drives
    the equality/hash for objects.  This allows overrides of all other
    attributes by later classes.
    """

    # filters are assumed to be textfilters
    raw: bool = False

    # is this filter active?
    active: bool = True
    # invert filter, match() returns False
    invert: bool = False
    label: Optional[str] = None
    name: str = ""

    cls_: Optional[type] = None
    formatter: Optional[Callable] = None
    show = show
    model_config = ConfigDict(arbitrary_types_allowed=True, extra=pydantic.Extra.forbid)

    def __eq__(self, other):
        """see notes on hash"""
        if not isinstance(other, BFilter):
            return NotImplemented
        return self.f == other.f

    def __hash__(self):
        """be careful here.  __hash__ and __eq__ drive successive overrides of filters
        by subclasses.  if you were to include `invert` in the hash, then updating the filter
        to inversion would not work.  Right now the only thing that is being used is the filter
        function `v` itself
        """
        return hash((self.f))

    def __repr__(self):
        "repr"
        name = f"{self.name}:" if self.name else ""
        return (
            f"{name}{self.__class__.__name__}.{'!' if self.invert else ''}{self.label}"
        )


class ConfigurationException(ValueError):
    "tracks possible configuration exceptions"

    def __str__(self):
        "adds header/footer"
        v = Exception.__str__(self)
        return f"{constants.HDR}{v}{constants.FTR}"

    def __repr__(self):
        "adds header/footer"
        v = Exception.__repr__(self)
        return f"{constants.HDR}{v}{constants.FTR}"

    def allow_cpdb(self):
        return os.getenv("bme_debug_allow_cpdb")


class SpecialCommand:
    """special classes to command particular behavior"""


class DisableAll(SpecialCommand):
    """disable a Mgr content up to that point
    i.e. ValidatorMgr becomes empty, ditto Filter
    """


class Auto:
    """validation function will access data directly"""


class AutoExp:
    """allows exp lookup by testee.attrname"""

    @classmethod
    def get_exp(cls, validator: "Validator", testee: Any):
        """allows exp lookup by testee.attrname"""
        try:
            return getattr(testee, validator.name)
        # pragma: no cover pylint: disable=unused-variable
        except (AttributeError,) as e:
            msg = f"{repr(validator)} : {e}:  Known fields on `testee` {repr(testee)} : {list(vars(testee).keys())}"

            if verbose:
                ppp(validator, f"\n\nAutoExp {e=} {testee}")

            raise ConfigurationException(msg)


def get_alias_check_equality(li_in: List[Optional[ExtAlias]]) -> Optional[ExtAlias]:
    """return an ExtAlias if they all match, ignoring Nones"""
    try:

        lia = [v for v in li_in if v is not None]

        if not lia:
            return None

        s = set(lia)
        if len(s) > 1:
            raise ConfigurationException(f"{li_in=}: aliases have to match")

        return lia[0]

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            breakpoint()
        raise


def get_alias_from_ancestors(
    cls: type, ancestors: List[type], ext: str
) -> Optional[str]:
    """get the ancestors' provider"""
    try:
        for ancestor in ancestors:
            name = ancestor.__name__
            if ancestor is cls:
                continue
            try:

                for attrname in ["cls_validators", "cls_filters"]:
                    source = getattr(ancestor, attrname, {})
                    if not source:
                        continue
                    if source:
                        found = source.get(ext)
                        if found:
                            return found.alias
            # pragma: no cover pylint: disable=unused-variable
            except (AttributeError,) as e:
                pass

        return None

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            breakpoint()
        raise


class ValidationError(AssertionError):
    """give better insight on a validation error than base AssertionError"""

    def __init__(
        self,
        msg=None,
        validator: Optional["Validator"] = None,
        got=undefined,
        exp=undefined,
        testee=undefined,
    ):
        "init"
        super().__init__(msg)
        self.validator = validator
        self.got = got
        self.exp = exp
        self.testee = testee

    def __repr__(self):
        """repr"""

        try:
            indent = " " * 2
            li = [f"{self.__class__.__name__}({self.args[0]})"]

            exp_seen = False
            if self.exp is not undefined:
                li.append(f"{indent}exp={self.exp}")
                exp_seen = True
            if self.got is not undefined:
                li.append(f"{indent}got={self.got}")

            if self.validator:
                for name, v in self.validator.dict(
                    exclude={"mgr", "error", "title", "name", "active"}
                ).items():
                    if name == "exp":
                        if exp_seen:
                            continue
                        if type(v) == type and issubclass(v, (AutoExp,)):
                            v = v.__name__
                    elif name == "v":
                        if getattr(v, "__class__", None) and v.__class__.__name__ in (
                            "FunctionCheck",
                        ):
                            v = v.f
                    li.append(f"{indent}{name}={v}")
            else:
                li.append("validator wasn't set")

            return "\n".join(li)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    __str__ = __repr__

    def debug(self):
        "returns a dictionary of relevant data"
        try:
            validator = self.validator.dict()
        except (AttributeError,) as e:
            validator = self.validator

        return dict(msg=str(self), validator=validator)


class OutInfo:
    def dumps(self):
        return json.dumps(self.__dict__, sort_keys=True, indent=2)

    def __init__(self, error: bool, **kwargs) -> None:
        self.has_error = bool(error)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __setattr__(self, __name: str, __value: Any) -> None:
        """support json-izing"""
        if __value is undefined:
            return
        if isinstance(__value, (str, int, float, bool)):
            pass
        else:
            __value = str(__value)

        self.__dict__[__name] = __value


def lazyinfo(
    *args,
    testee=None,
    gather_test_info: Callable = None,
    exception=None,
    write_on_success=False,
    **kwargs,
) -> str:

    """
    when called on an exception, try to gather as much as possible and
    save it to json so that you can use to interact with the exception context later
    """
    try:

        res = ""
        type_ = tb = None
        if exception:
            type_, _, tb = sys.exc_info()
        else:
            # we actually dont do all that much with lazyinfo when nothing happened
            return f"{testee}.  no exception "

        dn_out = os.getenv("lzrt_info_dir")
        if not dn_out:
            print(
                f"env variable $lzrt_info_dir is not set.  No diagnostics can be written."
            )
            return

        error = error = bool(exception)
        outinfo = OutInfo(error=error)
        if testee:
            outinfo.testmodule = testee.__module__
            outinfo.testclass = testee.__class__.__name__
            outinfo.testmethod = testee._testMethodName

            pass

        if exception:
            outinfo.exception = exception

        kwargs = dict(**kwargs)

        subber = Subber(*([outinfo, kwargs, testee] + list(args)))

        if gather_test_info:
            outinfo0 = outinfo
            outinfo = gather_test_info(
                subber=subber,
                testee=testee,
                outinfo=outinfo,
                exception=exception,
                tb=tb,
            )
            if not outinfo:
                outinfo = outinfo0

        if error:
            error_part = "error."
        else:
            error_part = ""

        fn_o = f"{error_part}{testee.__class__.__module__}.{testee.__class__.__name__}"
        _testMethodName = getattr(testee, "_testMethodName", None)
        if _testMethodName:
            fn_o = f"{fn_o}.{_testMethodName}"

        fn_o += ".json"

        fnp_exp = getattr(exception, "fnp_exp", undefined)
        fnp_got = getattr(exception, "fnp_got", undefined)

        if not outinfo:
            str_exc = str(exception)
            return f"🧨 {outinfo=} for exception:{str_exc:100.100}"

        outinfo.file_exp = fnp_exp
        outinfo.file_got = fnp_got

        if kwargs.get("polars"):
            outinfo.app = "jplshowdiff.py"

        if tb:
            outinfo.filename = tb.tb_frame.f_code.co_filename
            outinfo.linenum = tb.tb_lineno

        fnpo = Path(dn_out) / fn_o

        if exception:
            res += f"\n  info@ {fnpo}"

            url = getattr(outinfo, "url", None)
            if url:
                url2 = format_url(url)
                res += f"\n  url: {url2}"
                outinfo.url = url2

            testclass = getattr(outinfo, "testclass", None)
            testmethod = getattr(outinfo, "testmethod", None)

            if testclass and testmethod:
                res += f"\n  spec: {testclass}.{testmethod}"

            filename = getattr(outinfo, "filename", None)
            linenum = getattr(outinfo, "linenum", None)
            if filename and linenum:
                res += f"\n  edit@ {filename}:{linenum}"

        out = outinfo.dumps()

        if res:
            res = f"\n{res}\n"

        showinfo = os.getenv("showinfo") or write_on_success

        if error or showinfo:


            with fnpo.open("w") as fo:
                fo.write(out)

            # write symlink last
            fnp_last = Path(dn_out) / "lastinfo.json"
            if fnp_last.exists():
                fnp_last.unlink()
            os.symlink(fnpo, fnp_last)

            if exception:
                msg = f"\n\n🐝diagnostics, usable with jlazyinfo.py are in :{fnpo}"
                args = exception.args
                if args and isinstance(args[0], str):
                    arg0 = args[0] + msg
                    exception.args = (arg0,) + exception.args[1:]
        return res

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            breakpoint()
        raise


class ALazyRoot:
    "keep annos happy"
