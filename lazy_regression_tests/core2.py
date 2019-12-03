# -*- coding: utf-8 -*-


#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
    Union,
)

# if TYPE_CHECKING:

#######################################################


###################################################################

import sys
import os
import unittest
import json
import codecs

import re
import shutil
from collections import namedtuple

from copy import deepcopy

###################################################################

import pdb

from lazy_regression_tests._baseutils import debugObject, ppp, Dummy

from traceback import print_exc as xp


def cpdb(**kwds: "Any") -> bool:  # pragma: no cover
    # return True
    if cpdb.enabled == "once":
        cpdb.enabled = False  # type : ignore
        return True
    return cpdb.enabled  # type : ignore


cpdb.enabled = False  # type : ignore


def rpdb() -> bool:  # pragma: no cover
    try:
        from django.core.cache import cache
    except (Exception,) as e:
        cache = {}
    import sys

    in_celery = sys.argv[0].endswith("celery") and "worker" in sys.argv
    if in_celery:
        return False
    return bool(cache.get("rpdb_enabled") or getattr("rpdb", "enabled", False))


rpdb.enabled = False  # type : ignore


import logging

try:
    from timeout_decorator import timeout, TimeoutError as CustomTimeoutError

    TIMEOUT_MAXTIME_TO_ALLOW = 5
except (ImportError,) as e:  # pragma: no cover
    timeout = None
    TIMEOUT_MAXTIME_TO_ALLOW = 0

    class CustomTimeoutError(Exception):
        """we'll never see this """

        passs


from lazy_regression_tests.utils import (
    MediatedEnvironDict,
    undefined,
    Subber,
    RegexRemoveSaver as RegexRemoveSaver1,
    ppp,
    fill_template,
)


from lazy_regression_tests.filters2 import (
    RawFilterMgr,
    TextFilterMgr,
    FilterMgr2,
    RawFilter,
    TextFilter,
)


class MediatedEnvironDict(dict):
    def __init__(self, acquired=False, **kwds):
        """
        """
        self.acquired = acquired
        super(MediatedEnvironDict, self).__init__(**kwds)

    def acquire(self, rootname):
        if self.acquired:
            return

        len_root = len(rootname)

        for k, value in os.environ.items():
            if k.startswith(rootname):
                k2 = k[len_root:]
                self[k2] = value

        self.acquired = True


class LazyCheckerOptions:

    candidate_textfilters = {}
    candidate_rawfilters = {}

    def __repr__(self):
        return "%s[id=%s]" % (self.__class__.__name__, id(self))

    def __init__(
        self,
        extension: str,
        write_exp_on_ioerror: bool = True,
        rawfiltermgr=None,
        textfiltermgr=None,
    ):
        self.extension = extension
        self.write_exp_on_ioerror = write_exp_on_ioerror
        self.rawfiltermgr = rawfiltermgr or RawFilterMgr()
        self.textfiltermgr = textfiltermgr or TextFilterMgr()
        ppp(self, self)

        self.filterhash = None

        self.reg_callbacks = {}

    def activate_textfilter(self, name, filter_=None, callback=None):

        if filter_ is None:
            di = self.candidate_textfilters
            filter_ = di.get(name)
            if not filter_:
                possibles = ",".join(list(di.keys()))

                msg = f"unknown textfilter `{name}`.  known textfilters are `{possibles}` on `{self}.candidate_textfilters`"
                raise ValueError(msg)

            self.textfiltermgr += di[name]
        else:
            filter_.name = name
            self.textfiltermgr += filter_

        if callback:
            self.reg_callbacks[name] = callback

    def remove_textfilter(self, name):
        self.textfiltermgr.pop(name)

    def activate_rawfilter(self, name, filter_=None, callback=None):

        if filter_ is None:
            di = self.candidate_rawfilters
            filter_ = di.get(name)
            if not filter_:
                possibles = ",".join(list(di.keys()))

                msg = f"unknown rawfilter `{name}`.  known rawfilters are `{possibles}` on `{self}.candidate_rawfilters`"
                raise ValueError(msg)

            self.rawfiltermgr += di[name]
        else:
            filter_.name = name
            self.rawfiltermgr += filter_

        if callback:
            self.reg_callbacks[name] = callback

    def remove_rawfilter(self, name):
        self.rawfiltermgr.pop(name)

    def filter_raw(self, tmp, data):
        return self.rawfiltermgr.filter(self, tmp, data)

    def filter_text(self, tmp, data):
        return self.textfiltermgr.filter(self, tmp, data).strip()

    def prep(self, tmp, data):
        return data

    def to_text(self, tmp, data):
        return str(data)

    def format(self, tmp, data):
        try:
            # used to only format once
            if (
                isinstance(data, str)
                and self.filterhash
                and self.filterhash == hash(data)
            ):
                return data

            data = self.prep(tmp, data)
            data = self.filter_raw(tmp, data)
            str_data = self.to_text(tmp, data)
            str_data = self.filter_text(tmp, str_data)

            self.filterhash = hash(str_data)

            return str_data
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                ppp(self, self)
                pdb.set_trace()
            raise


