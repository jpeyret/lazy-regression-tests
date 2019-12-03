######################################################
# Typing
#######################################################
from typing import Optional, Any

#######################################################

import sys

from traceback import print_exc as xp

###################################################################

#######################################################
# optional dependency
#######################################################

try:
    from bs4 import BeautifulSoup as bs
except (ImportError,) as e:
    try:
        from BeautifulSoup import BeautifulSoup as bs
    except (Exception,) as e2:
        bs = None

#######################################################

import pdb


from lazy_regression_tests.utils import (
    nested_dict_get,
    nested_dict_pop,
    set_cpdb,
    set_rpdb,
    first,
    fill_template,
    ppp,
    undefined,
)


def cpdb(**kwds: "Any") -> bool:  # pragma: no cover
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


import re


class FilterMgr:
    """deprecated FilterMgr, using the FilterMgr2 and LazyMixin2 from now"""

    def __repr__(self):
        return "%s[id=%s filters=%s]" % (
            self.__class__.__name__,
            id(self),
            self.filters,
        )

    @classmethod
    def factory(cls, filters):
        if isinstance(filters, cls):
            return filters
        elif not (filters):
            # do-nothing filter...
            return FilterMgr()
        else:
            return cls(filters)

    def __init__(self):

        self.di_filter = {}
        self.filters = []

    def get(self, name):
        return self.di_filter.get(name)

    def __iadd__(self, filter_):
        try:
            if not isinstance(filter_, self.filter_cls):
                filter_ = self.filter_cls.factory(filter_)
            li = self.di_filter.setdefault(filter_.name, [])
            li.append(filter_)
            self.filters.append(filter_)
            return self

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    def filter(self, options, tmp, data):
        for filter_ in self.filters:
            callback = options.reg_callbacks.get(filter_.name)
            data = filter_(options, tmp, data, callback)
        return data

    def pop(self, name: str):
        raise NotImplementedError("%s.pop(%s)" % (self, locals()))


class DataMatcher(object):
    def __repr__(self):
        return "%s.%s:%s" % (self.__module__, self.__class__.__name__, self.name)

    def __init__(self, selector, name):
        self.selector = selector
        self.name = name

    name = None
    scalar = False

    def add_to_filter_hit(self, tmp, value):
        if self.scalar:
            tmp.filterhits[self.name] = value
        else:
            li = tmp.filterhits.setdefault(self.name, [])
            li.append(value)


class RawFilter:
    pass


class RawFilterMgr(FilterMgr):
    filter_cls = RawFilter


class TextFilter:
    pass


class RegexMatcher(TextFilter, DataMatcher):
    def __init__(self, pattern, name, scalar=False, *args):
        self.patre = re.compile(pattern, *args)
        self.name = name
        self.scalar = scalar

    def search(self, *args, **kwds):
        return self.patre.search(*args, **kwds)

    def __getattr__(self, attrname):
        return getattr(self.patre, attrname)

    # pdb.set_trace()
    # version_info = sys.version_info
    # print("version_info:%s" % (version_info))

    if sys.version_info <= (3, 7):

        def __deepcopy__(self, *args, **kwargs):
            """ bit of a cheat here, because before Python 3.7 regex can't be deepcopied
                shouldn't be too much of a problem as the RegexMatchers aren't meant to be modified once
                created, but it still means that that are the same across all filters
            """

            return self


# need to add support for CSS filters #👈!!!TODO!!! 049.lazy.021.p4.v2 🧨 these should be CSS rawfilters


class RegexRemoveSaver(RegexMatcher):
    """this will remove the matching line but also save it"""

    def filter(self, options, tmp, data, callback):

        li = []

        try:
            line_out = []
            for line in data.split("\n"):
                hit = self.patre.search(line)
                if hit:
                    li.append(line)
                    self.add_to_filter_hit(tmp, line)

                else:
                    line_out.append(line)

            if callback:
                callback(self.name, data, li)

            return "\n".join(line_out)
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = filter


class TextFilterMgr(FilterMgr):
    filter_cls = TextFilter


