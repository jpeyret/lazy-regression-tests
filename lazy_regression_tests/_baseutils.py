import sys
import types

import logging

from string import Template

from functools import partial, wraps

logger = logging.getLogger(__name__)

undefined = Ellipsis

from typing import List, Any, Tuple, Iterable

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


import pdb


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


def set_rpdb(rpdb, remove=True, recurse=True):
    if "--rpdb" in sys.argv:
        rpdb.enabled = True
        # howto- set cpdb on modules...
        if recurse:
            for module in sys.modules.values():
                try:
                    # this checks if it's likely to be cpdb, not something w same name
                    _ = module.rpdb.enabled
                    module.rpdb = rpdb
                except AttributeError:  # pragma: no cover
                    pass

        if remove:
            sys.argv.remove("--rpdb")
        return rpdb.enabled
    return False


def set_cpdb(cpdb, remove=True, recurse=True, boolvalue=None):

    # !!!TODO!!!p4 - stop handling --pdb and consider it reserved

    single_use_flag = "--cpdb"

    flags = set(["--cpdbmany", "--cpdbonce", single_use_flag])
    args = set(sys.argv)

    # print("sys.argv#20", id(sys.argv), sys.argv, id(sys.argv))

    single_use_flag = "once" if single_use_flag in sys.argv else False

    found = single_use_flag or (args & flags)

    if boolvalue is None:
        boolvalue = getattr(cpdb, "enabled", False) or found

    if boolvalue:
        cpdb.enabled = boolvalue
        if recurse:
            for module in sys.modules.values():
                try:
                    # this checks if it's likely to be cpdb, not something w same name
                    _ = module.cpdb.enabled
                    module.cpdb = cpdb
                except AttributeError:  # pragma: no cover
                    pass
    # import pdb
    # pdb.set_trace()
    if remove:
        # pdb.set_trace()
        for flag in flags:
            try:
                sys.argv.remove(flag)
            except (ValueError,) as e:
                pass
                # print("couldnt remove:%s:" % (flag) )
                # print("sys.argv#250", id(sys.argv), sys.argv)
    # print("sys.argv#29", id(sys.argv), sys.argv, id(sys.argv))


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
    truncate=60,
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
    truncate=60,
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
        msg = sep * linefeed + "%s%s %s\n" % (" " * indentlevel, header, repr(contents))
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


def nested_dict_get(dict_: dict, lookup: str, default=undefined):
    try:

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

    except (Exception,) as e:  # pragma: no cover
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

    except (Exception,) as e:  # pragma: no cover
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