OPT_DIRECTIVE_SKIP = "skip"
OPT_DIRECTIVE_BASELINE = "baseline"
OPT_DIRECTIVE_NODIFF = "nodiff"


class _Control(object):
    """unifies environment and function arguments
       to determine handlers for IOError and AssertionError
       save in the LazyTemp results object as well.
    """

    def __init__(
        self, lazy: "LazyMixin", env: MediatedEnvironDict, options: LazyCheckerOptions
    ):

        self.lazy = lazy
        self.env = env
        self.options = options

    def write_exp_on_ioerror(self):
        return getattr(self.options, "write_exp_on_ioerror", True)

    _directive = undefined

    @property
    def directive(self) -> str:
        """ note that  """
        if self._directive is undefined:
            res = self._directive = self.env.get("directive", "").strip().lower()
            assert res in (
                OPT_DIRECTIVE_SKIP,
                OPT_DIRECTIVE_BASELINE,
                OPT_DIRECTIVE_NODIFF,
                "",
            )
        return self._directive

    def skip(self):
        return self.directive == OPT_DIRECTIVE_SKIP

    def baseline(self):
        return self.directive == OPT_DIRECTIVE_BASELINE

    def nodiff(self):
        return self.directive == OPT_DIRECTIVE_NODIFF


class LazyTemp(object):
    def __repr__(self):
        return "LazyTemp[id=%s]" % (id(self))

    def __init__(self, control, env, testee):
        self.control = control
        self.fnp_exp = self.fnp_got = None
        self.env = env.copy()
        self.message = ""
        self.filterhits = {}
        self.testee = testee


class LazyMixin(object):

    ENVIRONMENT_VARNAME_ROOT = "lzrt_"

    lazy_basename_extras = ""

    T_FILENAME = "%(filename)s %(classname)s %(_testMethodName)s %(lazy_basename_extras)s %(suffix)s %(extension)s"

    # this normally resolves to os.environ, but can be preset for testing
    lazy_environ = MediatedEnvironDict()

    lazytemp = None

    @classmethod
    def get_basename(cls, name_, file_, module_):
        lazy_filename = os.path.splitext(os.path.basename(file_))[0]
        return lazy_filename

    def _lazy_get_t_dirname(self, exp_got, subber):

        env_name = dict(exp="template_dirname_exp", got="template_dirname_got")[exp_got]
        dirname = self.control.env[env_name]

        dirname2 = os.path.join(dirname, subber.get("classname"))

        return dirname2

    def _get_fnp_save(
        self,
        exp_got: Union["got", "exp"],
        options: LazyCheckerOptions,
        suffix: Optional[str],
    ):
        """get the save path"""

        try:

            subber = Subber(
                self,
                options,
                {
                    "filename": self.lazy_filename,
                    "suffix": suffix,
                    "classname": self.__class__.__name__,
                    "exp_got": exp_got,
                },
            )

            # calculating the directory path
            t_dirname = self._lazy_get_t_dirname(exp_got, subber)
            _litd = t_dirname.split(os.path.sep)

            dirname_extras = getattr(self, "lazy_dirname_extras", "")
            if dirname_extras:
                # expand something like "foo, bar" into [..."%(foo)s", "%(bar)s"...]
                li_replace = [
                    "%%(%s)s" % (attrname) for attrname in dirname_extras.split()
                ]

                if "%(lazy_dirname_extras)s" in _litd:
                    _litd = replace(_litd, "%(lazy_dirname_extras)s", li_replace)
                else:
                    _litd.extend(li_replace)

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

        except (Exception,) as e:  # pragma: no cover
            pdb.set_trace()
            if cpdb():
                pdb.set_trace()
            raise

    def preformat(self, data, options: LazyCheckerOptions):

        try:

            env = self.lazy_environ
            if not self.lazy_environ.acquired:
                env.clear()
                env.acquire(self.ENVIRONMENT_VARNAME_ROOT)

            self.control = control = _Control(self, env, options)

            tmp = self.lazytemp = self.lazytemp or LazyTemp(control, env, self)
            return options.format(tmp, data)

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    def assert_exp(
        self, got: Any, options: Optional[LazyCheckerOptions], suffix: str = ""
    ):

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
                return

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
                    return
                else:
                    raise

            # the environment requests only equality is checked, without trying to show details
            # typically indicated by setting environment variable `lzrt_directive=nodiff`
            # this may be desired if the differences could cause timeouts with `assertEqual`
            if control.nodiff():
                tmp.message = message = "exp and got are not equal but diffing disabled"
                if exp != formatted_got():
                    raise self.Fail(message)

            try:
                # supports a timeout mechanism, if the module is available
                self.assertEqualTimed(exp, formatted_got)
            except (AssertionError,) as e:  # pragma: no cover
                raise
            except (CustomTimeoutError,) as e:  # pragma: no cover
                tmp.message = message = (
                    "exp and got are not equal but comparison timed out after %s"
                    % (TIMEOUT_MAXTIME_TO_ALLOW)
                )
                self.Fail(message)

            return self.lazytemp

        except (AssertionError,) as e:  # pragma: no cover
            if rpdb():  # pragma: no cover
                pdb.set_trace()

                dn = "/Users/jluc/kds2/issues2/049.lazy/021.p4.v2"
                fnp = os.path.join(dn, "exp.%s.txt" % (self.__class__.__name__))
                with open(fnp, "w") as fo:
                    fo.write(exp)

                fnp = os.path.join(dn, "got.%s.txt" % (self.__class__.__name__))
                with open(fnp, "w") as fo:
                    fo.write(formatted_got)

            raise
        except (Exception,) as e:  # pragma: no cover
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
        assertEqualTimed = assertEqual


