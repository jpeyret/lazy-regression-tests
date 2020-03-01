import pdb
import sys
import re
import json

# pylint: disable=unused-import
from lazy_regression_tests._baseutils import debugObject, ppp, Dummy, getpath
from traceback import print_exc as xp

# pylint: enable=unused-import


#######################################################
# Dependencies
#######################################################

# from bs4 import BeautifulSoup as bs

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
    DictFormatter,
    InvalidConfigurationException,
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

    name: str = None
    scalar = False
    selector: str = None

    def __repr__(self):
        try:
            return f"{self.__class__.__name__:30.30} selector:{self.selector} name:{self.name}"
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,):
            return "%s.%s:%s" % (self.__module__, self.__class__.__name__, self.name)

    def __init__(self, selector, name):
        self.selector = selector
        self.name = name

    def format_filtered_hook(self, value):
        return value

    def add_to_filter_hit(self, tmp, value):
        try:

            value = self.format_filtered_hook(value)

            tmp.add_filtered(self.name, value, self.scalar)
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
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


class DictFilter(RawFilter, DataMatcher):

    scalar = True
    dict_ = "?"

    def __repr__(self):
        return "%s[%s]=%s" % (self.__class__.__name__, self.name, self.dict_)

    def __init__(self, dict_: dict, name: str):
        assert isinstance(dict_, dict)
        self.dict_ = dict_
        self.name = name
        self.formatter = DictFormatter(di_default_formatter=dict_)

    def filter(self, options, tmp, data, callback=None):
        try:
            keep = {}
            data = self.formatter.process(data, keep=keep, in_place=False)
            self.add_to_filter_hit(tmp, keep)
            return data

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


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

    def filter(self, options, tmp, data, callback=None):

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

    def filter(self, options, tmp, data, callback=None):

        li = []

        try:
            line_out = []
            lines = data.split("\n")
            for ix, line in enumerate(lines):
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

    name = filter_ = active = callback = None

    def __repr__(self):

        try:
            return f"{self.__class__.__name__:30.30} active:{self.active} filter:{str(self.filter_):30.30}"

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            pdb.set_trace()
            return "%s.%s" % (self.__class__.__name__, self.name)
            # raise

        return "%s:%s active:%s callback=%s with %s\n" % (
            self.__class__.__name__,
            self.name,
            self.filter_,
            self.active,
            (self.callback.__name__ if self.callback is not None else None),
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

            assert filter_ is None or isinstance(
                filter_, DataMatcher
            ), "unexpected filter_ type: %s" % (filter_)

            assert callback is None or callable(callback)

            self.raw = getattr(filter_, "raw", False)

            self.filter_ = filter_
            self.active = active if active in (True, False) else bool(filter_)
            self.callback = callback

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def filter(self, *args, **kwargs):
        return self.filter_.filter(*args, **kwargs)

    def copy(self):
        return self.__class__(
            name=self.name,
            filter_=self.filter_,
            active=self.active,
            callback=self.callback,
        )


class FilterManager:
    """ a filter mgr allows tracking of filters by name, via FilterDirectives

        its core method is  `set_filter` 
    """

    def prep(self, tmp, data):
        """default do-nothing implementation"""
        try:
            return data
        # pragma: no cover pylint: disable=unused-variable, broad-except
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def to_text(self, tmp, data):
        """default do-nothing implementation"""
        try:
            return str(data)
        # pragma: no cover pylint: disable=unused-variable, broad-except
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def __repr__(self):

        try:
            filters = sorted(self.filters.keys())
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            filters = self.filters

        sub = dict(
            id_="id=%s" % id(self) if verbose else "",
            name=self.__class__.__name__,
            filters=filters,
        )

        tmpl = "%(name)s[%(id_)s] filters=%(filters)s"  # % (sub, self)

        return fill_template(tmpl, sub, self, RescueDict())

    def __init__(self, *filters_in):
        self.filters = {}
        for filter_ in filters_in:
            self.set_filter(filter_)

    def get_raw_text_filters(self):
        """docstring"""
        try:

            rawfiltermgr = RawFilterManager()
            textfiltermgr = TextFilterManager()
            for name, directive in self.filters.items():
                if directive.active is not True:
                    continue

                filter_ = directive.filter_

                if filter_ is None:
                    raise InvalidConfigurationException(
                        f"Directive.{name} : {directive} is active. without a filter"
                    )

                if isinstance(filter_, RawFilter):
                    rawfiltermgr.set_filter(directive)
                elif isinstance(filter_, TextFilter):
                    textfiltermgr.set_filter(directive)
                else:
                    raise InvalidConfigurationException(
                        "Directive.%s uses an unknown FilterType.  Filters need be either RawFilter or TextFilter subclasses"
                        % (directive)
                    )

            return rawfiltermgr, textfiltermgr

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def filter(self, options, tmp, data):
        """applies its filters to incoming data"""
        try:
            callbacks = getattr(options, "reg_callbacks", {})

            for name, directive in self.filters.items():

                if not directive.active:
                    continue

                callback = callbacks.get(directive.name)
                data = directive.filter(options, tmp, data, callback)
            return data

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
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

        if breakpoints("set_filter", {"name": name}):  # pragma: no cover
            pdb.set_trace()

        try:

            if isinstance(name, FilterDirective):
                directive = name.copy()
                self += directive

            elif isinstance(name, FilterManager):

                # hmmm, wonder if we could override the FilterManager class here....

                for directive in name.filters.values():
                    self += directive.copy()
            else:
                directive = FilterDirective(
                    name=name, filter_=filter_, active=active, callback=callback
                )
                self += directive

            return self

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
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

                if directive.filter_:
                    existing.filter_ = directive.filter_

                if directive.callback:
                    existing.callback = directive.callback

            else:
                self.filters[directive.name] = directive

            return self

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def copy(self):
        newinst = self.__class__()
        for name, filter_ in self.filters.items():
            newinst.filters[name] = filter_.copy()
        return newinst

    def debug(self, testee):

        try:
            padder = "⚙️" * 6 + "  lazy-tests configuration  " + "⚙️" * 6
            print(f"\n{padder}\n{self}  filters:")

            for key in self.filters:
                value = self.filters[key]
                print(
                    f"  {key:20.20}: active:{str(value.active):5.5} filter:{str(value.filter_):30.30}"
                )

            li_revmro = list(reversed(testee.__class__.mro()))

            li = [
                (cls, getattr(cls, "cls_filters", {}).get("html")) for cls in li_revmro
            ]

            li = [tu_ for tu_ in li if tu_[1]]

            print(
                "\n\n ⚙️class-level inheritance:\n%s\n"
                % "\n".join([tu[0].__name__ for tu in li])
            )

            actual = None
            for cls, filt_ in li:
                oi = filt_.filters
                # print(f"\n{cls.__name__:30.30} {filt_} filters.id:{id(filt_.filters)}")

                for key, actual in oi.items():
                    filter_ = getattr(actual, "filter_", actual)
                    print(
                        f"  {key:20.20} : active:{actual.active} {str(filter_):40.40} id actual:{id(actual)}"
                    )

            print(f"\n{padder}\n")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if 1 or cpdb():
                pdb.set_trace()
            raise


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

        classname = cls.__name__

        # breakpoints dont work for now as the class defs are an import time execution
        # not a call time execution
        if breakpoints(
            "build_filters_for_class", dict(classname=classname)
        ):  # pragma: no cover
            pdb.set_trace()

        # remember, the mro for a class includes the class itself
        if not li_ancestor_filter:
            return {}

        if len(li_ancestor_filter) == 0:
            raise NotImplementedError("%s.build_filters_for_class(%s)" % (cls, {}))

        if len(li_ancestor_filter) >= 1:

            # first, build a set of all extensions
            s_extension = set()
            for di in li_ancestor_filter:
                s_extension |= set(di.keys())

            finals = getattr(cls, "cls_filters", {})

            ancestors = li_ancestor_filter

            res = {}

            for extension in s_extension:
                li = [di.get(extension) for di in ancestors]
                li = [di for di in li if di]

                mgr_cls = None
                mgr = finals.get(extension)

                if not isinstance(mgr, FilterManager):

                    mgr = None
                    for cand in li:
                        if isinstance(cand, FilterManager):
                            mgr = cand

                    mgr_cls = mgr.__class__ if mgr else FilterManager

                else:
                    mgr_cls = mgr.__class__

                mgr_cls = mgr_cls or FilterManager

                newfilter = mgr_cls()
                for directive3 in li:
                    if not isinstance(directive3, list):
                        directive2 = [directive3]
                    else:
                        directive2 = directive3

                    for directive in directive2:
                        newfilter.set_filter(directive)

                res[extension] = newfilter

            return res
            # pdb.set_trace()

        else:
            return last_

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if 1 or rpdb() or cpdb():
            pdb.set_trace()
        raise


class JsonFilterManager(FilterManager):
    """Filter Manager for JSON/dict content"""

    def prep(self, tmp, data):
        try:
            if isinstance(data, dict):
                return data
            elif isinstance(data, str):
                return json.loads(data)
            else:
                raise NotImplementedError(
                    "%s.prep:unsupported data type:%s" % (self, type(data))
                )

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def to_text(self, tmp, data):
        try:
            return json.dumps(data, sort_keys=True, indent=4)
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise
