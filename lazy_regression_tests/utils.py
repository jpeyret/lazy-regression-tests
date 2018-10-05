
import re
import os
import difflib
from collections import deque, namedtuple

import pdb
from lib.utils import set_cpdb, set_rpdb, ppp, debugObject
from traceback import print_exc as xp

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


###################################################################
# Python 2 to 3.  !!!TODO!!!p4- Simplify after Python support ends.
###################################################################
try:
    _ = basestring
except (NameError,) as e:
    basestring = str
###################################################################




def cpdb():
    return cpdb.enabled
cpdb.enabled = False

def rpdb():
    return rpdb.enabled
rpdb.enabled = False

Found = namedtuple('Found', 'found by')

def found_repr(self):
    return "found:%-30.30s: by:%s:" % (self[0],self[1])

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

            #remember, at most, window # of lines
            dq = deque(maxlen=window)
            cntr = 0

            res = []


            for line in lines:

                if line[0] in ("+","-"):
                    #cntr, while > 0 adds line to res
                    cntr = window
                    while True:
                        try:
                            #try if res.extend(dq) works
                            res.append(dq.popleft())
                        except (IndexError,) as e:
                            break
                    res.append(line)
                elif cntr > 0:
                    cntr -= 1
                    res.append(line)
                else:
                    #this line won't be used, unless a later line
                    #requires it in context.
                    dq.append(line)
            return res
        except (Exception,) as e:
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
                #this doesn't work well 0 1 2 3 ... vs 100 101 102 103 ... 
                #will show all the - in the maxlines since there is nothing in common...
                lines2 = lines2[:self.maxlines]

            msg = "\n".join(lines2)
            msg = msg.strip()
            if msg and msg[1] != " ":
                msg = "  %s" % (msg) 
            return msg 

        except (Exception,) as e:
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
            li = list_[0:pos] + with_ + list_[pos+1:]
            return li

        res = list_[:]
        res[pos] = with_
        return res

    except (Exception,) as e:
        if cpdb(): pdb.set_trace()
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
            if isinstance(filter_, basestring):
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
                        #dont override what's already set
                        if not k in self:
                            self[k] = v
                            continue

            self.acquired = True
            # pdb.set_trace()

        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
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
        except (Exception,) as e:
            ppp(self, "%s.is_match" % (self))
            logger.info( "names:%s" %  names)
            if cpdb(): pdb.set_trace()
            raise


    def __init__(self, target):
        self.target = target
        self._init()

    def _init(self):
        pass

class RegexFinder(Finder):

    def _init(self):
        self.patre = re.compile(target)

    def is_match(self, notify, *names):
        raise NotImplementedError()


class NamesMatchTemp(object):
    def __init__(self):
        self.finds = []
        self.work = []

    def __repr__(self):
        return """
  hits:%s
  work:%s\n""" % (self.finds, self.work)

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


        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise


class _Filter(object):

    def __init__(self, matchers_=[], notify=None, callback=None):

        self.matchers = []
        for matcher in matchers_:
            if isinstance(matcher, Finder):
                self.matchers.append(matcher)
            else:
                self.matchers.append(Finder(matcher))
        self.notify = notify or self._notify
        self.callback = callback

    def scan(self, target):
        self.temp = NamesMatchTemp()

        for key in target.keys():
            for matcher in self.matchers:
                if matcher.is_match(self.notify, key):
                    continue

        self.callback and self.callback(target, self.temp)
        return self.temp

    def _notify(self, found):
        self.temp.finds.append(found)

NamesMatcher = _Filter

class DictionaryKeyFilter(_Filter):

    def __init__(self, *args, **kwds):
        super(DictionaryKeyFilter, self).__init__(*args, **kwds)
        self.worker = RemoveWorkerNamesMatch()
        self.callback = self.worker.process

