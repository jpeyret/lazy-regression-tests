""" base utilities package, shared among libraries

    do not expect much coverage of it in any library because
    most libraries won't use much of its functionality.

"""

import sys
import types
import re

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

#######################################################


import logging
import pdb

from string import Template

from functools import partial, wraps

logger = logging.getLogger(__name__)

undefined = NotImplemented

from typing import List, Any, Tuple, Iterable

# for isinstance tests...
type_regex_hack = re.compile("").__class__

verbose = "-v" in sys.argv

try:
    from cStringIO import StringIO  # 223ed
except (ImportError,) as e:
    from io import StringIO  # 223ed

import json
import copy

try:
    basestring_ = basestring  # type: ignore
except (NameError,) as e:
    basestring_ = str


#################################
# Python 3 bytes=>str support
#################################


def cast_bytes2str(fn):
    """decorator to cast the result of a function to a str if and only if it's bytes"""

    def decorated(*args, **kwds):

        res = fn(*args, **kwds)
        if isinstance(res, bytes):
            return res.decode("utf-8")
        return res

    return decorated


#################################


def _pseudo_decor(fn, attrname):
    """decorator to cast the an attribute with a function result to a str if and only if it's bytes

       can't be used directly, see `cast_contentbytes2str`
    """

    # https://stackoverflow.com/a/25827070

    # magic sauce to lift the name and doc of the function
    @wraps(fn)
    def ret_fun(*args, **kwargs):
        # do stuff here, for eg.

        # print ("decorator arg is %s" % str(attrname))
        res = fn(*args, **kwargs)
        value = getattr(res, attrname)
        if isinstance(value, bytes):
            # howto- bytes=>str
            value = value.decode("utf-8")
            setattr(res, attrname, value)
        return res

    return ret_fun


cast_contentbytes2str = partial(_pseudo_decor, attrname="content")


def cpdb(*args, **kwargs):
    "disabled"


def rpdb(*args, **kwargs):
    "disabled"


def real_rpdb() -> bool:  # pragma: no cover

    count = getattr(rpdb, "count", None)
    if count is not None:
        rpdb.count -= 1
        return rpdb.count > 0

    try:
        from django.core.cache import cache
    except (ImportError,):
        cache = {}
    import sys

    in_celery = sys.argv[0].endswith("celery") and "worker" in sys.argv
    if in_celery:
        return False
    res = bool(cache.get("rpdb_enabled"))

    if res and count is None:
        rpdb.count = 3

    return res


def set_rpdb(rpdb_in=None, remove=True, recurse=True):

    rpdb_in = rpdb_in or rpdb

    if "--rpdb" in sys.argv:
        real_rpdb.count = 3

        try:
            from django.core.cache import cache
        except (Exception,) as e:
            cache.set("rpdb_enabled", 1, 300)

    if recurse:
        for module in list(sys.modules.values()):
            try:
                # this checks if it's likely to be cpdb, not something w same name
                # _ = module.rpdb.enabled
                module.rpdb = real_rpdb
            except AttributeError:  # pragma: no cover
                pass

    if remove:
        try:
            sys.argv.remove("--rpdb")
        except (ValueError,) as e:
            pass

    return real_rpdb


#######################################################
# cpdb v2
#######################################################


def real_cpdb(**kwds):  # pragma: no cover
    real_cpdb.count -= 1
    return real_cpdb.count > 0


real_cpdb.count = 3


def cpdb():
    "disabled"


def set_cpdb(cpdb_in=None, remove=True, recurse=True, boolvalue=None):

    single_use_flag = "--cpdb"

    in_celery = sys.argv[0].endswith("celery") and "worker" in sys.argv
    if in_celery:
        return fake_cpdb

    if cpdb_in is None:
        cpdb_in = cpdb

    flags = set(["--cpdbmany", "--cpdbonce", single_use_flag])
    args = set(sys.argv)

    # print("sys.argv#20", id(sys.argv), sys.argv, id(sys.argv))

    single_use_flag = "once" if single_use_flag in sys.argv else False

    found = single_use_flag or (args & flags)

    if remove:
        for flag in flags:
            try:
                sys.argv.remove(flag)
            except (ValueError,) as e:
                pass

    if boolvalue is None:
        boolvalue = (
            bool(found)
            or getattr(cpdb_in, "enabled", False)
            or getattr(cpdb_in, "count", 0)
        )

    if boolvalue:
        # it was set before or its being set for the first time.

        if recurse:
            # set cpdbs on modules that have a stub for it
            for module in list(sys.modules.values()):
                try:
                    # pdb.set_trace()
                    # print(module)
                    # this checks if it's likely to be cpdb, not something w same name
                    existing = getattr(module, "cpdb", None)
                    if existing:
                        if existing.__doc__ == "disabled":
                            if verbose:
                                logger.info("matching cpdb")
                        else:
                            # pdb.set_trace()
                            if verbose:
                                logger.info("old style cpdb on %s" % (module))

                        module.cpdb = real_cpdb
                except AttributeError:  # pragma: no cover
                    pass

        return real_cpdb
    return cpdb_in


#######################################################


def ppp(o, header=None):
    if header is None:
        if isinstance(o, dict):
            header = "[%s %s...]" % (type(o), repr(o)[0:10])
        else:
            header = "[%s %s]" % (type(o), repr(o))

    # header = header or

    msg = debugObject(o, header)
    print(msg)


def stripdict(di, *args):
    di = di.copy()
    for name in ["self"] + list(args):
        _ = di.pop(name, None)
    return di


def debugObject(
    obj,
    header="",
    skip__=True,
    li_skipfield=[],
    indentlevel=0,
    sep="\n",
    li_skiptype=[types.MethodType],
    linefeed=1,
    truncate=120,
):

    if isinstance(obj, dict):
        di = obj
        return debugDict(
            di, header, li_skipfield, sep, indentlevel=indentlevel, linefeed=linefeed
        )
    elif isinstance(obj, list):
        return (
            header
            + "\n"
            + "\n".join(
                [
                    debugObject(
                        o, li_skipfield, sep, indentlevel=indentlevel, linefeed=linefeed
                    )
                    for o in obj[0:5]
                ]
            )
        )

    elif isinstance(obj, basestring_):
        return "\n%s:%s" % (header, obj)

    else:

        if not header and isinstance(obj, object):
            header = "%s@%s" % (obj.__class__.__name__, obj.__module__)

        di = {}

        cls_ = getattr(obj, "__class__", None)

        for attrname in dir(obj):

            # properties can make a huge mess of things...
            attr = getattr(cls_, attrname, None)
            if attr and isinstance(attr, property):
                di[attrname] = "[property]"
                continue

            if skip__ and attrname.startswith("__") and attrname.endswith("__"):
                continue
            try:
                attrval = di[attrname] = getattr(obj, attrname, "???")
            except Exception as e:  # pragma: no cover
                attrval = "exception:%s" % (e)

            if type(attrval) in li_skiptype:
                li_skipfield.append(attrname)

        if not di:
            return "%s = %s" % (header, str(obj)[:500])

        return debugDict(
            di,
            header,
            li_skipfield,
            sep,
            indentlevel=indentlevel,
            linefeed=linefeed,
            truncate=truncate,
        )


# from repr import repr


def debugDict(
    dict,
    header="",
    li_skipfield=[],
    skip__=False,
    indentlevel=0,
    sep="\n",
    linefeed=1,
    truncate=120,
):

    buf = StringIO()

    try:
        li = list(dict.items())
    except AttributeError:  # pragma: no cover
        return str(type(dict))

    try:
        li.sort()
    except (TypeError,) as e:
        logger.debug("debugDict:li.sort() error on %s" % (li))
        pass

    contents = " ={}" * (not li)  # huh?

    if truncate:
        msg = sep * linefeed + "%s%s %s\n" % (
            " " * indentlevel,
            header,
            repr(contents)[0:truncate],
        )
    else:
        msg = sep * linefeed + "%s%s %s\n" % (" " * indentlevel, header, str(contents))

    buf.write(msg)

    for k, v in li:
        sk = str(k)

        if skip__ and sk.startswith("__") and sk.endswith("__"):
            continue

        # make sure we dont leak secrets...
        if "secret" in sk.lower():
            continue

        if sk in li_skipfield:
            continue

        try:
            if truncate:
                buf.write("%s=%s%s" % (k, repr(v)[0:truncate], sep))
            else:
                buf.write("%s=%s%s" % (k, str(v), sep))

        except UnicodeEncodeError:
            pass
        except AttributeError:  # pragma: no cover
            buf.write("%s=%s%s" % (k, "?", sep))
        except Exception:
            pass

    return buf.getvalue()


