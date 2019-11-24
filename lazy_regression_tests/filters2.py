######################################################
# Typing
#######################################################
from typing import Optional, Any

#######################################################


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

    def filter(self, options, tmp, data, callback):
        try:
            # hit = data.select(self.selector)

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

            value = nested_dict_pop(data, self.selector)
            self.add_to_filter_hit(tmp, value)

            if callback:
                callback(self.name, data, value)

            return data

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = filter
