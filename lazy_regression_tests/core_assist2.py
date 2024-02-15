"""
supports class-level aggregation of Lazy Filters and Validators
"""
import os
import sys
from typing import List, Any, Dict, cast, Tuple, Optional
from collections import defaultdict
import pprint
from dataclasses import dataclass

from pathlib import Path

#################################################################
# Dependencies
#################################################################
from more_itertools import partition

from lazy_regression_tests.basics import get_alias_from_ancestors

from lazy_regression_tests.providers import (
    di_ext_provider,
    PAbstractExtProvider,
    DEFAULT_PROVIDER,
)
from lazy_regression_tests.validators import ValidatorMgr, build_validators_for_class
from lazy_regression_tests.constants import (
    ENVIRONMENT_VARNAME_ROOT,
    LAZY_HEADER_SEPARATOR,
    TIMEOUT_MAXTIME_TO_ALLOW,
)
from lazy_regression_tests.common import (
    ExtAlias,
    ConfigurationException,
    TU_NOCATCH,
    LazyTemp,
    ValidatorTemp,
    timeout,
    Checker,
)

# import constants

from lazy_regression_tests.filters import Filter, FilterMgr, BFilter


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

#################################################################
# Dependencies
#################################################################

undefined = NotImplemented

# disable stuff that makes this module's audit noisy
# pylint: disable=no-self-argument,super-init-not-called,no-member,bad-mcs-method-argument
# pylint: disable=bad-mcs-classmethod-argument,no-name-in-module,line-too-long

from pydantic import BaseModel, Field

from lazy_regression_tests._baseutils import set_cpdb, set_rpdb, set_breakpoints3, ppp


if __name__ == "__main__":
    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints

verbose = False


class _HelperRoot:
    def __init__(self, lz: "LazyRoot"):
        self.lz = lz

    _filters = _validators = undefined

    @property
    def filters(self) -> Dict[str, FilterMgr]:
        "return filters"
        if self._filters is undefined:
            self._filters = {f.ext: f for f in self.lz.filters}
        return self._filters

    @property
    def validators(self) -> Dict[str, ValidatorMgr]:
        "return validators"
        if self._validators is undefined:
            self._validators = {f.ext: f for f in self.lz.validators}
        return self._validators

    def __getattr__(self, attrname: str):
        """returns Checker for attrname"""
        try:

            filter_ = self.filters.get(attrname)
            validator = self.validators.get(attrname)

            if not filter_ and not validator:
                raise AttributeError(
                    f"unknown {attrname} known filters={'/'.join(self.filters.keys())} validators={'/'.join(self.validators.keys())}"
                )

            checker = Checker(lz=self.lz, f=filter_, v=validator, ext=attrname)
            setattr(self.lz, attrname, checker)
            return checker

        # pragma: no cover pylint: disable=unused-variable
        except (AttributeError,) as e:
            raise
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


@dataclass
class LazyRoot:
    """
    class and instance level root behavior for lazy
    intent is to allow things like `self.lz.html.val.title`
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
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
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

            print("\n", "🔎" * 30, file=out)
            print(f"{self.__class__.__name__}.extensions:{self.extensions}", file=out)
            print("\n", "🔎" * 30, "\n", file=out)

            for ext in self.extensions:
                checker: Checker = getattr(self, ext)
                checker.show(file=out, nesting="  ")
            print(out.getvalue())

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
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
            print(f"{cls.__name__}")
        # gather all the past and current filters in a list, by extension
        for ix, acls in enumerate(ancestors):
            if verbose:
                print(f"{ix:02} ancestor={acls.__name__}")
            for ext, values in acls.cls_filters.items():

                if isinstance(values, FilterMgr):
                    values = values.filters

                elif not isinstance(values, list):
                    values = [values]

                if verbose:
                    print(f"   {ext:6.6} {values=}")

                li = di_filter[ext]
                li.extend(values)

        li_filtermgr: List[FilterMgr] = []
        di_filtermgr = {}
        for name, filters in di_filter.items():
            di = {}
            filters0 = filters
            alias_ = None

            # ExtProvider by name or alias
            if isinstance(filters, (list, tuple)):
                # if name == "settings":
                #     breakpoint() #🛑
                #     pass
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
                ppp(dict(ext=ext, name=name, alias=alias_), msg)

            filtermgr = di_filtermgr[name] = FilterMgr(
                ext=name, filters=list(di.values()), alias=alias_
            )

            li_filtermgr.append(filtermgr)

        return di_filtermgr

    # pragma: no cover pylint: disable=unused-variable
    except (TU_NOCATCH) as e:
        raise
    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
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
    lz: LazyRoot

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
            """fallback if timeout package is not available"""
            try:
                self.assertEqual(exp, got, message)
            except (AssertionError,) as e:
                raise self.format_assertion_message(e)


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
            # pylint: disable=bad-super-call
            def initialize_instance(self, *args, **kwargs):
                """injecting an `__init__` that will happen before the TestCase.__init__"""
                super(newclass, self).__init__(*args, **kwargs)  # type: ignore
                # self.filters = {k: v.copy(deep=True) for k, v in self.cls_filters.items()}
                self.lz = self.__class__.lz.clone(testee=self)

            # we want to inject this so that it always comes before TestCase.__init__
            setattr(newclass, "__init__", initialize_instance)
            return newclass
        # pragma: no cover pylint: disable=unused-variable
        except (TypeError,) as e:
            print(f"\n\n{e=}")
            ppp(dict(clsname=clsname, found=found, basesold=basesold, bases=bases))
            if cpdb():
                breakpoint()
            raise

        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def __init__(cls, name, bases, attrs, **kwargs):
        """aggregate cls_filters, cls_validators from ancestors and cls"""
        try:
            li_bases2current = list(reversed(cls.mro()))

            # if name == "Base2":
            #     breakpoint() #🛑
            #     pass

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

            cls.lz = lz

            super().__init__(name, bases, attrs)
        # pragma: no cover pylint: disable=unused-variable
        except (ConfigurationException,) as e:
            cls.lz = e
        except (TU_NOCATCH) as e:
            raise
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise
