import pdb
import os

from pathlib import Path

undefined = NotImplemented


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

from timeout_decorator import timeout, TimeoutError as CustomTimeoutError


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

from lazy_regression_tests._baseutils import debugObject, ppp, Dummy

from traceback import print_exc as xp

from .validators import ValidationManager, NamedTesteeAttributeValidator


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


class LazyCheckerOptions:
    pass


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


#######################################################
#
#######################################################


class _LazyMeta(type):
    def __new__(mcls, name, bases, attrs, **kwargs):
        cls_ = super(_LazyMeta, mcls).__new__(mcls, name, bases, attrs)
        return cls_

    def __init__(cls, name, bases, attrs, **kwargs):
        """ 
        intercepting the newly created class allows stacking of the 
        ancestral validators and formatters in reverse mro order
        i.e. top of ancestors go first

        👆 TODO: filters too

        """

        try:

            # we want to build out the validators by running the basic ancestral ones first
            # ex:  check status=200 and content_type = html before checking <title>
            li_bases2current = reversed(cls.mro())

            # pick _this_ class's validators
            li_ori = getattr(cls, "cls_validators", [])
            if li_ori and not isinstance(li_ori, list):
                li_ori = [li_ori]
            else:
                li_ori = li_ori.copy()

            li_new = []

            # and now add the bases' validators
            for basecls in li_bases2current:
                validators = getattr(basecls, "cls_validators", [])

                if validators:
                    if not isinstance(validators, list):
                        validators = [validators]
                    li_new.extend(validators)

            cls.cls_validators = li_new + li_ori

            #!!!TODO!!! 049.lazy.026.lazy3 👇
            # add same for filters, by extension

            #!!!TODO!!! 049.lazy.026.lazy3 👆

            return super().__init__(name, bases, attrs)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class LazyMixin(metaclass=_LazyMeta):
    cls_filters = {}
    cls_validators = []
    add_lazy_dirname = []

    lazytemp = None
    lazy_basename_extras = ""

    # this normally resolves to os.environ, but can be preset for testing
    lazy_environ = MediatedEnvironDict()

    T_FILENAME = "%(filename)s %(classname)s %(_testMethodName)s %(lazy_basename_extras)s %(suffix)s %(extension)s"

    ENVIRONMENT_VARNAME_ROOT = "lzrt_"

    @classmethod
    def get_basename(cls, name_, file_, module_):
        cls.lazy_pa = pa = Path(file_)
        return pa.stem

    #######################################################
    # dubious
    #######################################################

    def preformat(self, data, options: "LazyCheckerOptions"):

        pdb.set_trace()

        return  # 🧨049.lazy.026.lazy3

        try:

            env = self.lazy_environ
            if not self.lazy_environ.acquired:
                env.clear()
                env.acquire(self.ENVIRONMENT_VARNAME_ROOT)

            self.control = control = _Control(self, env, options)

            tmp = self.lazytemp = self.lazytemp or LazyTemp(control, env, self)

            # 🤔 ahhh, but we need this to BeautifulSoup or do other stuff...
            return options.format(tmp, data)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def _lazy_get_t_dirname(self, exp_got, subber):

        env_name = dict(exp="template_dirname_exp", got="template_dirname_got")[exp_got]
        dirname = self.control.env[env_name]

        dirname2 = os.path.join(dirname, subber.get("classname"))

        return dirname2

    def _get_fnp_save(
        self, exp_got: Union["got", "exp"], options: str, suffix: Optional[str]
    ):
        """get the save path"""

        try:

            extension = options

            subber = Subber(
                self,
                options,
                {
                    "filename": self.lazy_filename,
                    "suffix": suffix,
                    "classname": self.__class__.__name__,
                    "exp_got": exp_got,
                    "extension": extension,
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

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    #######################################################
    # validator related
    #######################################################

    _validationmgr = undefined

    @property
    def validationmgr(self):
        if self._validationmgr is undefined:
            res = None
            self._validationmgr = res = ValidationManager(self, *self.cls_validators)

        return self._validationmgr

    def check_expectations(self, **sources):
        try:
            self.validationmgr.check_expectations(self, **sources)
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

            # pdb.set_trace()
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
                # pdb.set_trace()
                raise
            # timeout_decorator.timeout_decorator.TimeoutError
            except (
                Exception,
            ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
                if cpdb():
                    pdb.set_trace()
                raise

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
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise
