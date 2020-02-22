""" core LazyMixin functionality 

be very cautious of referencing self.<attribute> when there is no 'lazy' prefix to it

for this reason auxiliary classes have been moved to core_assist.py

"""

import pdb
import os
import sys

from pathlib import Path

undefined = NotImplemented

verbose = "-v" in sys.argv

#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    Union,
)


#######################################################

import pdb


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


# from timeout_decorator import timeout, TimeoutError as CustomTimeoutError

try:

    from timeout_decorator import timeout

    import timeout_decorator

    CustomTimeoutError = timeout_decorator.timeout_decorator.TimeoutError

    TIMEOUT_MAXTIME_TO_ALLOW = 5
except (ImportError,) as e:  # pragma: no cover
    # pdb.set_trace()
    timeout = None
    TIMEOUT_MAXTIME_TO_ALLOW = 0

    class CustomTimeoutError(Exception):
        """we'll never see this """

        pass


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

from lazy_regression_tests._baseutils import debugObject, ppp, Dummy

from traceback import print_exc as xp

from .validators import (
    ValidationManager,
    NamedTesteeAttributeValidator,
    build_validators_for_class,
)
from .filters import build_filters_for_class, FilterManager


# aliasing the JSON response filter management to DictFilterManager as there is
# very little that is HTTP specific
from .http_validators import JsonFilterManager as DictFilterManager

from lazy_regression_tests.utils import (
    # MediatedEnvironDict,
    undefined,
    Subber,
    RegexRemoveSaver as RegexRemoveSaver1,
    ppp,
    fill_template,
)

#######################################################
# extract to secondary
#######################################################

# 🔬LazyCheckerOptions2 in v2


from .core_assist import LazyChecker, LazyTemp, MediatedEnvironDict, _Control, _LazyMeta

OPT_DIRECTIVE_SKIP = "skip"
OPT_DIRECTIVE_BASELINE = "baseline"
OPT_DIRECTIVE_NODIFF = "nodiff"


