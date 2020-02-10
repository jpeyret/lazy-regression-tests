import pdb
import sys
import re

from operator import attrgetter

from lazy_regression_tests._baseutils import debugObject, ppp, Dummy, getpath

from traceback import print_exc as xp

#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
)


from lazy_regression_tests.utils import (
    nested_dict_get,
    nested_dict_pop,
    first,
    fill_template,
    ppp,
    RescueDict,
    Subber,
)


verbose = "-v" in sys.argv

undefined = NotImplemented

# https://stackoverflow.com/questions/6102019/type-of-compiled-regex-object-in-python
# yeah, it is what it is, so be it...
type_regex_hack = re.compile("").__class__


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

#######################################################
# Filters
#######################################################


class DataMatcher(object):
    def __repr__(self):
        return "%s.%s:%s" % (self.__module__, self.__class__.__name__, self.name)

    def __init__(self, selector, name):
        self.selector = selector
        self.name = name

    name = None
    scalar = False

    def add_to_filter_hit(self, tmp, value):
        try:
            if self.scalar:
                tmp.filterhits[self.name] = value
            else:
                li = tmp.filterhits.setdefault(self.name, [])
                if not isinstance(li, list):
                    return

                li.append(value)
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class RawFilter:
    raw = True


class TextFilter:
    raw = False


class RegexMatcher(TextFilter, DataMatcher):
    def __init__(self, pattern, name, scalar=False, *args):
        self.patre = re.compile(pattern, *args)
        self.name = name
        self.scalar = scalar

    def search(self, *args, **kwds):
        return self.patre.search(*args, **kwds)

    def __getattr__(self, attrname):
        return getattr(self.patre, attrname)

    if sys.version_info <= (3, 7):

        def __deepcopy__(self, *args, **kwargs):
            """ bit of a cheat here, because before Python 3.7 regex can't be deepcopied
                shouldn't be too much of a problem as the RegexMatchers aren't meant to be modified once
                created, but it still means that instances are the same across all copied Regex-based filters
            """

            return self


class RegexFilter(RegexMatcher):
    def process_line(self, hit, line):
        try:
            raise NotImplementedError(
                "%s.process_line(%s).  need to implement on subclass" % (self, locals())
            )
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def filter(self, options, tmp, data, callback):

        li = []

        try:
            line_out = []
            for line in data.split("\n"):
                hit = self.patre.search(line)
                if hit:
                    line2 = self.process_line(hit, line)
                    line_out.append(line2)
                    self.add_to_filter_hit(tmp, line)
                else:
                    line_out.append(line)

            if callback:
                callback(self.name, data, li)

            return "\n".join(line_out)
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = filter


class RegexSubstitHardcoded(RegexFilter):
    """allows for replacement of the line with different contents

       can't use a re.sub directly because the Filter won't know if 
       it's just a match filter or a match & substitution
    """

    def process_line(self, hit, line):
        try:

            for from_, to_ in self.subs:
                if isinstance(from_, str):
                    line = line.replace(from_, to_)
                elif hasattr(from_, "sub"):
                    line = from_.sub(to_, line)
                else:
                    raise NotImplementedError(
                        f"{self}.process_line(from_:{from_}, to_:{to_})"
                    )

            return line

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def __init__(self, pattern, name, subs, scalar=False, *args):
        super(RegexSubstitHardcoded, self).__init__(pattern, name, scalar)
        self.subs = subs


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
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = filter


#######################################################
# Filter management
#######################################################


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

            self.raw = getattr(filter_, "raw", False)

            self.filter = filter_
            self.active = active if active in (True, False) else bool(filter_)
            self.callback = callback

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
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


class FilterManager:
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

    def get_raw_text_filters(self):
        """docstring"""
        try:

            raws = []
            texts = []

            for key, filter_ in self.filters.items():
                if filter_.raw:
                    raws.append(filter_)
                else:
                    texts.append(filter_)

            return (raws, texts)
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def filter(self, options, tmp, data):
        """applies its filters to incoming data"""
        try:

            for directive in self.filters.values():

                if not directive.active:
                    continue

                callback = options.reg_callbacks.get(directive.name)
                data = directive.filter(options, tmp, data, callback)
            return data

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
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

            elif isinstance(name, FilterManager):
                for directive in name.filters.values():
                    self += directive.copy()
            else:
                directive = FilterDirective(
                    name=name, filter_=filter_, active=active, callback=callback
                )
                self += directive

            return self

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
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

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def copy(self):
        newinst = self.__class__()
        for name, filter_ in self.filters.items():
            newinst.filters[name] = filter_.copy()
        return newinst


class RawFilterManager(FilterManager):
    filter_cls = RawFilter


class TextFilterManager(FilterManager):
    filter_cls = TextFilter


#######################################################
# Filters
#######################################################


def build_filters_for_class(cls, li_ancestor_filter):
    """build filters for class, before instance overrides"""
    try:

        # remember, the mro for a class includes the class itself
        if not li_ancestor_filter:
            return {}

        last_ = li_ancestor_filter[-1]

        if last_ is getattr(cls, "cls_filters", None):
            return last_

        first_filt = first(li_ancestor_filter)

        di_debug = dict(
            first_filt_keys=first_filt.keys(), len_first_filt=len(first_filt)
        )

        raise NotImplementedError(
            "build_filters_for_class(%s):\ndi_debug:%s" % (cls.__name__, di_debug)
        )
    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if 1 or rpdb() or cpdb():
            pdb.set_trace()
        raise