class LazyCheckerOptions2(FilterMgr2, LazyCheckerOptions):
    def __init__(self, *filters_in, write_exp_on_ioerror: bool = True):
        self.write_exp_on_ioerror = write_exp_on_ioerror
        self.filters = {}

        self.filterhash = None
        self.reg_callbacks = {}

        for filter_ in filters_in:
            self.set_filter(filter_)

    def get_raw_text_filters(self):
        """ 
        takes all the active and valid FilterDirectives and assign them to a RawFilterMgr or a TextFilterMgr
        this allows the use of set_filter without worrying about whether a filter is a Raw or TextFilter.

        """

        try:

            rawfiltermgr = FilterMgr2()
            textfiltermgr = FilterMgr2()
            for name, directive in self.filters.items():
                if directive.active is not True:
                    continue

                filter_ = directive.filter

                if filter_ is None:
                    raise ValueError(
                        "Directive.%s is active. without a filter" % (directive)
                    )

                if isinstance(filter_, RawFilter):
                    rawfiltermgr.set_filter(directive)
                elif isinstance(filter_, TextFilter):
                    textfiltermgr.set_filter(directive)
                else:
                    raise ValueError(
                        "Directive.%s uses an unknown FilterType.  Filters need be either RawFilter or TextFilter subclasses"
                        % (directive)
                    )

            return rawfiltermgr, textfiltermgr

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise


class LazyMixin2(LazyMixin):

    _filters = None

    @property
    def filters(self):
        """ 
        filters are typically configured at the class level, via `cls_filters`, but need to be deep-copied so that
        each test function can modify them independently.
        Warning:  before Python 3.7 regexes can't be deep-copied so Filters based on 
        Regexes are in fact shallow-copied as the Filters themselves don't get mutated,
        instead relying on the FilterDirective + FilterMgr mechanism for configuration
        and adjustment.
        """

        if self._filters is None:
            res = self._filters = Dummy()

            for name, mgr in getattr(self, "cls_filters", {}).items():
                setattr(res, name, deepcopy(mgr))

        return self._filters

    def assert_exp(self, got: Any, extension: str, suffix: str = ""):
        try:

            checker = self.filters[extension]

            rawfiltermgr, textfiltermgr = checker.get_raw_text_filters()

            core_checker = LazyCheckerOptions(
                extension=extension,
                rawfiltermgr=rawfiltermgr,
                textfiltermgr=textfiltermgr,
            )

            if hasattr(checker, "to_text"):
                core_checker.to_text = checker.to_text
            if hasattr(checker, "prep"):
                core_checker.prep = checker.prep

            return LazyMixin.assert_exp(self, got, core_checker, suffix)

        except (AssertionError,) as e:  # pragma: no cover
            raise
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise
