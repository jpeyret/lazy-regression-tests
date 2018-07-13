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

import sys
import os
import unittest
import json
import codecs

import re

import shutil



from BeautifulSoup import BeautifulSoup as bs

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
from traceback import print_exc as xp

try:
    from utils import DiffFormatter, replace, MediatedEnvironDict
except (ImportError,) as e:
    #not sure if needed
    # from .utils import DiffFormatter
    raise


from lib.utils import ppp, debugObject
from lib.utils import fill_template, Subber, RescueDict

import pdb
def cpdb():
    return cpdb.enabled
cpdb.enabled = False

def rpdb():
    return rpdb.enabled
rpdb.enabled = False


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
#environment variable names
#######################
env_directive  = "lzrt_directive"
env_t_dirname        = "lzrt_template_dirname"
env_t_basename       = "lzrt_template_basename"


from collections import namedtuple

Choice = namedtuple('Choice', 'code help')

class DirectiveChoices(object):
    """what can go into environment variable `lzrt_directive"""

    baseline = Choice(
        "baseline", 
        """establish a baseline behavior - all mismatches and IOError are ignored
and existing expecations are reset"""
        )
    skip = Choice(
        "skip",
        """do not run lazy-regression-tests"""
        )
    missing_pass = Choice(
        "missing_pass",
        """IOError on expectations will be ignored and treated as a match success
the formatted `got/received` value will be written to the expectation.
"""
        )
    assert_missing = Choice(
        "assert_missing",
        """IOError on expectations throw an AssertionError instead of an IOError.
the formatted `got/received` value will be written to the expectation.        
"""
        )




class OnAssertionError(object):

    #use `baseline` when you want to reset the whole codeline to new expectations
    #can only be changed on the environment level, or via command line option
    #also implies onIOError.pass_missing
    baseline=DirectiveChoices.baseline.code

    #standard assertEqual behavior
    default="error"

    #we are not running these tests
    ignore = DirectiveChoices.skip.code




class LazyIOErrorCodes(object):
    """what happens when read.exp throws an IOError?"""

    #default behavior: `got` => File.exp, but throw an IOError
    #differentiates data mismatch from missing `exp` files
    default = ioerror = "lazy_write_ioerror"

    #write `got` to File.exp, without throwing an exception.
    #useful when first running, but see also OnAssertionError.baseline mode
    pass_missing = "lazy_write_passmissing"

    #default behavior: `got` => File.exp, but throw an AssertionError instead
    assertion = "lazy_write_assertionerror"



SYSARG_BASELINE = "--lazy-%s" % OnAssertionError.baseline
SYSARG_IGNORE = "--lazy-%s" % OnAssertionError.ignore
SYSARG_PASS_MISSING = "--lazy-%s" % LazyIOErrorCodes.pass_missing.replace("_","-")

    




#allows per subject-environment lookups i.e. got may be put somewhere else than exp
t_env_dirname_subject = "lzrt_template_dirname_%(subject)s"

##############
#defaults 
##############
lzrt_default_t_subdir = "%(subject)s/%(lazy_dirname_extras)s"
lzrt_default_t_basename = "%(filename)s %(classname)s %(_testMethodName)s %(lazy_basename_extras)s %(suffix)s %(extension)s"


###################
# utility functions and classes
####################

from utils import Found



class KeepTextFilter(object):
    def __init__(self, regexes = [], f_notify=None):

        """:param regexes: list of regex's.  or strings which will be compiled to regex
           you could also pass your own matching objects, they need `search(string)=>boolean`
           method
        """


        regexes_ = regexes[:]

        regexes_ = []
        for regex in regexes:
            if isinstance(regex, basestring):
                regex = re.compile(regex)
            regexes_.append(regex)

        self.regexes = regexes_
        self.f_notify = f_notify



    def _is_match(self, line):
        try:
            res = False
            for regex in self.regexes:
                if regex.search(line):
                    # if rpdb(): pdb.set_trace()
                    if self.f_notify:

                        self.f_notify(Found(line, regex))
                    return True
            return False
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    def filter(self, formatted_data):
        lines = []
        for line in formatted_data.splitlines():
            if self._is_match(line):
                lines.append(line)
        return "\n".join(lines)

    __call__ = filter


class RemoveTextFilter(KeepTextFilter):

    def filter(self, formatted_data):
        lines = []
        for line in formatted_data.splitlines():
            if not self._is_match(line):
                lines.append(line)                
        return "\n".join(lines)

    __call__ = filter



class _Control(object):
    def __init__(self, mixin, env, onIOError_):
        pass

        # pdb.set_trace()
        if rpdb(): pdb.set_trace()

        if not env or not env.acquired:
            env.acquire()

        self.skip = env.get(env_directive) == OnAssertionError.ignore

        self.baseline = env.get(env_directive) == OnAssertionError.baseline
        if self.baseline:
            self.handler_io_error = mixin.lazy_write_passmissing
        else:
            funcname_handler_ioerror = (
                #specified in the assertLazy call?
                onIOError_
                #environment?
                or env.get(env_directive)
                #default value on instance
                or mixin.lazy_onIOError
                )
            self.handler_io_error = (
                getattr(mixin, funcname_handler_ioerror, None) 
                or mixin.lazy_write_ioerror)




class LazyTemp(object):
    def __init__(self, control, env):
        self.fnp_exp = self.fnp_got = None
        self.env = env.copy()
        self.filterhits = []
        self.control = control

ENV_PREFIX = "lzrt_"

class LazyMixin(object):
    """main class.  see `assertLazy`"""

    lazy_filename = "needs-setting-in-your-unitest-file"

    lazy_onIOError = LazyIOErrorCodes.default
    lazy_rescuedict = RescueDict(template="")

    lazy_environ = MediatedEnvironDict(filters=[ENV_PREFIX]) 

    #default for extra attributes.
    lazy_dirname_extras = ""
    lazy_basename_extras = ""

    lazytemp = None
    lazy_message_formatter = None

    def lazy_filter_notify(self, found):
        self.lazytemp.filterhits.append(found)

    @classmethod
    def lazy_format_dict(cls, dict_):
        return json.dumps(dict_, sort_keys=True, indent=4)

    @property
    def verbose(self):
        res = sys.argv.count("-v")
        return res


    @classmethod
    def _lazy_get_t_dirname(cls, subject=""):

        env_t_dirname_specific = fill_template(t_env_dirname_subject, {"subject" : subject})

        env = cls.lazy_environ
        if not env or not env.acquired:
            env.acquire()


        res = ( 
                env.get(
                    env_t_dirname_specific
                )
                or 
                env.get(
                fill_template(env_t_dirname)
                )
            )

        if res is None:
            raise ValueError(
                MISSING_ENV_T_DIRNAME % dict(
                    subject=subject
                    ,specific=env_t_dirname_specific
                    ,generic=env_t_dirname
                    )
                )

        return res

    @classmethod
    def _lazy_get_t_basename(cls,subject):

        env = cls.lazy_environ
        if not env or not env.acquired:
            env.acquire()


        res = ( 
                env.get(
                fill_template(env_t_basename)
                )
                or lzrt_default_t_basename
            )
        return res

    def _lazy_write(self, fnp, formatted_data):

        dirname = os.path.dirname(fnp)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        if self.verbose:
            logger.info("%s._write:%s" % (self, fnp))

        with codecs.open(fnp, mode="w", encoding="utf-8", errors="ignore") as fo:
            fo.write(formatted_data)

    def lazy_write_assertionerror(self, fnp, formatted_data, message):
        try:
            self._lazy_write(fnp, formatted_data)
            self.assertEqual(str(IOError(fnp)), formatted_data, message)
        except (AssertionError,) as e:
            if rpdb(): pdb.set_trace()
            raise
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    def lazy_write_passmissing(self, fnp, formatted_data, message):
        try:
            logger.warning("%s.suppressed IOError" % (self))
            self._lazy_write(fnp, formatted_data)
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    def lazy_write_ioerror(self, fnp, formatted_data, message):
        try:
            self._lazy_write(fnp, formatted_data)
            raise IOError(fnp)
        except (IOError,) as e:
            if rpdb(): pdb.set_trace()
            raise
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    def lazy_fnp_exp_root(self):
        if rpdb(): pdb.set_trace()
        return self._lazy_get_fnp_root(subject="exp")

    def lazy_fnp_got_root(self):
        return self._lazy_get_fnp_root(subject="got")

    def lazy_format_string(self, data):

        if isinstance(data, unicode):
            return data

        return unicode(data, encoding="utf-8", errors="ignore")

    def lazy_format_html(self, data):
        data = self.lazy_format_string(data)
        soup = bs(data)                #make BeautifulSoup
        return soup.prettify() #prettify the html

    def lazy_format_json(self, data):
        di = json.loads(data)
        return self.lazy_format_dict(di)

    def lazy_format_data(self, data, extension=""):

        if isinstance(data, dict):
            return self.lazy_format_dict(data)

        elif isinstance(data, basestring):

            f = getattr(self, "format_%s" % (extension.lower()), None) or self.lazy_format_string
            return f(data)
        else:
            return self.lazy_format_string(data)

    def _lazy_get_fnp_root(self, subject):
        """get the root name, before extension and suffix"""

        subber = Subber(self, {"filename": self.lazy_filename, "subject":subject,"classname":self.__class__.__name__}, self.lazy_rescuedict)

        #calculating the directory path
        t_dirname = self._lazy_get_t_dirname(subject=subject)
        _litd = t_dirname.split(os.path.sep)

        dirname_extras = getattr(self, "lazy_dirname_extras","")
        if dirname_extras:
            #expand something like "foo, bar" into [..."%(foo)s", "%(bar)s"...]
            li_replace = ["%%(%s)s" % (attrname) for attrname in dirname_extras.split()]

            if "%(lazy_dirname_extras)s" in _litd:
                _litd = replace(_litd, "%(lazy_dirname_extras)s", li_replace)
            else:
                _litd.extend(li_replace)

        _lid = ["/"] + [fill_template(t_, subber) for t_ in _litd]

        dirname = os.path.join(*_lid)

        #calculating the filename
        t_basename = self._lazy_get_t_basename(subject)
        _litb = t_basename.split()
        _lib = [fill_template(t_, subber) for t_ in _litb]
        basename = ".".join([i_ for i_ in _lib if i_])

        return os.path.join(dirname, basename)
    
    def _lazy_add_extension(self, fnp, extension="", suffix=""):
        """adds suffix, extension to the filename"""

        #don't add empty parts...
        li = [str(i_) for i_ in [fnp, suffix, extension] if i_]

        return ".".join(li)


    def assertLazy(self, got, extension="", suffix="", onIOError=None, message=None, filter_=None, formatter=None, f_notify=None):
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

            control = _Control(self, env, onIOError)

            tmp = self.lazytemp = LazyTemp(control, env)



            if control.skip:
                logger.info("skipping lazy checks")
                return

            tmp.fnp_exp = fnp_exp = self._lazy_add_extension(self.lazy_fnp_exp_root(), extension, suffix)

            formatter = formatter or self.lazy_format_data
            formatted_data = formatter(got, extension)

            #is there a filter for the extension?
            filter_ = filter_ or getattr(self, "lazy_filter_%s" % (extension), None)
            if filter_:
                # if rpdb(): pdb.set_trace()
                reset_notify = False
                if f_notify is not False and not filter_.f_notify:
                    reset_notify = True
                    filter_.f_notify = self.lazy_filter_notify

                try:
                    formatted_data = filter_(formatted_data)
                finally:
                    filter_.f_notify = None

            tmp.fnp_got = fnp_got = self._lazy_add_extension(self.lazy_fnp_got_root(), extension, suffix)
            self._lazy_write(fnp_got, formatted_data)

            try:
                if self.verbose:
                    logger.info("%s.assertLazy.reading:%s" % (self, fnp_exp))
                # with open(fnp_exp) as fi:
                with codecs.open(fnp_exp, encoding="utf-8", errors="ignore") as fi:
                    exp = fi.read()
            except (IOError,) as e:
                # handler = self._lazy_get_handler_io_error(onIOError)

                # try:
                #     assert handler == control.handler_io_error
                # except (Exception,) as e:
                #     if cpdb(): 
                #         self.lazy_debug()
                #         pdb.set_trace()
                #     raise

                return control.handler_io_error(fnp_exp, formatted_data, message)

            if self.verbose >= 2:
                msg = "\nexp:%s:\n<>\ngot:%s:" % (exp, formatted_data)
                logger.info(msg)

            # if rpdb(): pdb.set_trace()
            if self.lazy_message_formatter and not message:
                if exp != formatted_data:
                    message = self.lazy_message_formatter.format(exp, formatted_data, window=5)

            if control.baseline:
                try:
                    self.assertEqual(exp, formatted_data, message)
                except (AssertionError,) as e:
                    self._lazy_write(fnp_exp, formatted_data)
                    logger.warning("%s.  expectation has been reset" % (e))
                return

            self.assertEqual(exp, formatted_data, message)

        except (IOError,AssertionError) as e:
            raise
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    def lazy_debug(self):
        if self.lazytemp:
            print("lazy_debug")
            # logger.info(debugObject(self.lazytemp, "temp"))
            logger.info(debugObject(self.lazytemp.env, "env"))
            logger.info(
                "handler_io_error:%s.%s" 
                % (
                    self.lazytemp.control.handler_io_error.__module__
                    ,self.lazytemp.control.handler_io_error.func_name
                    )

                )


def output_help():

    if getattr("output_help", "done", False):
        return

    module = "lazy-regression-tests"
    logger.info(
        "%s - %s establishes baseline behavior - IOError and mismatches pass" % 
        (module, SYSARG_BASELINE)
        )
    logger.info(
        "%s - %s don't run regression tests" % 
        (module, SYSARG_IGNORE)
        )
    logger.info(
        "%s - %s pass tests with missing expectations" % 
        (module, SYSARG_PASS_MISSING)
        )

    output_help.done = True

def lazy_pass_missing(*classes):
    if "-h" in sys.argv:
        output_help()

    if SYSARG_PASS_MISSING in sys.argv:

        for cls_ in classes:
            cls_.lazy_environ[env_directive] = OnAssertionError.pass_missing
        sys.argv.remove(SYSARG_PASS_MISSING)


def lazy_baseline(*classes):
    if "-h" in sys.argv:
        output_help()

    if SYSARG_BASELINE in sys.argv:

        for cls_ in classes:
            cls_.lazy_environ[env_directive] = OnAssertionError.baseline
        sys.argv.remove(SYSARG_BASELINE)

def lazy_ignore(*classes):
    if "-h" in sys.argv:
        output_help()

    if SYSARG_IGNORE in sys.argv:

        for cls_ in classes:
            cls_.lazy_environ[env_directive] = OnAssertionError.ignore
        sys.argv.remove(SYSARG_IGNORE)



