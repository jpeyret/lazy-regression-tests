import re
import os
import difflib
from collections import deque, namedtuple
from functools import partial


import pdb

from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
    fill_template,
    Subber,
    RescueDict,
)

from traceback import print_exc as xp

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


###################################################################
# Python 2 to 3.  !!!TODO!!!p4- Simplify after Python support ends.
###################################################################
try:
    basestring_ = basestring
except (NameError,) as e:
    basestring_ = str

try:
    unicode_ = unicode
except (NameError,) as e:
    unicode_ = str


def cpdb(**kwds):  # pragma : no cover
    if cpdb.enabled == "once":
        cpdb.enabled = False  # type: ignore
        return True
    return cpdb.enabled


cpdb.enabled = False  # type: ignore


def rpdb():  # pragma : no cover
    return rpdb.enabled


rpdb.enabled = False  # type: ignore
Found = namedtuple("Found", "found by")


def found_repr(self):
    return "found:%-30.30s: by:%s:" % (self[0], self[1])


Found.__repr__ = found_repr


class DiffFormatter(object):
    """inherit from object to make it a new-style class, else super will complain"""

    def __init__(self, *args, **kwds):

        self.window = kwds.pop("window", None)
        self.maxlines = kwds.pop("maxlines", None)

        self._differ = difflib.Differ()

        # super(DiffFormatter, self).__init__(self, *args, **kwds)

    def _window(self, lines, window=None):
        try:

            if not window:
                return lines
            if not isinstance(window, int):
                raise TypeError("window has to be an int")

            # remember, at most, window # of lines
            dq = deque(maxlen=window)
            cntr = 0

            res = []

            for line in lines:

                if line[0] in ("+", "-"):
                    # cntr, while > 0 adds line to res
                    cntr = window
                    while True:
                        try:
                            # try if res.extend(dq) works
                            res.append(dq.popleft())
                        except (IndexError,) as e:
                            break
                    res.append(line)
                elif cntr > 0:
                    cntr -= 1
                    res.append(line)
                else:
                    # this line won't be used, unless a later line
                    # requires it in context.
                    dq.append(line)
            return res
        except (Exception,) as e:  # pragma : no cover
            raise

    def format(self, exp, got, window=None):
        try:
            exp_ = exp.splitlines()
            got_ = got.splitlines()
            lines = self._differ.compare(exp_, got_)

            window = window or self.window

            if window:
                lines2 = self._window(lines, window)
            else:
                lines2 = list(lines)

            if self.maxlines:
                # this doesn't work well 0 1 2 3 ... vs 100 101 102 103 ...
                # will show all the - in the maxlines since there is nothing in common...
                lines2 = lines2[: self.maxlines]

            msg = "\n".join(lines2)
            msg = msg.strip()
            if msg and msg[1] != " ":
                msg = "  %s" % (msg)
            return msg

        except (Exception,) as e:  # pragma : no cover
            raise


def replace(list_, item=None, with_=[]):
    """utility function:
       given an item, if it's found in the list_, replace it there,
       except that lists are expanded at that position
    """

    try:
        try:
            pos = list_.index(item)
        except (ValueError,) as e:
            return list_[:]

        if isinstance(with_, list):
            li = list_[0:pos] + with_ + list_[pos + 1 :]
            return li

        res = list_[:]
        res[pos] = with_
        return res

    except (Exception,) as e:  # pragma : no cover
        if cpdb():
            pdb.set_trace()
        raise


class MediatedEnvironDict(dict):
    def __init__(self, filters=[], seed={}, *args, **kwds):
        """
        :param filters: filter.search(envname) will  
        :param seed   : default values which block env variables
        :param **kwds : passed on to std `dict` constructor
        """

        super(MediatedEnvironDict, self).__init__(*args, **kwds)
        self.set_filters(filters)
        self.acquired = False
        self.seed = seed
        self.update(**self.seed)

    def set_filters(self, filters):
        li = self.filters = []
        for filter_ in filters:
            if isinstance(filter_, basestring_):
                li.append(re.compile(filter_))
            else:
                li.append(filter_)

    def acquire(self):
        """
        read environment variables matching the filters
        note `seed` keys will not get updated"""

        try:

            for k, v in os.environ.items():
                for filter_ in self.filters:
                    if filter_.search(k):
                        # dont override what's already set
                        if not k in self:
                            self[k] = v
                            continue

            self.acquired = True
            # pdb.set_trace()

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def clear(self):
        """flushes the dict and reapplies the seed"""
        self.acquired = False
        super(MediatedEnvironDict, self).clear()
        self.update(**self.seed)