def fill_template(tmpl: str, *args: Any) -> str:
    return tmpl % Subber(*args)


def sub_template(tmpl: str, *args: Any) -> str:
    tmp = Template(tmpl)
    return tmp.substitute(Subber(*args))  # type: ignore


def first(li, empty_value=None):
    if not li:
        return empty_value

    if isinstance(li, list):
        return li[0]

    if isinstance(li, dict):
        return li.values()[0]

    raise NotImplementedError("first.  unknown type for %s[%s]" % (li, type(li)))


class Subber(object):
    """ implement a first found getter for lookup keys
        each obj in li_arg is asked, via getattr & get, whether
        it holds a key.  if found it is returned immediately
        Else 
    """

    def __init__(self, *args: Any):
        self.li_arg = list(args)
        # raise NotImplementedError, "li_arg:%s" % (self.li_arg)
        self.di_res = {}
        self.verbose = False

    def removed(self, *remove_args: Any) -> "Subber":
        """return a new Subber without some args
           a common use would be not have `self` as a subber on property
           lookups
        """
        args2 = [arg for arg in self.li_arg if not arg in remove_args]
        return Subber(*args2)

    def append(self, obj: Any):
        self.li_arg.append(obj)

    def insert(self, pos, obj: Any):
        self.li_arg.insert(pos, obj)

    def __repr__(self):
        def fmt(arg, maxlen=20):
            msg = "%s" % (arg)
            if len(msg) > maxlen:
                return msg[:maxlen] + "..."
            else:
                return msg

        return "Subber([" + ",".join([fmt(arg) for arg in self.li_arg]) + "])"

        # return str(self.li_arg)

    @classmethod
    def factory(cls, obj, *args):

        li_sub = []

        for arg in args:
            if isinstance(arg, basestring_):
                li = arg.split(",")
                for arg2 in li:
                    arg2 = arg2.strip()
                    if arg2 == "self":
                        li_sub.append(obj)
                        continue
                    elif not "." in arg2:
                        sub = getattr(obj, arg2)
                        li_sub.append(sub)
                        continue
                    else:
                        raise NotImplementedError("!!!todo!!! rgetattr")
            else:
                li_sub.append(arg)
        return cls(*li_sub)

    def _get_from_args(self, key):
        """generic way to look for a key in the arg list"""

        for arg in self.li_arg:

            try:
                got = arg[key]
                if self.verbose:
                    print("got:%s from %s.return" % (key, arg))
                return got
            except (KeyError):
                try:
                    # try getattr
                    got = getattr(arg, key)
                    if self.verbose:
                        print("got:%s from %s.return" % (key, arg))
                    return got
                except AttributeError:  # pragma: no cover
                    if self.verbose:
                        print("no luck:%s from %s.continue" % (key, arg))

                    continue

            except (AttributeError, TypeError):
                # no __getitem__, try getattr
                try:
                    got = getattr(arg, key)
                    if self.verbose:
                        print("got:%s from %s.return" % (key, arg))
                    return got
                except AttributeError:  # pragma: no cover
                    if self.verbose:
                        print("no luck:%s from %s.continue" % (key, arg))
                    continue

        try:
            if self.verbose:
                print("no luck:%s .  KeyError using subber: %s" % (key, self))
            raise KeyError(key)
        except Exception as e:  # pragma: no cover
            raise

    def get(self, key, default=None):
        try:
            res = self._get_from_args(key)
            return res
        except KeyError:  # pragma: nocover
            return default

    def __getitem__(self, keyname):

        """
        implement dictionary, attribute, func/method call lookup - a la Django Templates, but across
        a number of passed in arguments.

        if it's func/method call, then func(keyname, li_arg) is called (which includes the callable itself.

        """
        res = self._get_from_args(keyname)
        self.di_res[keyname] = res
        return res


