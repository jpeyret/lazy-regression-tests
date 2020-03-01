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


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


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


# pylint: disable=unused-import
from lazy_regression_tests._baseutils import ppp, Dummy
from traceback import print_exc as xp

# pylint: enable=unused-import


# pylint: disable=unused-wildcard-import,wildcard-import
from .common import *

# pylint: enable=unused-wildcard-import,wildcard-import


from .validators import ValidationManager


# aliasing the JSON response filter management to DictFilterManager as there is
# very little that is HTTP specific

from lazy_regression_tests.utils import Subber, fill_template


from .core_assist import LazyChecker, LazyTemp, MediatedEnvironDict, _Control, _LazyMeta


class LazyMixin(metaclass=_LazyMeta):
    """ Intended as a Mixin to unittest classes it provides a number of services automatically

        - validations via cls_validators and set_expectation
        - regression testing against last seen baseline via `self.assert_exp(data, extension)`
        - filtering to avoid false regression alerts from variable data (timestamps, csrf protection tokens)
           - cls_filters = dict(<extension>=FilterDirectives...)
           - self.set_filter(FilterDirective)

        - both validations and filters are intended to be defined in mixin ancestor classes and mixed and 
          matched as desired

        class MyTest(LazyMixin, unittest.TestCase):
            cls_filters = dict(html=filter_csrftokens)
            cls_validators = [validate_http, validate_html]

            
    """

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
    def get_basename(cls, name_, file_, module_) -> str:
        """ called from mytest.py this returns mytest and is the base for file naming
        its use in client code is a bit anomalous as the enclosing class
        hasn't been created yet.
        """
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
        """ get the template for the directory names where to save files """
        try:

            env_name = dict(
                exp="template_dirname_exp",
                got="template_dirname_got",
                report="template_dirname_report",
            )[exp_got]
            dirname = subber.get("dirname") or self._lazy_control.env.get(env_name)

            if dirname is None:
                if exp_got in ("exp", "got"):
                    raise InvalidConfigurationException(
                        "could not get output directory for %s in %s"
                        % (exp_got, self._lazy_control.env)
                    )
                return None

            dirname2 = os.path.join(
                dirname, self.lazy_filename, subber.get("classname")
            )

            return dirname2

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def _handle_dirname_extras(self, _litd):
        """ allows injection of extra instance-set attributes into the directory hierarchies
        The intent of `lazy_dirname_extras` is to partition tests by other attributes, like say 
        a site name or a test database name.
        given `lazy_dirname_extras = "site"` and `self.site = 'example.com'`
        .
        └── <myclass>
            ├── example.com
            │   └── <get_basename>.<myclass>.<_testMethodName>.txt

        """

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
        """ get the save path """

        try:

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

            if t_dirname is None:
                return None

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

        # pragma: no cover pylint: disable=unused-variable, broad-except
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    #######################################################
    # validator related
    #######################################################

    _filters = _validationmgr = undefined

    @property
    def validationmgr(self):
        """ create the validationmgr on demand """
        if self._validationmgr is undefined:
            self._validationmgr = ValidationManager(self, *self.cls_validators)

        return self._validationmgr

    @property
    def filters(self):
        """ build filters at the instance level """
        if self._filters is undefined:
            self._filters = self.lazy_build_filters()

        return self._filters

    def check_expectations(
        self, lazy_skip=None, lazy_skip_except=None, lazy_sourced_only=True, **sources
    ):
        """ validate active validation directives """
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
        """ add/modify a validation """

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
        """
        regression test that `got` is the same as what was last encountered and stored
        in `exp` file.
        """

        try:

            if not isinstance(extension, str):
                raise InvalidConfigurationException(
                    "%s.extension has to be a string (extension=%s) and one of the existing filters"
                    % (self, extension)
                )

            try:
                filter_ = self.filters[extension]
            # pragma: no cover pylint: disable=unused-variable
            except (KeyError,) as e:
                raise InvalidConfigurationException(
                    f"{self}. unknown extension={extension}. known extensions in filters:{self.filters.keys()}"
                )

            rawfiltermgr, textfiltermgr = filter_.get_raw_text_filters()

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

        # pragma: no cover pylint: disable=unused-variable
        except (AssertionError,) as e:  # pragma: no cover
            raise
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def _get_fnp_raw(self, options, suffix, control, tmp, got):
        """ 
        where do we save the raw received data,
        after formatting, but before filtering ? 
        """

        try:
            if not control.save_raw:
                return

            fnp_raw = self._get_fnp_save("report", options, suffix)

            return fnp_raw

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def _lazycheck(self, got: Any, options: LazyChecker, suffix: str = "") -> LazyTemp:

        try:
            env = self.lazy_environ
            if not self.lazy_environ.acquired:
                env.clear()
                env.acquire(self.ENVIRONMENT_VARNAME_ROOT)

            self._lazy_control = control = _Control(self, env, options)

            # only create the lazy temp the first time.
            tmp = self.lazytemp = self.lazytemp or LazyTemp(control, env, self)

            # the environment requests that no diffing or writing take place
            # typically indicated by setting environment variable `lzrt_directive=skip`
            if control.skip():
                return tmp

            # calculate the paths of the exp/got files
            tmp.fnp_got = fnp_got = self._get_fnp_save("got", options, suffix)
            tmp.fnp_exp = fnp_exp = self._get_fnp_save("exp", options, suffix)

            fnp_raw = self._get_fnp_raw(options, suffix, control, tmp, got)

            # linefeeds have a tendency to creep in sometimes
            formatted_got = options.format(tmp, got, fnp_raw).rstrip()

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

            # pragma: no cover pylint: disable=unused-variable
            except (IOError,) as e:
                # we just want to write the received data as our expectation
                tmp.execinfo.ioerror_exp = fnp_exp
                tmp.message = message = "no check because IOError on %s" % (fnp_exp)
                with open(fnp_exp, "w") as fo:
                    fo.write(formatted_got)
                return tmp

            # the environment requests only equality is checked, without trying to show details
            # typically indicated by setting environment variable `lzrt_directive=nodiff`
            # this may be desired if the differences could cause timeouts with `assertEqual`
            if control.nodiff():
                tmp.message = message = "exp and got are not equal but diffing disabled"
                if exp != formatted_got():
                    raise self.fail(message)

            # pragma: no cover pylint: disable=unused-variable
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
            except (Exception,) as e:
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
            try:
                self.assertEqual(exp, got, message)
            except (AssertionError,) as e:
                raise self.format_assertion_message(e)

    else:
        #
        def assertEqualTimed(self, exp, got, message=None):
            """ fallback if timeout package is not available """
            try:
                self.assertEqual(exp, got, message)
            except (AssertionError,) as e:
                raise self.format_assertion_message(e)

    def format_assertion_message(self, ori):

        message = f"""

❌❌❌Regressions found:

Expected contents are in file:
  {self.lazytemp.fnp_exp}

Received contents are in file:
  {self.lazytemp.fnp_got}

Original exception:
 {ori}
❌❌❌
"""
        exc = ori.__class__(message)
        return exc