class Finder(object):

    target = "?"

    def __repr__(self):
        return self.target

    def is_match(self, notify, *names):
        try:

            if len(names) > 1:
                raise NotImplementedError()

            if names[0] == self.target:
                notify(Found(names, self))
        except (Exception,) as e:  # pragma : no cover
            ppp(self, "%s.is_match" % (self))
            logger.info("names:%s" % names)
            if cpdb():
                pdb.set_trace()
            raise

    def __init__(self, target):
        self.target = target
        self._init()

    def _init(self):
        pass


class NamesMatchTemp(object):
    def __init__(self):
        self.finds = []
        self.work = []

    def __repr__(self):
        return """
  hits:%s
  work:%s\n""" % (
            self.finds,
            self.work,
        )


class WorkerNamesMatch(object):
    def __init__(self):
        self.done = {}

    def process(self, target, matchtemp):
        self.done = {}
        self._process(target, matchtemp)

    def _process(self, target, matchtemp):
        raise NotImplementedError("%s.process" % (self))


class RemoveWorkerNamesMatch(WorkerNamesMatch):
    def _process(self, target, matchtemp):
        try:
            di = self.done
            for found in matchtemp.finds:

                if len(found.found) > 1:
                    raise NotImplementedError("%s._process" % (self))

                key = found.found[0]
                di[key] = target.pop(key)

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise


class _Filter(object):
    """hacky because this is different for dictionary than text filtering"""

    def __init__(self, matchers_=[], notify=None, callback=None):

        self.matchers = []
        for matcher in matchers_:
            if isinstance(matcher, Finder):
                self.matchers.append(matcher)
            else:
                self.matchers.append(Finder(matcher))
        self.notify = notify or self._notify
        self.callback = callback

    # def scan(self, target, temp=None):
    def scan(self, target):
        # self.temp = temp or getattr(self, "temp", None) or NamesMatchTemp()
        self.temp = NamesMatchTemp()

        for key, value in target.items():
            #!!!TODO!!! - recurse into nested dicts.

            for matcher in self.matchers:
                if matcher.is_match(self.notify, key):
                    continue

            # recursion error....
            # if isinstance(value, dict):
            #     self.scan(target, self.temp)

        if self.callback:
            self.callback(target, self.temp)
        return self.temp

    def _notify(self, found):
        self.temp.finds.append(found)


NamesMatcher = _Filter


class DictionaryKeyFilter(_Filter):
    def __init__(self, *args, **kwds):
        super(DictionaryKeyFilter, self).__init__(*args, **kwds)
        self.worker = RemoveWorkerNamesMatch()
        self.callback = self.worker.process


class DataMatcher(object):
    def __repr__(self):
        return "%s.%s" % (self.__module__, self.__class__.__name__)

    hitname = None

    raw_format_filter = False

    def __init__(self, *args, **kwds):
        self.verbose = kwds.get("verbose")
        self.hitname = kwds.get("hitname")


class RegexMatcher(DataMatcher):
    def __init__(self, pattern, *args, **kwds):
        self.patre = re.compile(pattern, *args)
        super(RegexMatcher, self).__init__(*args, **kwds)

    def search(self, *args, **kwds):
        return self.patre.search(*args, **kwds)

    def __getattr__(self, attrname):
        return getattr(self.patre, attrname)


class RegexRemoveSaver(RegexMatcher):
    """this will remove the matching line but also save it"""

    def __init__(self, pattern, *args, **kwds):
        assert kwds.get("hitname"), "RegexRemoveSaver needs a hitname"
        super(RegexRemoveSaver, self).__init__(pattern, *args, **kwds)


class RegexSubstitHardcoded(RegexMatcher):
    """allows for replacement of the line with different contents

       can't use a re.sub directly because the Filter won't know if 
       it's just a match filter or a match & substitution
    """

    def __repr__(self):

        subinfo = None

        try:

            if callable(self.substitution):
                if isinstance(self.substitution, partial):
                    subinfo = "partial:%s" % self.substitution.func.__name__
                else:
                    subinfo = "func.%s" % self.substitution.__name__
            else:
                subinfo = str(self.substitution)
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

        return "%s.(pattern=%s, substitution=%s" % (
            self.__class__.__name__,
            self.pattern,
            subinfo,
        )

    def __init__(self, pattern, substitution, *args):

        self.patre = re.compile(pattern, *args)
        self.substitution = substitution

    def __getattr__(self, attrname):
        return getattr(self.patre, attrname)

    def substitute(self, line):
        return self.substitution


class RegexSubstitFilter(RegexSubstitHardcoded):
    def __init__(self, pattern, substitution, *args, **kwds):

        self.verbose = kwds.get("verbose")

        if not callable(substitution):
            raise TypeError(
                "substitution needs to be a callable f(re.MatchObject)=>str"
            )

        super(RegexSubstitFilter, self).__init__(pattern, substitution, *args)

    def substitute(self, line):
        try:
            res = self.patre.sub(self.substitution, line)
            # if rpdb(): # pragma : no cover
            #     pdb.set_trace()
            if self.verbose:
                logger.info("\n  %s\n  :%s:\n  =>\n  :%s:" % (self, line, res))
            return res

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise


