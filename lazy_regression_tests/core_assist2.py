"""
supports class-level aggregation of Lazy Filters and Validators
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List

#################################################################
# Dependencies
#################################################################
from more_itertools import partition

from lazy_regression_tests._baseutils import ppp, set_breakpoints3, set_cpdb, set_rpdb
from lazy_regression_tests.basics import ALazyRoot, get_alias_from_ancestors
from lazy_regression_tests.common import (
    TU_NOCATCH,
    Checker,
    ConfigurationException,
    ExtAlias,
    get_lazy_logger,
    timeout,
)
from lazy_regression_tests.constants import (
    TIMEOUT_MAXTIME_TO_ALLOW,
)
from lazy_regression_tests.filters import BFilter, FilterMgr
from lazy_regression_tests.providers import (
    di_ext_provider,
)
from lazy_regression_tests.validators import ValidatorMgr, build_validators_for_class


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


logger = get_lazy_logger()
rpdb = breakpoints = cpdb
undefined = NotImplemented

if __name__ == "__main__":
    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints

verbose = False


class _HelperRoot:
    def __init__(self, lz: "LazyRoot"):
        self._lz = lz

    _filters = _validators = undefined

    @property
    def filters(self) -> Dict[str, FilterMgr]:
        "return filters"
        if self._filters is undefined:
            self._filters = {f.ext: f for f in self._lz.filters}
        return self._filters

    @property
    def validators(self) -> Dict[str, ValidatorMgr]:
        "return validators"
        if self._validators is undefined:
            self._validators = {f.ext: f for f in self._lz.validators}
        return self._validators

    def __getattr__(self, attrname: str):
        """returns Checker for attrname"""
        try:

            filter_ = self.filters.get(attrname)
            validator = self.validators.get(attrname)

            if not filter_ and not validator:
                tmp1 = '/'.join(self.filters.keys())
                raise AttributeError(
                    f"unknown {attrname} known filters={tmp1} validators={'/'.join(self.validators.keys())}"
                )

            checker = Checker(_lz=self._lz, f=filter_, v=validator, ext=attrname)
            setattr(self._lz, attrname, checker)
            return checker

        # pragma: no cover
        except (AttributeError,) as _e:
            raise
        except (Exception,) as _e:
            if cpdb():
                breakpoint()
            raise


@dataclass
class LazyRoot(ALazyRoot):
    """
    class and instance level root behavior for lazy
    intent is to allow things like `self._lz.html.val.title`
    """

    filters: List[FilterMgr]
    validators: List[ValidatorMgr]
    testee: Any = None
    h: _HelperRoot = None

    _extensions = undefined

    @property
    def extensions(self):
        "show available extensions"
        if self._extensions is undefined:
            res = self._extensions = set([o.ext for o in self.filters])
            res.update(set([o.ext for o in self.validators]))
        return sorted(self._extensions)

    def clone(self, testee=None):
        """clone a LazyRoot"""
        try:
            validators = []
            for v in self.validators:
                validators.append(v.copy(deep=True, exclude={"checker"}))

            filters = [fmgr.clone() for fmgr in self.filters]
            dupe = LazyRoot(validators=validators, filters=filters, testee=testee)
            if testee:
                for val in dupe.validators:
                    val.testee = testee
                dupe.testee = testee
            return dupe
        # pragma: no cover
        except (Exception,) as _e:
            if cpdb():
                breakpoint()
            raise

    def __getattr__(self, attrname: str) -> Checker:
        """route anything unknown to the helper
        should be a Checker for the extension
        """

        if attrname.startswith("__"):
            raise AttributeError

        return getattr(self.h, attrname)

    def __post_init__(self):
        "initialize"
        self.h = _HelperRoot(self)

    def show(self):
        try:
            from io import StringIO

            out = StringIO()

            print("\n", "🔎" * 30, file=out) # debugging
            print(f"{self.__class__.__name__}.extensions:{self.extensions}", file=out) # debugging
            print("\n", "🔎" * 30, "\n", file=out) # debugging

            for ext in self.extensions:
                checker: Checker = getattr(self, ext)
                checker.show(file=out, nesting="  ")
            print(out.getvalue()) # debugging

        # pragma: no cover
        except (Exception,) as _e:
            if cpdb():
                breakpoint()
            raise


def build_filters_for_class(
    cls: type, ancestors_in: List[type], di_alias: Dict[str, str]
):
    """build FilterMgrs for a class by adding up filters by extension from all its supers and itself
    and assign them to cls_Filters
    """
    try:
        di_filter = defaultdict(list)
        ancestors = [
            ancestor for ancestor in ancestors_in if hasattr(ancestor, "cls_filters")
        ]

        if verbose:
            logger.debug(f"{cls.__name__}")
        # gather all the past and current filters in a list, by extension
        for ix, acls in enumerate(ancestors):
            if verbose:
                logger.debug(f"{ix:02} ancestor={acls.__name__}")
            for ext, values in acls.cls_filters.items():

                if isinstance(values, FilterMgr):
                    values = values.filters

                elif not isinstance(values, list):
                    values = [values]

                if verbose:
                    logger.debug(f"   {ext:6.6} {values=}")

                li = di_filter[ext]
                li.extend(values)

        li_filtermgr: List[FilterMgr] = []
        di_filtermgr = {}
        for name, filters in di_filter.items():
            di = {}
            alias_ = None

            # ExtProvider by name or alias
            if isinstance(filters, (list, tuple)):
                filters, aliases = [
                    list(v) for v in partition(ExtAlias.is_instance, filters)
                ]
                if aliases:
                    alias_ = aliases[-1].alias
                    di_alias[name] = alias_

            else:
                if isinstance(filters, ExtAlias):
                    alias_ = filters.alias
                    di_alias[name] = alias_

            alias_ = alias_ or di_alias.get(name)

            if not alias_:
                alias_ = get_alias_from_ancestors(cls, ancestors_in, name)
                if alias_:
                    di_alias[name] = alias_

            ext_provider = di_ext_provider[alias_ or name]

            for v_in in filters:

                if isinstance(v_in, BFilter):
                    filter2 = v_in
                else:
                    filter2 = ext_provider.build_filter(v_in)

                # here's the tricky part.  we assign the filter to its hash in a dictionary
                # so later filters in the list - like inactive ones - replace the earlier ones)
                di.__setitem__(filter2, filter2)

            # and now we reassign the list, which is now unique by filter, in their original position
            # of declaration
            if name == "settings" and alias_ is None:
                msg = f"\n\nbuild_filters_for_class {cls=} {name=}, {ext=}"
                logger.debug(msg)

            filtermgr = di_filtermgr[name] = FilterMgr(
                ext=name, filters=list(di.values()), alias=alias_
            )

            li_filtermgr.append(filtermgr)

        return di_filtermgr

    # pragma: no cover
    except (TU_NOCATCH) as _e:
        raise
    # pragma: no cover
    except (Exception,) as _e:
        if cpdb():
            breakpoint()
        raise


#################################################################
# TestCase-facing code
#################################################################


class LazyMixin:
    """added Lazy functionality at the TestCase level"""

    # populated by _LazyMeta
    cls_filters: Dict[str, FilterMgr]
    _lz: LazyRoot

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
            except (AssertionError,) as _e:
                raise self.format_assertion_message(_e)

    else:
        #
        def assertEqualTimed(self, exp, got, message=None):
            """fallback if timeout package is not available"""
            try:
                self.assertEqual(exp, got, message)
            except (AssertionError,) as _e:
                raise self.format_assertion_message(_e)


class _LazyMeta(type):
    def __new__(mcls, clsname, bases, dct):
        """
        1. decorate class with custom methods
        2. inject LazyMixin, ONCE, into bases
        """
        try:

            basesold = bases[:]
            found = False
            for bcls in bases:
                if issubclass(bcls, LazyMixin):
                    found = True
                    break
            if not found:
                bases = (LazyMixin,) + bases
                pass

            newclass = super(_LazyMeta, mcls).__new__(mcls, clsname, bases, dct)

            # this particulal super call format was necessary to get it
            # working at runtime
            #
            def initialize_instance(self, *args, **kwargs):
                """injecting an `__init__` that will happen before the TestCase.__init__"""
                super(newclass, self).__init__(*args, **kwargs)  # type: ignore
                self._lz = self.__class__._lz.clone(testee=self)

            # we want to inject this so that it always comes before TestCase.__init__
            setattr(newclass, "__init__", initialize_instance)
            return newclass
        # pragma: no cover
        except (TypeError,) as _e:
            logger.exception(_e)
            if cpdb():
                ppp(dict(clsname=clsname, found=found, basesold=basesold, bases=bases))  # debugging
                breakpoint()

            raise

        except (Exception,) as _e:
            if cpdb():
                breakpoint()
            raise

    def __init__(cls, name, bases, attrs, **kwargs):
        """aggregate cls_filters, cls_validators from ancestors and cls"""
        try:
            li_bases2current = list(reversed(cls.mro()))

            if breakpoints('LazyMeta', {'classname': cls.__name__}):  # pragma: no cover
                cls_validators = attrs.get("cls_validators")
                print(f'\n\n!!!classname:{cls.__name__} {cls_validators=}') # debugging
                breakpoint()
                pass

            cls.__lz_ori = dict(
                cls_validators=cls.__dict__.get("cls_validators", {}),
                cls_filters=cls.__dict__.get("cls_filters", {}),
            )

            di_alias = {}

            cls.cls_filters = build_filters_for_class(cls, li_bases2current, di_alias)

            validators = build_validators_for_class(cls, li_bases2current, di_alias)

            cls.cls_validators = validators


            lz = LazyRoot(
                filters=list(cls.cls_filters.values()),
                validators=list(validators.values()),
            )

            cls._lz = lz

            super().__init__(name, bases, attrs)
        # pragma: no cover
        except (ConfigurationException,) as _e:
            cls.lz = _e
        except (TU_NOCATCH) as _e:
            raise
        except (Exception,) as _e:
            if cpdb():
                breakpoint()
            raise