class LazyMixin(metaclass=_LazyMeta):
    cls_filters = {}
    cls_validators = []
    add_lazy_dirname = []

    lazy_dirname_extras = []

    lazytemp = None
    lazy_basename_extras = ""

    # this normally resolves to os.environ, but can be preset for testing
    lazy_environ = MediatedEnvironDict()

    T_FILENAME = "%(filename)s %(classname)s %(_testMethodName)s %(lazy_basename_extras)s %(suffix)s %(lazy_extension)s"

    ENVIRONMENT_VARNAME_ROOT = "lzrt_"

    @classmethod
    def get_basename(cls, name_, file_, module_):
        cls.lazy_pa = pa = Path(file_)
        return pa.stem

    def lazy_build_filters(self):
        try:
            res = {}
            for extension, filter_ in self.__class__.cls_filters.items():
                # if cpdb(): pdb.set_trace()
                filter_copy = filter_.copy()
                assert filter_copy, "filter_copy empty"
                res[extension] = filter_copy

            return res

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def _lazy_get_t_dirname(self, exp_got, subber):

        try:

            env_name = dict(exp="template_dirname_exp", got="template_dirname_got")[
                exp_got
            ]
            dirname = subber.get("dirname") or self.control.env[env_name]

            dirname2 = os.path.join(dirname, subber.get("classname"))

            return dirname2

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def _handle_dirname_extras(self, _litd):
        try:

            dirname_extras = getattr(self, "lazy_dirname_extras", "")
            if not dirname_extras:
                return _litd

            if isinstance(dirname_extras, list):
                dirname_extras = " ".join(dirname_extras)
            if dirname_extras:
                # expand something like "foo, bar" into [..."%(foo)s", "%(bar)s"...]
                li_replace = [
                    "%%(%s)s" % (attrname) for attrname in dirname_extras.split()
                ]

                if "%(lazy_dirname_extras)s" in _litd:
                    _litd = replace(_litd, "%(lazy_dirname_extras)s", li_replace)
                else:
                    _litd.extend(li_replace)

            return _litd

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def _get_fnp_save(
        self,
        exp_got: Union["got", "exp"],
        options: "LazyChecker",
        suffix: Optional[str],
    ):
        """get the save path"""

        try:

            extension = options

            subber = Subber(
                options,
                {
                    "filename": self.lazy_filename,
                    "suffix": suffix,
                    "classname": self.__class__.__name__,
                    "exp_got": exp_got,
                },
                # the lower priority the TestCase instance the less probability
                # of name clashes
                self,
            )

            # calculating the directory path
            t_dirname = self._lazy_get_t_dirname(exp_got, subber)
            _litd = t_dirname.split(os.path.sep)

            _litd = self._handle_dirname_extras(_litd)

            _lid = ["/"] + [fill_template(t_, subber) for t_ in _litd]

            dirname = os.path.join(*_lid)

            # calculating the filename
            t_basename = self.T_FILENAME
            _litb = t_basename.split()
            _lib = [fill_template(t_, subber) for t_ in _litb]
            basename = ".".join([i_ for i_ in _lib if i_])

            basename = basename.replace(" ", "_")
            basename = basename.replace("/", "_")

            if not os.path.isdir(dirname):
                os.makedirs(dirname)

            return os.path.join(dirname, basename)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    #######################################################
    # validator related
    #######################################################

    _filters = _validationmgr = undefined

    @property
    def validationmgr(self):
        if self._validationmgr is undefined:
            res = None
            self._validationmgr = res = ValidationManager(self, *self.cls_validators)

        return self._validationmgr

    @property
    def filters(self):
        if self._filters is undefined:
            self._filters = self.lazy_build_filters()

        return self._filters

    def check_expectations(
        self, lazy_skip=None, lazy_skip_except=None, lazy_sourced_only=True, **sources
    ):
        try:
            self.validationmgr.check_expectations(
                self,
                lazy_skip=lazy_skip,
                lazy_skip_except=lazy_skip_except,
                lazy_sourced_only=lazy_sourced_only,
                **sources,
            )
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def set_expectation(self, *args, **kwargs):
        validationmgr = self.validationmgr

        name = args[0]
        if breakpoints("set_expectation", {"name": name}):  # pragma: no cover
            pdb.set_trace()

            # put this in your breakpoints.json

        validationmgr.set_expectation(*args, **kwargs)

    #######################################################
    # diff-related
    #######################################################

    def assert_exp(self, got: Any, extension: str, suffix: str = "") -> LazyTemp:

        # 🔬 this is the v2 path

        try:

            assert isinstance(extension, str), (
                "need string extension parameter for LazyMixin2 %s.assert_exp(extension=%s)"
                % (self, extension)
            )

            filter_ = self.filters[extension]

            rawfiltermgr, textfiltermgr = filter_.get_raw_text_filters()

            di_debug = {}

            # raise NotImplementedError("%s.assert_exp(%s)" % (self, di_debug))

            checker = LazyChecker(
                extension=extension,
                rawfiltermgr=rawfiltermgr,
                textfiltermgr=textfiltermgr,
            )

            if hasattr(filter_, "to_text"):
                checker.to_text = filter_.to_text
            if hasattr(filter_, "prep"):
                checker.prep = filter_.prep

            return self._lazycheck(got, checker, suffix)

        except (AssertionError,) as e:  # pragma: no cover
            raise
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def _lazycheck(self, got: Any, options: LazyChecker, suffix: str = "") -> LazyTemp:

        try:
            env = self.lazy_environ
            if not self.lazy_environ.acquired:
                env.clear()
                env.acquire(self.ENVIRONMENT_VARNAME_ROOT)

            self.control = control = _Control(self, env, options)

            # only create the lazy temp the first time.
            tmp = self.lazytemp = self.lazytemp or LazyTemp(control, env, self)

            # the environment requests that no diffing or writing take place
            # typically indicated by setting environment variable `lzrt_directive=skip`
            if control.skip():
                return

            # calculate the paths of the exp/got files
            tmp.fnp_got = fnp_got = self._get_fnp_save("got", options, suffix)
            tmp.fnp_exp = fnp_exp = self._get_fnp_save("exp", options, suffix)

            # linefeeds have a tendency to creep in sometimes
            formatted_got = options.format(tmp, got).rstrip()

            # at this point, we want to write the received, formatted, data regardless
            with open(fnp_got, "w") as fo:
                fo.write(formatted_got)

            # the newly received data is to be taken as our expectations
            # typically indicated by setting environment variable `lzrt_directive=baseline`
            if control.baseline():
                with open(fnp_exp, "w") as fo:
                    fo.write(formatted_got)
                return tmp

            try:
                with open(fnp_exp) as fi:
                    # linefeeds have a tendency to creep in sometimes
                    exp = fi.read().rstrip()
            except (IOError,) as e:
                # by default we just want to write the received data as our expectation
                if control.write_exp_on_ioerror():
                    tmp.message = message = "no check because IOError on %s" % (fnp_exp)
                    with open(fnp_exp, "w") as fo:
                        fo.write(formatted_got)
                    return tmp
                else:
                    raise

            # the environment requests only equality is checked, without trying to show details
            # typically indicated by setting environment variable `lzrt_directive=nodiff`
            # this may be desired if the differences could cause timeouts with `assertEqual`
            if control.nodiff():
                tmp.message = message = "exp and got are not equal but diffing disabled"
                if exp != formatted_got():
                    raise self.fail(message)

            try:
                # supports a timeout mechanism, if the module is available
                self.assertEqualTimed(exp, formatted_got)
            except (CustomTimeoutError,) as e:  # pragma: no cover
                tmp.message = message = (
                    "exp and got are not equal but comparison timed out after %s seconds"
                    % (TIMEOUT_MAXTIME_TO_ALLOW)
                )
                self.fail(message)
            except (AssertionError,) as e:  # pragma: no cover
                raise
            except (
                Exception,
            ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
                if cpdb():
                    pdb.set_trace()
                raise

            return self.lazytemp

        except (AssertionError,) as e:  # pragma: no cover
            raise
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    #######################################################
    # Note the conditional method definition and the fallback to
    # basic assertEqual
    #######################################################
    if timeout:

        @timeout(TIMEOUT_MAXTIME_TO_ALLOW)
        def assertEqualTimed(self, exp, got, message=None):
            """ comparisons will automatically times out after %s seconds""" % (
                TIMEOUT_MAXTIME_TO_ALLOW
            )
            self.assertEqual(exp, got, message)

    else:
        #
        def assertEqualTimed(self, exp, got, message=None):
            self.assertEqual(exp, got, message)
