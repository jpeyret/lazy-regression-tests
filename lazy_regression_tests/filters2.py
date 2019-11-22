#######################################################
# Typing
#######################################################
from typing import Optional, Any

#######################################################


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

    def filter(self, tmp, data):
        for filter_ in self.filters:
            data = filter_(tmp, data)
        return data

    def pop(self, name: str):
        raise NotImplementedError("%s.pop(%s)" % (self, locals()))


class DataMatcher(object):
    def __repr__(self):
        return "%s.%s:%s" % (self.__module__, self.__class__.__name__, self.name)

    name = None
    scalar = False


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

    def filter(self, tmp, data):
        try:
            line_out = []
            for line in data.split("\n"):
                hit = self.patre.search(line)
                if hit:
                    if self.scalar:
                        tmp.filterhits[self.name] = line
                    else:
                        li = tmp.filterhits.setdefault(self.name, [])
                        li.append(line)
                else:
                    line_out.append(line)

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

    def filter(self, tmp, data):
        try:
            raise NotImplementedError("%s.filter(%s)" % (self, ""))
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = filter


class DictKeyRemoveFilter(RawFilter, DataMatcher):
    pass

    def filter(self, tmp, data):
        try:
            raise NotImplementedError("%s.filter(%s)" % (self, ""))
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = filter