class CSSRemoveFilter(RawFilter, DataMatcher):
    pass

    def __init__(self, pattern, name, scalar=False, *args):
        self.selector = pattern
        self.name = name
        self.scalar = scalar

    def pre_format(self, data):
        try:
            data = bs(data)
            return data
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    def filter(self, options, tmp, data, callback):
        try:

            if isinstance(data, str):
                data = self.pre_format(data)

            li = []

            for hit in data.select(self.selector):

                s_hit = str(hit)
                self.add_to_filter_hit(tmp, hit)
                li.append(hit)

            if callback:
                callback(self.name, data, li)

            for hit in li:
                hit.decompose()

            return data
            # raise NotImplementedError("%s.filter(%s)" % (self, ""))
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = filter


class DictKeyRemoveFilter(RawFilter, DataMatcher):
    pass

    def filter(self, options, tmp, data, callback):

        try:

            value = nested_dict_pop(data, self.selector, None)
            self.add_to_filter_hit(tmp, value)

            if callback:
                callback(self.name, data, value)

            return data

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = filter


class FilterDirective:
    """ Tracks combinations of Filters, active flags, callbacks by name
        
    """

    name = filter = active = callback = None

    def __repr__(self):
        return "%s:%s active:%s callback=%s with %s\n" % (
            self.__class__.__name__,
            self.name,
            self.filter,
            self.active,
            (callback.__name__ if self.callback is not None else None),
        )

    def __init__(
        self, name: str, filter_: Any = None, active: bool = None, callback=None
    ):
        try:
            self.name = name

            # swap arguments if keywords not used
            if isinstance(filter_, bool) and active is None:
                active = filter_
                filter_ = None

            assert active is None or isinstance(active, bool)

            assert filter_ is None or isinstance(filter_, DataMatcher)

            assert callback is None or callable(callback)

            self.filter = filter_
            self.active = active if active in (True, False) else bool(filter_)
            self.callback = callback

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    def copy(self):
        return self.__class__(
            name=self.name,
            filter_=self.filter,
            active=self.active,
            callback=self.callback,
        )


class FilterMgr2:
    """ a filter mgr allows tracking of filters by name, via FilterDirectives

        its core method is  `set_filter` 
    """

    def __repr__(self):

        sub = dict(
            id_="id=%s" % id(self) if verbose else "", name=self.__class__.__name__
        )

        tmpl = "%(name)s[%(id_s)s] filters=%(filters)s"  # % (sub, self)

        return fill_template(tmpl, sub, self, RescueDict())

    def __init__(self, *filters_in):
        self.filters = {}
        for filter_ in filters_in:
            self.set_filter(filter_)

    def filter(self, options, tmp, data):
        """applies its filters to incoming data"""
        try:

            for directive in self.filters.values():

                if not directive.active:
                    continue

                callback = options.reg_callbacks.get(directive.name)
                data = directive.filter(options, tmp, data, callback)
            return data

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    def set_filter(self, name, filter_=None, active=None, callback=None):
        """
        allows successive adjustments of the filters

        you can add FilterDirectives, FilterMgr, or specify everything via
        this method

        Note the importance of using directive.copy:  by intent FilterDirectives and
        FilterMgrs can be shared accross a test suite, so changing any element should
        only happen on copies.

        """

        try:

            if isinstance(name, FilterDirective):
                directive = name.copy()
                self += directive

            elif isinstance(name, FilterMgr2):
                for directive in name.filters.values():
                    self += directive.copy()
            else:
                directive = FilterDirective(
                    name=name, filter_=filter_, active=active, callback=callback
                )
                self += directive

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    def __iadd__(self, directive):
        """ adds a FilterDirective to `self.filters`
            if a directive by that name already existed, it is updated.
        """

        try:

            existing = self.filters.get(directive.name)
            if existing:

                if directive.active in (False, True):
                    existing.active = directive.active

                if directive.filter:
                    existing.filter = directive.filter

                if directive.callback:
                    existing.callback = directive.callback

            else:
                self.filters[directive.name] = directive

            return self

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    def copy(self):
        newinst = self.__class__()
        for name, filter_ in self.filters.items():
            newinst.filters[name] = filter_.copy()
