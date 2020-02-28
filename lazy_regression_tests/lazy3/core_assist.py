""" core LazyMixin functionality 

be very cautious of referencing self.<attribute> when there is no 'lazy' prefix to it

for this reason auxiliary classes have been moved to core_assist.py

"""

import pdb
import os

# pylint: disable=unused-wildcard-import,wildcard-import,unused-import
from .common import *

#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    Union,
)

from lazy_regression_tests._baseutils import ppp, Dummy

from traceback import print_exc as xp


# pylint: enable=unused-wildcard-import,wildcard-import,unused-import

from .validators import build_validators_for_class
from .filters import build_filters_for_class


#######################################################


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


class LazyChecker:

    extension = "?"

    def __repr__(self):
        return "%s[%s]" % (self.__class__.__name__, self.extension)

    def __init__(
        self,
        extension: str,
        rawfiltermgr=None,
        textfiltermgr=None,
        # write_exp_on_ioerror: bool = True,
    ):
        self.lazy_extension = self.extension = extension

        # self.write_exp_on_ioerror = write_exp_on_ioerror
        self.rawfiltermgr = rawfiltermgr
        self.textfiltermgr = textfiltermgr

        self.filterhash = None

        self.reg_callbacks = {}

    def debug(self, ix, lines):
        print("\n".join(lines[ix - 5 : +ix + 5]))

    def prep(self, tmp, data):
        return data

    def to_text(self, tmp, data):
        return str(data)

    def filter_raw(self, tmp, data):
        return self.rawfiltermgr.filter(self, tmp, data)

    def filter_text(self, tmp, data):
        return self.textfiltermgr.filter(self, tmp, data).strip()

    def format(self, tmp, data, fnp_raw):
        try:
            # used to only format once
            if (
                isinstance(data, str)
                and self.filterhash
                and self.filterhash == hash(data)
            ):
                return data

            data = self.prep(tmp, data)

            if fnp_raw:
                str_data = self.to_text(tmp, data)

                dirname = os.path.dirname(fnp_raw)
                if not os.path.isdir(dirname):
                    os.makedirs(dirname)

                with open(fnp_raw, "w") as fo:
                    fo.write(str_data)

            data = self.filter_raw(tmp, data)
            str_data = self.to_text(tmp, data)
            str_data = self.filter_text(tmp, str_data)

            self.filterhash = hash(str_data)

            return str_data
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                ppp(self, self)
                pdb.set_trace()
            raise


class ExecInfo:
    def __init__(self):
        self.ioerror_exp = self.ioerror_got = None


class LazyTemp(object):
    def __repr__(self):
        return "LazyTemp[id=%s]" % (id(self))

    def __init__(self, control, env, testee):
        self.control = control
        self.fnp_exp = self.fnp_got = None
        self.env = env.copy()
        self.message = ""
        self.filtered = Dummy()
        self.testee = testee

        self.execinfo = ExecInfo()

    def add_filtered(self, name, value, scalar):
        """ each filter saves what it finds here """
        try:
            if scalar:
                setattr(self.filtered, name, value)
            else:
                li = getattr(self.filtered, name, None)
                if li is None:
                    li = []
                    setattr(self.filtered, name, li)

                li.append(value)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


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


class _Control(object):
    """unifies environment and function arguments
       to determine handlers for IOError and AssertionError
       save in the LazyTemp results object as well.
    """

    def __init__(
        self, lazy: "LazyMixin", env: MediatedEnvironDict, options: "LazyCheckerOptions"
    ):

        self.lazy = lazy
        self.env = env
        self.options = options

    _save_raw = undefined

    @property
    def save_raw(self):
        """ this depend on 2 environmental settings:
            :param lzrt_save_raw_received_data : if it it's set we can do it
            :param lzrt_template_dirname_report : where to put it
        """

        if self._save_raw is undefined:
            res = bool(self.env.get("template_dirname_report"))
            self._save_raw = bool(res and self.env.get("save_raw_received_data"))
        return self._save_raw

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
    def __init__(cls, name, bases, attrs, **kwargs):
        """ 
        intercepting the newly created class allows stacking of the 
        ancestral validators and formatters in reverse mro order
        i.e. top of ancestors go first
        """

        try:

            classname = cls.__name__

            # we want to build out the validators by running the basic ancestral ones first
            # ex:  check status=200 and content_type = html before checking <title>
            li_bases2current = list(reversed(cls.mro()))

            li_ancestor_filter = []

            for basecls in li_bases2current:

                cls_filters = getattr(basecls, "cls_filters", {})

                if cls_filters:
                    li_ancestor_filter.append(cls_filters)

            cls.cls_validators = build_validators_for_class(cls, li_bases2current)

            cls.cls_filters = build_filters_for_class(cls, li_ancestor_filter)

            super().__init__(name, bases, attrs)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise
