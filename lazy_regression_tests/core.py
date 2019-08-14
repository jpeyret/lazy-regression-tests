# -*- coding: utf-8 -*-
"""Mixin to support regression testing lazily:

       given a some received data (referred as `got`)
       does it match what was seen, and saved, the last time?

       Default naming: <module>.<classname>.<function>.<extension>

          but you can specify instance attributes to use in
          either the directory or file names

       A typical test write might save data as follows:

       For each `got` data passed to assertLazy, the mixin will

       1.  save the `got` to the `got` directory branch.
       2.  load the matching `exp` file 

          `exp` files that do not exist get created with `got` data.
          this will be used as `exp` the next time around.
    
          an error will be thrown, but setting onIOerror = "pass_missing" will 
          suppress that.
        
       3.  then `assertEqual` them.


/Users/jluc/kds2/wk/issues/nfb022.utils/issues/013.utmixin/temp/tmp
├── exp
│   ├── db1
│   │   └── test_uthelper_mixin.TestLive.test_rdbname_in_directory
│   ├── db2
│   │   └── test_uthelper_mixin.TestLive.test_rdbname_in_directory
│   ├── test_uthelper_mixin.TestLive.test_basic
│   ├── test_uthelper_mixin.TestLive.test_html.html
│   └── test_uthelper_mixin.TestLive.test_ignore
└── got
    ├── db1
    │   └── test_uthelper_mixin.TestLive.test_rdbname_in_directory
    ├── db2
    │   └── test_uthelper_mixin.TestLive.test_rdbname_in_directory
    ├── test_uthelper_mixin.TestLive.test_basic
    ├── test_uthelper_mixin.TestLive.test_html.html
    └── test_uthelper_mixin.TestLive.test_ignore
"""

#######################################################
# Typing
#######################################################

from typing import Any

###################################################################

import sys
import os
import unittest
import json
import codecs

import re
import shutil


###################################################################


try:
    from bs4 import BeautifulSoup as bs
except (ImportError,) as e:
    try:
        from BeautifulSoup import BeautifulSoup as bs
    except (Exception,) as e2:
        bs = None

import logging


from yaml import dump as ydump, safe_load as yload


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
from traceback import print_exc as xp

try:
    from lazy_regression_tests.utils import (
        DiffFormatter,
        replace,
        MediatedEnvironDict,
        Found,
        basestring_,
        unicode_,
        debugObject,
        fill_template,
        Subber,
        RescueDict,
        ppp,
    )
except (ImportError,) as e:
    # not sure if needed
    # from .utils import DiffFormatter
    raise

import pdb


def cpdb():
    return cpdb.enabled


cpdb.enabled = False  # type: ignore


def rpdb():  # pragma : no cover
    return rpdb.enabled


rpdb.enabled = False  # type: ignore
###################
# configuration
#####################

MISSING_ENV_T_DIRNAME = """
******************************************************************************
lazy-regression-tests:  Invalid configuration 
The template for the directory name could not be found 
for subject `%(subject)s`.
Try setting either `$%(specific)s` or the generic `$%(generic)s`.
This needs to point to a user-writeable directory of your choice.
******************************************************************************
"""


#########################
# environment variable names
#######################
env_directive = "lzrt_directive"
env_t_dirname = "lzrt_template_dirname"
env_t_basename = "lzrt_template_basename"


from collections import namedtuple

Choice = namedtuple("Choice", "code help")

opt_nodiff = "nodiff"


class DirectiveChoices(object):
    """what can go into environment variable `lzrt_directive"""

    baseline = Choice(
        "baseline",
        """establish a baseline behavior - all mismatches and IOError are ignored
and existing expecations are reset""",
    )
    skip = Choice("skip", """do not run lazy-regression-tests""")

    nodiff = Choice(opt_nodiff, """check equality, but don't run diff""")

    missing_pass = Choice(
        "missing_pass",
        """IOError on expectations will be ignored and treated as a match success
the formatted `got/received` value will be written to the expectation.
""",
    )
    assert_missing = Choice(
        "assert_missing",
        """IOError on expectations throw an AssertionError instead of an IOError.
the formatted `got/received` value will be written to the expectation.        
""",
    )

    @classmethod
    def output_help(cls, writer):

        writer("\n")
        writer("possible values in $lzrt_directive:\n")
        for k in dir(cls):
            v = getattr(cls, k)
            if isinstance(v, Choice):
                option = "'%s'" % (k)
                writer("  %-20s : %s\n" % (option, v.help))


class OnAssertionError(object):

    # use `baseline` when you want to reset the whole codeline to new expectations
    # can only be changed on the environment level, or via command line option
    # also implies onIOError.pass_missing
    baseline = DirectiveChoices.baseline.code

    # standard assertEqual behavior
    default = "error"

    # we are not running these tests
    ignore = DirectiveChoices.skip.code

    nodiff = DirectiveChoices.nodiff.code


class LazyIOErrorCodes(object):
    """what happens when read.exp throws an IOError?"""

    # default behavior: `got` => File.exp, but throw an IOError
    # differentiates data mismatch from missing `exp` files
    default = ioerror = "lazy_write_ioerror"

    # write `got` to File.exp, without throwing an exception.
    # useful when first running, but see also OnAssertionError.baseline mode
    pass_missing = "lazy_write_passmissing"

    # default behavior: `got` => File.exp, but throw an AssertionError instead
    assertion = "lazy_write_assertionerror"


SYSARG_BASELINE = "--lazy-%s" % OnAssertionError.baseline
SYSARG_IGNORE = "--lazy-%s" % OnAssertionError.ignore
SYSARG_PASS_MISSING = "--lazy-%s" % LazyIOErrorCodes.pass_missing.replace("_", "-")
SYSARG_NODIFF = "--lazy-%s" % OnAssertionError.nodiff


# allows per subject-environment lookups i.e. got may be put somewhere else than exp
t_env_dirname_subject = "lzrt_template_dirname_%(subject)s"

##############
# defaults
##############
lzrt_default_t_subdir = "%(subject)s/%(lazy_dirname_extras)s"
lzrt_default_t_basename = "%(filename)s %(classname)s %(_testMethodName)s %(lazy_basename_extras)s %(suffix)s %(extension)s"


###################
# utility functions and classes
####################


class _Control(object):
    """unifies environment and function arguments
       to determine handlers for IOError and AssertionError
       save in the LazyTemp results object as well.
    """

    def __init__(
        self, mixin: "LazyMixin", env: MediatedEnvironDict, onIOError_, **kwargs
    ):
        pass

        if not env or not env.acquired:
            env.acquire()

        directive = env.get(env_directive)

        self.skip = directive == OnAssertionError.ignore

        self.nodiff = directive == OnAssertionError.nodiff

        self.nest_testfilename = kwargs.get("nest_testfilename")

        self.lazy_filename = kwargs.get("lazy_filename")

        self.baseline = env.get(env_directive) == OnAssertionError.baseline
        if self.baseline:
            self.handler_io_error = mixin.lazy_write_passmissing
        else:
            funcname_handler_ioerror = (
                # specified in the assertLazy call?
                onIOError_
                # environment?
                or env.get(env_directive)
                # default value on instance
                or mixin.lazy_onIOError
            )
            self.handler_io_error = (
                getattr(mixin, funcname_handler_ioerror, None)
                or mixin.lazy_write_ioerror
            )


class LazyTemp(object):
    def __init__(self, control, env):
        self.fnp_exp = self.fnp_got = None
        self.env = env.copy()
        self.filterhits = {}
        self.control = control

    def notify(self, found, by_=None):
        try:
            # only save hits that have a finder.hitname

            hitname = getattr(getattr(found, "by", None), "hitname", None) or getattr(
                by_, "hitname", None
            )

            if hitname:
                li = self.filterhits.setdefault(hitname, [])
                li.append(found)

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise


ENV_PREFIX = "lzrt_"


PATRE_YAML_OBJECTSPEC = re.compile("!!python/.+$")


def yaml_to_dict(data, track_type=False):
    """take an arbitrary python object and transform it to dict form"""
    try:

        #
        str_yaml = ydump(data, default_flow_style=False)

        lines = []
        for line in str_yaml.split("\n"):

            hit = PATRE_YAML_OBJECTSPEC.search(line)
            if hit:
                line2 = PATRE_YAML_OBJECTSPEC.sub("", line).rstrip()
                lines.append(line2)

                # this isnt working yet...
                if track_type:
                    lines.append("""  _ytype : "%s" """ % line[hit.start() : hit.end()])

            else:
                lines.append(line)

        safe_yaml = "\n".join(lines)

        res = yload(safe_yaml)

        return res
    except (Exception,) as e:  # pragma : no cover
        if cpdb():
            pdb.set_trace()
        raise


class LazyMixin(object):
    """main class.  see `assertLazy`"""

    lazy_filename = "needs-setting-in-your-unitest-file"

    lazy_onIOError = LazyIOErrorCodes.default
    lazy_rescuedict = RescueDict(template="")

    lazy_environ = MediatedEnvironDict(filters=[ENV_PREFIX])

    # default for extra attributes.
    lazy_dirname_extras = ""
    lazy_basename_extras = ""

    lazytemp = None
    lazy_message_formatter = None

    lazy_message_formatter
    lazy_message_formatter = DiffFormatter()

    def lazy_filter_notify(self, found):
        self.lazytemp.notify(found)

    @classmethod
    def lazy_format_dict(cls, dict_, filter=None):
        return unicode_(
            json.dumps(dict_, sort_keys=True, indent=4, separators=(",", ":"))
        ).strip()

    @classmethod
    def lazy_format_dict2yaml(cls, dict_, filter=None):
        return ydump(dict_, default_flow_style=False)

    @property
    def verbose(self):
        res = sys.argv.count("-v")
        return res

    @classmethod
    def _lazy_get_t_dirname(cls, subject="", control=None):

        env_t_dirname_specific = fill_template(
            t_env_dirname_subject, {"subject": subject}
        )

        env = cls.lazy_environ
        if not env or not env.acquired:
            env.acquire()

        res = env.get(env_t_dirname_specific) or env.get(fill_template(env_t_dirname))

        if res is None:
            raise ValueError(
                MISSING_ENV_T_DIRNAME
                % dict(
                    subject=subject,
                    specific=env_t_dirname_specific,
                    generic=env_t_dirname,
                )
            )

        # nesting each test script under its own subdirectory
        nest_testfilename = getattr(control, "nest_testfilename", False)
        nest_testfilename = getattr(control, "lazy_filename", "")
        if nest_testfilename:
            res = os.path.join(res, control.lazy_filename)

        return res

    @classmethod
    def _lazy_get_t_basename(cls, subject):

        env = cls.lazy_environ
        if not env or not env.acquired:
            env.acquire()

        res = env.get(fill_template(env_t_basename)) or lzrt_default_t_basename
        return res

    def _lazy_write(self, fnp, formatted_data):

        dirname = os.path.dirname(fnp)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        if self.verbose:
            logger.info("%s._write:%s" % (self, fnp))

        with codecs.open(fnp, mode="w", encoding="utf-8", errors="ignore") as fo:
            fo.write(formatted_data)

    def lazy_write_assertionerror(self, fnp, formatted_data, message, exc=None):
        try:
            self._lazy_write(fnp, formatted_data)
            self.assertEqual(str(IOError(fnp)), formatted_data, message)
        except (AssertionError,) as e:
            if rpdb():  # pragma : no cover
                pdb.set_trace()
            raise
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazy_write_passmissing(self, fnp, formatted_data, message, exc=None):
        try:
            logger.warning("%s.suppressed IOError:%s" % (self, exc))
            self._lazy_write(fnp, formatted_data)
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazy_write_ioerror(self, fnp, formatted_data, message, exc):
        try:
            self._lazy_write(fnp, formatted_data)
            self.fail(str(exc))
            # raise exc
        except (IOError,) as e:
            if rpdb():  # pragma : no cover
                pdb.set_trace()
            raise
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazy_fnp_exp_root(self, control=None):
        return self._lazy_get_fnp_root(subject="exp", control=control)

    def lazy_fnp_got_root(self, control=None):
        return self._lazy_get_fnp_root(subject="got", control=control)

    def lazy_format_string(self, data, filter=None):

        if isinstance(data, unicode_):
            return data.strip()

        return unicode_(data, encoding="utf-8", errors="ignore").strip()

    def lazy_format_html(self, data, filter=None):
        # raise NotImplementedError("%s.lazy_format_html(%s)" % (self, locals()))

        data = self.lazy_format_string(data)
        if bs is None:
            logger.warning("BeautifulSoup is unavaiable")
            return data
        soup = bs(data)  # make BeautifulSoup

        if filter:
            soup = filter.format(soup, lazytemp=self.lazytemp)

        if rpdb():
            pdb.set_trace()

        return soup.prettify()  # prettify the html

    def lazy_format_json(self, data, filter=None):
        di = json.loads(data)
        return self.lazy_format_dict(di)

    def lazy_format_yaml(self, data, filter=None):
        try:
            di = yaml_to_dict(data)
            return self.lazy_format_dict2yaml(di)
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazy_format_data(self, data, extension="", filter=None):

        if isinstance(data, dict):
            res = self.lazy_format_dict(data, filter=filter)
            if isinstance(res, basestring_):
                res = res.strip()
            return res

        elif isinstance(data, bytes):
            data = data.decode("utf-8")
            if extension == "html":
                # track the cast
                data = (
                    "<!-- lazy_format_data.info:cast via bytes.decode(utf-8) -->\n%s"
                    % (data)
                )

            f = (
                getattr(self, "lazy_format_%s" % (extension.lower()), None)
                or self.lazy_format_string
            )
            return f(data).strip()

        elif isinstance(data, basestring_):

            f = (
                getattr(self, "lazy_format_%s" % (extension.lower()), None)
                or self.lazy_format_string
            )
            return f(data, filter=filter).strip()

        elif extension == "yaml":
            return self.lazy_format_yaml(data)
        else:
            di_diag = dict(
                data=str(data)[:100], datatype=type(data), extension=extension
            )

            raise NotImplementedError("%s.lazy_format_data(%s)" % (self, di_diag))
            return self.lazy_format_string(data).strip()

    def _lazy_get_fnp_root(self, subject, control=None):
        """get the root name, before extension and suffix"""

        subber = Subber(
            self,
            {
                "filename": self.lazy_filename,
                "subject": subject,
                "classname": self.__class__.__name__,
            },
            self.lazy_rescuedict,
        )

        # pdb.set_trace()

        # calculating the directory path
        t_dirname = self._lazy_get_t_dirname(subject=subject, control=control)
        _litd = t_dirname.split(os.path.sep)

        dirname_extras = getattr(self, "lazy_dirname_extras", "")
        if dirname_extras:
            # expand something like "foo, bar" into [..."%(foo)s", "%(bar)s"...]
            li_replace = ["%%(%s)s" % (attrname) for attrname in dirname_extras.split()]

            if "%(lazy_dirname_extras)s" in _litd:
                _litd = replace(_litd, "%(lazy_dirname_extras)s", li_replace)
            else:
                _litd.extend(li_replace)

        _lid = ["/"] + [fill_template(t_, subber) for t_ in _litd]

        dirname = os.path.join(*_lid)

        # calculating the filename
        t_basename = self._lazy_get_t_basename(subject)
        _litb = t_basename.split()
        _lib = [fill_template(t_, subber) for t_ in _litb]
        basename = ".".join([i_ for i_ in _lib if i_])

        basename = basename.replace(" ", "_")
        basename = basename.replace("/", "_")

        return os.path.join(dirname, basename)

    def _lazy_add_extension(self, fnp, extension="", suffix=""):
        """adds suffix, extension to the filename"""

        # don't add empty parts...
        li = [str(i_) for i_ in [fnp, suffix, extension] if i_]

        return ".".join(li)

    def assertLazy(
        self,
        got,
        extension="",
        suffix="",
        onIOError=None,
        message=None,
        filter_=None,
        formatter=None,
        f_notify=None,
        no_assert=False,
        nest_testfilename=True,
    ):
        """ check that result matches expectations saved previously.
        when the expectations file doesn't exist yet, it is created with received data
        but an error is raised unless suppressed by `onIOError`.

        :param got :  received data, to be checked against expectation
        :param extension :  used determining file names but also data formatting
        :param onIOError :  handler for when the expectation file can't be found
        :param message:  same as other assert's message parameter
        :param filter_: a filtering function f(string)=>string
        :param formatter: a function f(data, extension)=>string
        :param f_notify: if using the default filter and this is empty, reroutes notifications
                         into default filter
        """

        try:
            env = self.lazy_environ
            if not bool(self.lazy_environ):
                env.clear()
                env.acquire()

            control = _Control(
                self,
                env,
                onIOError,
                **{
                    "nest_testfilename": nest_testfilename,
                    "lazy_filename": self.lazy_filename,
                }
            )

            smsg = "%s.assertLazy:" % (self)

            tmp = self.lazytemp = LazyTemp(control, env)
            tmp.got = got

            if control.skip:
                if self.verbose:
                    logger.info("%s skipping lazy checks" % (smsg))
                return

            tmp.fnp_exp = fnp_exp = self._lazy_add_extension(
                self.lazy_fnp_exp_root(control=control), extension, suffix
            )

            # is there a filter for the extension?
            filter_ = filter_ or getattr(self, "lazy_filter_%s" % (extension), None)

            formatter = formatter or self.lazy_format_data
            if got:
                formatted_data = formatter(got, extension, filter=filter_)
            else:
                formatted_data = ""

            if filter_:
                reset_notify = False
                if f_notify is not False and not filter_.f_notify:
                    reset_notify = True
                    filter_.f_notify = self.lazy_filter_notify

                try:
                    formatted_data = filter_(formatted_data)
                finally:
                    filter_.f_notify = None

            tmp.fnp_got = fnp_got = self._lazy_add_extension(
                self.lazy_fnp_got_root(control=control), extension, suffix
            )
            self._lazy_write(fnp_got, formatted_data)

            # the caller requested not to check exp == got.  this can be done, for example
            # to use the parsing and formatting mechanisms without actually comparing.
            if no_assert:
                if self.verbose:
                    logger.info("%s no_assert:%1.  returning" % (smsg, no_assert))
                return self.lazytemp

            try:
                if self.verbose:
                    logger.info("%s.assertLazy.reading:%s" % (self, fnp_exp))

                with codecs.open(fnp_exp, encoding="utf-8", errors="ignore") as fi:
                    exp = fi.read().strip()
            except (IOError,) as e:
                return control.handler_io_error(fnp_exp, formatted_data, message, exc=e)
            except (Exception,) as e:  # pragma : no cover
                pdb.set_trace()
                raise

            if self.verbose and self.verbose >= 2:
                msg = "\nexp:%s:\n<>\ngot:%s:" % (exp, formatted_data)
                logger.info(msg)

            if control.nodiff:
                message = " not equal but diffing disabled"

            if self.lazy_message_formatter and not message:
                if exp != formatted_data:
                    # pdb.set_trace()
                    if not control.baseline:
                        message = self.lazy_message_formatter.format(
                            exp, formatted_data, window=5
                        )
                    else:
                        message = "no match but baseline mode: will reset %(fnp_exp)s and pass test"

                    if self.verbose:
                        message += (
                            "\n exp @ %(fnp_exp)s \n got @ %(fnp_got)s" % locals()
                        )

                    if rpdb() and not message:
                        pdb.set_trace()

            if control.baseline:
                try:
                    # don't try a comparison, because those that often runs too long
                    # and you're not learning that much anyway on baseline
                    self.assertTrue(exp == formatted_data, message)
                    # self.assertEqual(exp, formatted_data, message)
                except (AssertionError,) as e:
                    e.lazytemp = self.lazytemp
                    self._lazy_write(fnp_exp, formatted_data)
                    logger.warning(u"lazy: %s.  expectation has been reset" % (e))

                return self.lazytemp

            if isinstance(formatted_data, basestring_):
                formatted_data = formatted_data.strip()
            self.assertEqual(exp, formatted_data, message)

            return self.lazytemp

        except (IOError, AssertionError) as e:
            e.lazytemp = self.lazytemp
            raise
        except (Exception,) as e:  # pragma : no cover
            e.lazytemp = getattr(self, "lazytemp", None)

            if cpdb():
                pdb.set_trace()
            raise

    def lazy_debug(self):
        if self.lazytemp:
            print("lazy_debug")
            # logger.info(debugObject(self.lazytemp, "temp"))
            logger.info(debugObject(self.lazytemp.env, "env"))
            logger.info(
                "handler_io_error:%s.%s"
                % (
                    self.lazytemp.control.handler_io_error.__module__,
                    self.lazytemp.control.handler_io_error.func_name,
                )
            )


def output_help():

    if getattr("output_help", "done", False):
        return

    writer = sys.stderr.write

    writer("\n")
    writer("*" * 80)
    writer("\n")

    # pdb.set_trace()

    module = "lazy-regression-tests"

    writer(
        "%s behavior can be controlled with flags or by environment variable $lzrt_directive\n"
        % (module)
    )

    writer("available flags:\n")
    writer(
        "- %s establishes baseline behavior - IOError and mismatches pass\n"
        % (SYSARG_BASELINE)
    )
    writer("- %s don't run regression tests\n" % (SYSARG_IGNORE))
    writer("- %s pass tests with missing expectations\n" % (SYSARG_PASS_MISSING))
    writer("- %s check equality but dont run diff s\n" % (SYSARG_NODIFF))

    DirectiveChoices.output_help(writer)

    writer("\n")
    writer("*" * 80)

    output_help.done = True


if "-h" in sys.argv:
    output_help()


def lazy_pass_missing(*classes):
    # if "-h" in sys.argv:
    #     output_help()

    if SYSARG_PASS_MISSING in sys.argv:

        for cls_ in classes:
            cls_.lazy_environ[env_directive] = OnAssertionError.pass_missing
        sys.argv.remove(SYSARG_PASS_MISSING)


def lazy_nodiff(*classes):
    # if "-h" in sys.argv:
    #     output_help()
    # pdb.set_trace()

    if SYSARG_NODIFF in sys.argv:

        for cls_ in classes:
            cls_.lazy_environ[env_directive] = OnAssertionError.nodiff
        sys.argv.remove(SYSARG_NODIFF)


def lazy_baseline(*classes):
    # if "-h" in sys.argv:
    #     output_help()

    if SYSARG_BASELINE in sys.argv:

        for cls_ in classes:
            cls_.lazy_environ[env_directive] = OnAssertionError.baseline
        sys.argv.remove(SYSARG_BASELINE)


def lazy_ignore(*classes):
    # if "-h" in sys.argv:
    #     output_help()

    if SYSARG_IGNORE in sys.argv:

        for cls_ in classes:
            cls_.lazy_environ[env_directive] = OnAssertionError.ignore
        sys.argv.remove(SYSARG_IGNORE)