class KeepTextFilter(object):

    KEEP = True

    dflt_cls = RegexMatcher

    def __init__(self, regexes=[], f_notify=None):

        """:param regexes: list of regex's.  or strings which will be compiled to regex
           you could also pass your own matching objects, they need `search(string)=>boolean`
           method
        """

        try:
            self.formatters = []

            regexes_ = regexes[:]

            regexes_ = []
            for regex in regexes:
                if getattr(regex, "raw_format_filter", False):
                    self.formatters.append(regex)
                    continue

                if not isinstance(regex, DataMatcher):
                    regex = self.dflt_cls(re.compile(regex))
                regexes_.append(regex)

            self.regexes = regexes_
            self.f_notify = f_notify

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def copy(self):
        """return a duplicate, but with a copy of the regexes..."""

        newinst = self.__class__(regexes=[], f_notify=self.f_notify)
        newinst.regexes = self.regexes[:]
        return newinst

    def add_regex(self, regex):
        if not isinstance(regex, self.dflt_cls):
            regex = self.dflt_cls(re.compile(regex))
        self.regexes.append(regex)

    def _is_match(self, line):
        try:
            res = False
            for regex in self.regexes:
                if regex.search(line):
                    if self.f_notify:
                        self.f_notify(Found(line, regex))

                    # these are special classes such as
                    # utils.RegexSubstitHardcoded
                    # utils.RegexSubstitFilter
                    substitute = getattr(regex, "substitute", None)
                    if substitute:
                        line = substitute(line)
                        # but if we're called from RemoveTextFilter
                        # then keep the line
                        return self.KEEP, line

                    return True, line
            return False, line
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def filter(self, formatted_data):

        if not isinstance(formatted_data, list):
            formatted_data = formatted_data.splitlines()

        lines = []
        for line in formatted_data:
            keep, line = self._is_match(line)
            if keep:
                lines.append(line)
        return "\n".join(lines)

    __call__ = filter

    def format(self, data, lazytemp, **kwargs):

        if not self.formatters:
            return data

        try:
            for formatter in self.formatters:
                data = formatter.format(data, lazytemp=lazytemp, **kwargs)

            return data

            # raise NotImplementedError("format(%s)" % (locals()))
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise


class RemoveTextFilter(KeepTextFilter):

    KEEP = False

    def filter(self, formatted_data):
        lines = []
        for line in formatted_data.splitlines():
            keep, line = self._is_match(line)
            if not keep:
                lines.append(line)
        return "\n".join(lines)

    __call__ = filter

    # def format(self, data, **kwargs):

    #     if not self.formatters:
    #         return data

    #     try:
    #         raise NotImplementedError("format(%s)" % (locals()))
    #     except (Exception,) as e: # pragma : no cover
    #         if cpdb(): pdb.set_trace()
    #         raise


def curry_func(func, replacement, verbose=False, **kwds):
    """preps the function for replacement"""
    return partial(func, replacement=replacement, verbose=verbose, **kwds)


def simple_subber(match, *args, **kwds):

    """
        meant to be called as per re.sub(pattern, callable)
        :param match:  is a re.MatchObject
        :param replacement: keyword parameter - required - string to replace with
               use `operator.partial` or `curry_func` 

               ex: `partial(simple_subber, replacement="myreplacement"))`

        :param onlyonce: keyword parameter - used to avoid replacing on a reformat when 
        the replacement is found in the match string.
        :return: a string as per result of re.sub(pattern, callable)
    """

    try:
        try:
            replacement = kwds["replacement"]
        except (KeyError,) as e:
            raise TypeError(
                "missing replacement keyword parameter.  refer to docstring"
            )
            raise

        rpdb = kwds.get("rpdb")

        verbose = kwds.get("verbose")

        # avoid re doing multiple replaces...
        onlyonce = kwds.get("onlyonce")
        if onlyonce and replacement in match.string:
            return match.string[match.start() : match.end()]

        assert isinstance(replacement, basestring_)
        if rpdb or verbose:
            # ppp(match)

            di = {
                "match.re.pattern": match.re.pattern,
                "match.groups": match.groups(),
                "match.string": match.string,
            }
            ppp(di)

        try:
            res = match.string[match.start() : match.end()].replace(
                match.groups(0)[0], replacement
            )
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            return "!lazy_regression_tests:bad substitution:!"

        if verbose:
            print("\nsubstit02:\n  %s \n  =>\n  %s" % (match.string, res))
        if rpdb:
            pdb.set_trace()

        # raise NotImplementedError()
        return res

    except (Exception,) as e:  # pragma : no cover
        if cpdb():
            pdb.set_trace()
        raise