class RescueDict(object):
    """fall through in case a fill_template does not find a key
       use sparingly as it covers up exceptions
    """

    # ???TODO??? - consider adding a **kwds to default capability
    # that would NOT count as a Rescue.
    # i.e. `RescueDict(notes="")` would return "" for Notes if nothing else in the Subber
    # had `notes` set.

    def __init__(self, placeholder="?", template="%(key)s=%(placeholder)s"):
        self.placeholder = placeholder
        self.li_used = []
        self.s_asked = set()
        self.template = template
        self.hit = False

    def reset_hit(self):
        self.hit = False

    def __getitem__(self, key):

        self.li_used.append(key)
        self.s_asked.add(key)
        self.hit = True
        if not self.template:
            return self.placeholder

        return self.template % dict(key=key, placeholder=self.placeholder)


class RescueDictValue(object):
    def __init__(self, value):
        self.value = value

    def __getitem__(self, key):
        return self.value


def nested_dict_get(dict_: dict, lookup: Optional[str], default=undefined):
    try:

        # top-level
        if lookup is None:
            return dict_

        lookups = lookup.split(".")

        li_approach = lookups[:-1]
        final = lookups[-1]

        di = dict_
        for key in li_approach:
            try:
                di = di[key]
            except (KeyError,) as e:  # pragma: no cover
                raise

        if default is not undefined:
            res = di.get(final, default)
        else:
            return di[final]

        return res

    except (
        Exception,
    ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
        if cpdb():
            pdb.set_trace()
        raise


def nested_dict_pop(dict_: dict, lookup: str, value=undefined):
    try:

        lookups = lookup.split(".")

        li_approach = lookups[:-1]
        final = lookups[-1]

        di = dict_
        for key in li_approach:
            di = di.get(key)
            if di is None:
                if value is undefined:
                    raise KeyError(key)
                else:
                    return value

        if value is not undefined:
            res = di.pop(final, value)
            return res
        else:
            # will do a KeyError
            return di.pop(final)

    except (
        Exception,
    ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
        if cpdb():
            pdb.set_trace()
        raise


class Dummy(object):
    """because you can't set attributes on type object"""

    def __repr__(self):
        return "class.%s" % (self.__class__.__name__)

    __str__ = __repr__

    def setdefault(self, attrname, value):
        try:
            return getattr(self, attrname)
        except (AttributeError,) as e:  # pragma: nocover
            setattr(self, attrname, value)
            return value

    def debug(self):
        ppp(self.__dict__)

    def to_json(self):
        return self.__dict__

    def deepcopy(self):
        return copy.deepcopy(self)

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def update(self, **kwargs):
        self.__dict__.update(kwargs)
        return self

    def json_dumps(self):
        di = self.__dict__.copy()
        for k, v in di.items():
            if isinstance(v, datetime):
                di[k] = str(v)

        return json.dumps(di)

    def get(self, key, value=None):
        return self.__dict__.get(key, value)

    def __setitem__(self, attrname, value):
        setattr(self, attrname, value)

    def __getitem__(self, attrname):
        try:
            return getattr(self, attrname)
        except AttributeError as attrname:
            raise KeyError(attrname)


def getpath(src, path):
    """get nested path x.y.z against dictorary or object"""
    try:

        current = src
        accessors = path.split(".")
        for accessor in accessors:
            if isinstance(current, dict):
                try:
                    current = current[accessor]
                # pragma: no cover pylint: disable=unused-variable
                except (KeyError,) as e:
                    raise AttributeError(accessor)
            else:
                current = getattr(current, accessor)

        return current

    # pragma: no cover pylint: disable=unused-variable
    except (AttributeError,) as e:
        raise

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise


class DictFormatter:
    """ takes an input dictionary, looks for matching items from keys in 
    the second formatting dictonary and modifies the input dictionary when
    there is a match

    the formatting dictionary can be keyed by:

    - any acceptable dictionary key, in which case it's a straight key lookup
    - a regex string, which is then matched against the input dictionary's keys

    what happens when there is a match depends on the di_formatter value:

    - if it's None, the func_default function is called, which defaults to deleting the key
    - if it's a dict, there is a recursive call with the matched value of the input
    - if it's a function, the function gets called with the dict, key and value as a parameter
      and has to return a dict

    """

    def __repr__(self):
        return "%s" % (self.__class__.__name__)

    def del_dict_item(self, di: dict, key: Any, value: Any):
        """ delete the given key if it exists """
        di.pop(key, None)
        return di

    default_processor = del_dict_item

    def __init__(self, di_default_formatter=None):
        self.di_default_formatter = di_default_formatter

    def process(
        self,
        di_in,
        di_formatter=None,
        in_place=False,
        f_default=None,
        li_path=[],
        keep: dict = None,
    ):

        try:
            di = di_in if in_place else di_in.copy()

            di_formatter = di_formatter or self.di_default_formatter

            assert isinstance(
                di_formatter, dict
            ), "%s needs to be called with formatting dictionary or needs to have been initialized with one"

            f_default = f_default or self.default_processor

            li_tu_key_func = list(di_formatter.items())

            di_keys = None

            for key, func_fmt in li_tu_key_func:

                func_fmt = func_fmt or f_default

                if isinstance(key, type_regex_hack):
                    di_keys = di_keys or list(di.keys())
                    for di_key in di_keys:

                        if not isinstance(di_key, str):
                            continue

                        hit = key.search(di_key)
                        if hit:
                            v = di.get(di_key, undefined)
                            if callable(func_fmt):
                                if keep is not None:
                                    keep[di_key] = v

                                di = func_fmt(di, di_key, v)
                            elif isinstance(func_fmt, dict):
                                if keep is not None:

                                    childkeep = keep[di_key] = {}
                                else:
                                    childkeep = None
                                di = self.process(
                                    di,
                                    di_formatter=func_fmt,
                                    f_default=f_default,
                                    in_place=True,
                                    keep=childkeep,
                                )
                            else:
                                raise NotImplementedError(
                                    "%s.process(%s)" % (self, locals())
                                )
                    continue

                v = di.get(key, undefined)
                if v is undefined:
                    continue

                elif isinstance(v, dict):

                    # if rpdb(): # pragma: no cover
                    #     pdb.set_trace()

                    func_fmt = di_formatter[key]
                    if isinstance(func_fmt, dict):

                        if keep is not None:
                            childkeep = keep[key] = {}
                            # pdb.set_trace()
                        else:
                            childkeep = None

                        self.process(
                            v,
                            di_formatter=func_fmt,
                            f_default=f_default,
                            in_place=True,
                            keep=childkeep,
                        )
                    else:
                        if keep is not None:
                            keep[key] = v.copy()
                        if callable(func_fmt):
                            di[key] = func_fmt(di, key, v)
                        else:
                            del di[key]

                else:
                    # if the formatter is a dict, then only a value
                    # that is a dict should strip, by recursion
                    # this is not the case here
                    func_fmt = di_formatter[key]
                    if isinstance(func_fmt, dict):
                        continue

                    if keep is not None:
                        keep[key] = v

                    if callable(func_fmt):
                        di = func_fmt(di, key, v)
                    else:
                        del di[key]

            return di

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = process


class InvalidConfigurationException(ValueError):
    """ indicates that some configuration is missing or invalid """

    def __init__(self, msg, *args, **kwargs):

        new_message = f"""
⚙️⚙️⚙️⚙️⚙️⚙️⚙️

{msg}

⚙️⚙️⚙️⚙️⚙️⚙️⚙️
"""
        super(InvalidConfigurationException, self).__init__(
            new_message, *args, **kwargs
        )


class Breakpoints(object):

    enabled = False

    @classmethod
    def factory(cls, options=None, active=False, fnp_config=None):  # pragma: no cover
        fnp_config = fnp_config or getattr(options, OPTION_NAME, None)
        if fnp_config:
            try:
                return Breakpoints(fnp_config, active)
            except IOError:
                logger.warning("file %s not found" % (fnp_config))
                return DisabledBreakpoints()
        return DisabledBreakpoints()

    def __init__(self, fnp_config, active=False):  # pragma: no cover

        self.active = active
        self.enabled = active

        if isinstance(fnp_config, file_):
            self.fnp_config = fnp_config.name
            self.config = json.load(fnp_config)
        else:
            self.fnp_config = fnp_config
            with open(self.fnp_config) as fi:
                self.config = json.load(fi)

    def breakpoint(self, lookup, caller_variables):  # pragma: no cover

        self.enabled = False
        if not self.active:
            return

        try:
            breakpoints = self.config.get("breakpoints", {})
            # logger.debug("\n"+"*" * 80)
            # logger.debug("lookup:%s" % (lookup))
            # logger.debug("caller_variables:%s" % (caller_variables))
            # logger.debug("breakpoints:%s" % (breakpoints.keys()))
            # logger.debug("*" * 80 + "\n")
            # pdb.set_trace()

            conditions = breakpoints.get(lookup, [])

            if isinstance(conditions, dict):
                conditions = [conditions]

            for condition_ in conditions:
                # https://stackoverflow.com/questions/10832373/python-dictionary-match-key-values-in-two-dictionaries
                # for possible alternatives
                caller_status = dict(
                    [
                        (k, v)
                        for k, v in caller_variables.items()
                        if k in condition_.keys()
                    ]
                )

                if condition_ == caller_status:
                    logger.info(
                        "breakpoint activated @%s for %s" % (lookup, condition_)
                    )
                    res = self.enabled = True
                    return res

            return False

        except Exception as e:  # pragma: no cover
            logger.error(repr(e)[:100])
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = breakpoint


try:
    file_ = file
except NameError:
    from io import IOBase

    file_ = IOBase


def set_breakpoints3(recurse=True, fnp_config=None):

    if fnp_config is None:

        argv = sys.argv

        if not "-b" in argv:
            print("no breakpoints")
            return None

        pos_flag = argv.index("-b")

        fnp_config = argv.pop(pos_flag + 1)
        _ = argv.pop(pos_flag)

        print("fnp_config:%s" % (fnp_config))
        print("_:", _)
        print("sys.argv:%s" % (sys.argv))

    breakpoints = Breakpoints.factory(fnp_config=fnp_config, active=True)
    if breakpoints.active:
        if recurse:
            for module in sys.modules.values():
                try:
                    if not callable(module.breakpoints):
                        continue
                    module.breakpoints = breakpoints
                except AttributeError:  # pragma: no cover
                    pass
    return breakpoints


class UnavailableLibrary:
    """ throws error messages whenever something hasnt been installed 

    usage:
        try:
            from yaml import dump as ydump
        #use this to get a path to the client module
        except (ImportError,) as e: 
            class Foo:
                pass

            #anything calling on ydump will now blow up
            ydump = UnavailableLibrary(name = Foo.__module__, missing="yaml")    
    """

    exception_cls = InvalidConfigurationException

    def __init__(self, name: str, missing: str, message: str = ""):
        """
        :param missing: the name of the missing package, i.e. BeautifulSoup
        :param name: the name of the missing package
        """

        self.missing = missing
        self.name = name
        self.message = message

    def __repr__(self):
        """ error message """
        return f"""
Third party package/library '{self.missing}' has not been installed.  
You need to install it before using {self.name}
{self.message}
"""

    def __getattr__(self, *args, **kwargs):
        """ throw errors on any access """
        raise self.exception_cls(self)

    # and reroute call
    __call__ = __getattr__
