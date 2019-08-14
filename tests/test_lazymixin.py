# -*- coding: utf-8 -*-
"""
test lazy-regression-tests
"""

import sys
import os
import unittest
import json
import codecs
from collections import namedtuple

import re
import shutil
import difflib

pyver = sys.version_info.major


try:
    import unittest.mock as mock
except (ImportError,) as ei:
    import mock  # python 2?

try:
    from bs4 import BeautifulSoup as bs
except (ImportError,) as e:
    try:
        from BeautifulSoup import BeautifulSoup as bs
    except (Exception,) as e2:
        bs = None


import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
from traceback import print_exc as xp

# from lib.utils import set_cpdb, set_rpdb, ppp, debugObject
# from lib.utils import fill_template, Subber, RescueDict

from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
    fill_template,
    Subber,
    RescueDict,
)

from lazy_regression_tests.filters import CSSRemoveFilter


import pdb


def cpdb(**kwds):  # pragma : no cover
    if cpdb.enabled == "once":
        cpdb.enabled = False  # type: ignore
        return True
    return cpdb.enabled


cpdb.enabled = False  # type: ignore


def rpdb():  # pragma : no cover
    return rpdb.enabled


rpdb.enabled = False  # type: ignore
#

from lazy_regression_tests.core import (
    lzrt_default_t_basename,
    lzrt_default_t_subdir,
    LazyMixin,
    LazyIOErrorCodes,
    OnAssertionError,
    DiffFormatter,
    lzrt_default_t_basename,
)

from lazy_regression_tests.utils import (
    DictionaryKeyFilter,
    _Filter,
    RemoveTextFilter,
    RegexRemoveSaver,
    KeepTextFilter,
)

##########################################################
# tests
##########################################################


lzrt_template_dirname = "/<someroot>/out/tests/%(subject)s/%(lazy_dirname_extras)s"
lzrt_template_dirname_got = "/<someroot>/out/tests/%(subject)s/%(lazy_dirname_extras)s"
lzrt_template_dirname_exp = "/<someroot>/wk/tests/%(subject)s/%(lazy_dirname_extras)s"
lzrt_template_basename = lzrt_default_t_basename

di_mock_env = dict(
    lzrt_template_dirname=lzrt_template_dirname,
    lzrt_template_dirname_got=lzrt_template_dirname_got,
    lzrt_template_dirname_exp=lzrt_template_dirname_exp,
    lzrt_template_basename=lzrt_template_basename,
)

di_mock_env_no_extras = dict(
    [(k, v.replace("/%(lazy_dirname_extras)s", "")) for k, v in di_mock_env.items()]
)

module_ = "builtins"
module_ = module_ if module_ in sys.modules else "__builtin__"
funcpath_open = "%s.open" % module_


class Foo(object):
    pass


if __name__ == "__main__":
    lazy_filename = os.path.splitext(os.path.basename(__file__))[0]
else:
    try:
        logger.error("Foo.__module__:%s:" % (Foo.__module__))
        lazy_filename = Foo.__module__.split(".")[-1]
        # lazy_filename = "xxx"
        # lazy_filename = os.path.splitext(os.path.basename(__file__))[0]
        logger.error(Foo.__module__)
    except (NameError,) as e:
        logger.error(debugObject(globals(), "globals"))
        logger.error(debugObject(dir(Foo), "Foo"))
        raise


def debug_env(self):
    ppp(self.lazy_environ, "lazyenv")


class LazyMixinBasic(LazyMixin):

    """
    these are for not-live tests.



    """

    debug_env = debug_env

    lazy_filename = lazy_filename

    tmp_formatted_data = None

    def _lazy_write(self, fnp, formatted_data):
        self.tmp_formatted_data = formatted_data


class Test_001_Configuration(LazyMixinBasic, unittest.TestCase):

    # old_os_environ = os.environ
    # try:
    #     os.environ = {}
    #     self.assertRaises(OSError, my_function)
    # finally:
    #     os.environ = old_os_environ

    def test_001_missing_configuration(self):
        try:
            try:
                ante = os.environ
                os.environ = {}
                try:
                    tdirname = self._lazy_get_t_dirname("exp")
                except (ValueError,) as e:
                    message = str(e)
                    self.assertTrue("lzrt_template_dirname" in message)

                tbasename = self._lazy_get_t_basename("exp")
                # should default to default
                self.assertEqual(lzrt_default_t_basename, tbasename)

            finally:
                os.environ = ante

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise


@mock.patch.dict(os.environ, di_mock_env)
class Test_Basics(LazyMixinBasic, unittest.TestCase):
    def test_extensions(self):
        try:
            fnp_root = self.lazy_fnp_exp_root()

            got = self._lazy_add_extension(fnp_root, "html")
            exp = "%s.html" % (fnp_root)
            self.assertEqual(exp, got)

            suffix = "test"
            exp2 = "%s.%s.html" % (fnp_root, suffix)
            got2 = self._lazy_add_extension(fnp_root, "html", suffix=suffix)
            self.assertEqual(exp2, got2)

            got3 = self._lazy_add_extension(fnp_root)
            self.assertEqual(fnp_root, got3)
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def test_format_data(self):
        self.assertEqual(
            "{}", self.lazy_format_dict({}), "lazy_format_dict returns json.string"
        )
        self.assertEqual("{}", self.lazy_format_data({}))
        self.assertEqual("{}", self.lazy_format_data("{}"))

    def test_format_unicode_data(self):

        data = u"foo"
        self.assertEqual(data, self.lazy_format_data(data))


class TestBasic(LazyMixinBasic, unittest.TestCase):
    def lazy_write_ioerror(self, *args, **kwds):
        logger.info("%s.lazy_write_ioerror" % (self))
        pass

    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_equal_string(self):
        """sanity check - are we ok if exp == got"""

        try:
            exp = got = "foo"

            if pyver == 3:
                exp = str.encode(exp)
                got = str.encode(got)

            with mock.patch(funcpath_open, mock.mock_open(read_data=exp)):
                self.assertLazy(got, onIOError=LazyIOErrorCodes.pass_missing)

            with mock.patch(funcpath_open, mock.mock_open(read_data=exp)):
                self.assertLazy(got, ".txt")

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_002_filename(self):

        if __name__ == "__main__":
            name = os.path.splitext(os.path.basename(__file__))[0]
        else:
            name = self.__module__.split(".")[-1]

        print("self.__module__:%s" % (self.__module__))
        print("__file__:%s:" % (__file__))
        print("name:%s:" % (name))

        exp = got = "foo"

        if pyver == 3:
            exp = str.encode(exp)
            got = str.encode(got)

        with mock.patch(funcpath_open, mock.mock_open(read_data=exp)):
            self.assertLazy(got)

        print("fnp_got:%s:" % (self.lazytemp.fnp_got))

        msg = "name:%s:not in fnp_got:%s" % (name, self.lazytemp.fnp_got)
        self.assertTrue(name in self.lazytemp.fnp_got, msg)

    @mock.patch.dict(os.environ, di_mock_env)
    def test_003_suffix(self):

        got = "something"

        if pyver == 3:
            got = str.encode(got)

        suffix = "mysuffix"
        with mock.patch(funcpath_open, mock.mock_open(read_data=got)):
            self.assertLazy(got, "txt", suffix=suffix)

        msg = "suffix:%s:not in fnp_got:%s" % (suffix, self.lazytemp.fnp_got)
        self.assertTrue(suffix in self.lazytemp.fnp_got, msg)

    def test_004_attribute_names(self):
        try:
            mixin = LazyMixin()
            attrnames = dir(mixin)
            logger.info("dir(mixin):%s" % (attrnames))

            tolerated = ["verbose", "assertLazy"]

            prefix = "lazy"
            bad = []
            for attrname in attrnames:
                if attrname.startswith("__") and attrname.endswith("__"):
                    continue

                if attrname in tolerated:
                    continue

                try:
                    msg = "%s. should have started with _lazy or lazy" % attrname
                    attrname2 = attrname.lstrip("_")
                    self.assertTrue(attrname2.startswith(prefix), msg)
                except (AssertionError,) as e:
                    bad.append(attrname)

            bad.sort()
            bad and self.fail("naming convention:%s" % "\n  ".join(bad))

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_005_fnp_exp_root(self):
        try:
            exp = got = None
            exp = os.path.join(
                lzrt_template_dirname_exp
                % {"subject": "exp", "lazy_dirname_extras": ""},
                "test_lazymixin.%s.%s"
                % (self.__class__.__name__, self._testMethodName),
            )

            got = self.lazy_fnp_exp_root()
            msg = "\nexp:%s\n<>\ngot:%s" % (exp, got)
            self.assertEqual(exp, got, msg)

        except (Exception,) as e:  # pragma : no cover
            ppp(os.environ, "os.environ")
            ppp(dict(exp=exp, got=got, lazy_filename=self.lazy_filename))

            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env_no_extras)
    def test_006_fnp_got_root(self):
        try:
            exp = got = None
            exp = os.path.join(
                lzrt_template_dirname_got
                % {"subject": "got", "lazy_dirname_extras": ""},
                "test_lazymixin.%s.%s"
                % (self.__class__.__name__, self._testMethodName),
            )

            got = self.lazy_fnp_got_root()
            msg = "\nexp:%s\n<>\ngot:%s" % (exp, got)
            self.assertEqual(exp, got, msg)

        except (Exception,) as e:  # pragma : no cover
            ppp(os.environ, "os.environ")
            ppp(dict(exp=exp, got=got))
            if cpdb():
                pdb.set_trace()
            raise


lorem = """
<html><head><title></title></head><body>
<p>Lorem ipsum dolor sit amet, consectetur 
adipisicing elit. Consequatur Quidem, sint incidunt?</p></body></html>
"""


class Test_IOError_Handling(LazyMixin, unittest.TestCase):

    lazy_filename = lazy_filename

    debug_env = debug_env

    def _lazy_write(self, fnp, formatted_data):
        pass

    def lazy_format_html(self, data):
        self.formatted_by = "lazy_format_html"
        self.data = data

    data = formatted_by = handled_by = None

    def lazy_write_assertionerror(self, fnp, formatted_data, message, exc):
        try:
            self.handled_by = LazyIOErrorCodes.assertion
            self.assertEqual("IOError(%s)" % (fnp), formatted_data)
        except (AssertionError,) as e:
            raise
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazy_write_ioerror(self, fnp, formatted_data, message, exc):
        self.handled_by = "lazy_write_ioerror"
        raise IOError()

    di = di_mock_env.copy()
    di.update(lzrt_directive=LazyIOErrorCodes.assertion)

    @mock.patch.dict(os.environ, di.copy())
    def test_write_assertionerror(self):

        got = exp = "wont be found"
        try:

            with mock.patch(
                funcpath_open, mock.mock_open(read_data=exp)
            ) as mocked_open:

                self.lazy_environ["lzrt_directive"] = LazyIOErrorCodes.assertion

                mocked_open.side_effect = IOError("fake IOError")
                try:
                    self.assertLazy(got)
                except (AssertionError,) as e:
                    self.assertEqual(self.handled_by, LazyIOErrorCodes.assertion)
                except (Exception,) as e:  # pragma : no cover
                    # pdb.set_trace()
                    if rpdb():  # pragma : no cover
                        pdb.set_trace()
                    self.fail("should have AssertionError. got Exception:%s" % str(e))

                else:
                    self.fail("should have AssertionError")

        finally:
            self.lazy_environ.clear()

    @mock.patch.dict(os.environ, di_mock_env)
    def test_write_ioerror(self):

        got = exp = "wont be found"

        try:
            self.lazy_environ["lzrt_directive"] = LazyIOErrorCodes.ioerror

            with mock.patch(
                funcpath_open, mock.mock_open(read_data=exp)
            ) as mocked_open:

                mocked_open.side_effect = IOError("fake IOError")
                try:
                    self.assertLazy(got)
                except (IOError,) as e:
                    self.assertEqual(self.handled_by, "lazy_write_ioerror")

                except (AssertionError,) as e:
                    if (
                        self.lazy_environ.get("lzrt_directive")
                        == LazyIOErrorCodes.assertion
                    ):
                        self.assertEqual(self.handled_by, LazyIOErrorCodes.assertion)
                    else:
                        raise

                except (Exception,) as e:  # pragma : no cover
                    raise
                else:
                    self.fail("should have IOError")

        except (AssertionError, IOError) as e:
            raise

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise
        finally:
            self.lazy_environ.clear()


class LazyMixin_DirRdbname(LazyMixinBasic):
    """put `rdbname` attribute, if found, in the directory hieararchy"""

    lazy_dirname_extras = "rdbname"


def debug_expgot(exp, got, testee=None):

    li = ["\n"]
    if testee:
        li.append(str(testee))
    li.append("exp:%s:" % (exp))
    li.append("got:%s:" % (got))

    logger.info("\n  ".join(li))


class Test_DirRdbname(LazyMixin_DirRdbname, unittest.TestCase):
    @mock.patch.dict(os.environ, di_mock_env)
    def test_fnp_exp_root(self):
        try:
            self.rdbname = "mydb"

            exp = got = None
            exp = os.path.join(
                lzrt_template_dirname_exp
                % {"subject": "exp", "lazy_dirname_extras": self.rdbname},
                "test_lazymixin.%s.%s"
                % (self.__class__.__name__, self._testMethodName),
            )

            got = self.lazy_fnp_exp_root()
            msg = "\nexp:%s\n<>\ngot:%s" % (exp, got)
            self.assertEqual(exp, got, msg)

        except (Exception,) as e:  # pragma : no cover
            ppp(os.environ, "os.environ")
            debug_expgot(exp, got)

            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_fnp_exp_root_missing_rdbname(self):
        try:
            # self.rdbname = "mydb"

            exp = got = None
            exp = os.path.join(
                lzrt_template_dirname_exp
                % {"subject": "exp", "lazy_dirname_extras": ""},
                "test_lazymixin.%s.%s"
                % (self.__class__.__name__, self._testMethodName),
            )

            got = self.lazy_fnp_exp_root()
            msg = "\nexp:%s\n<>\ngot:%s" % (exp, got)
            self.assertEqual(exp, got, msg)

            if self.verbose:
                debug_expgot(exp, got, self)

        except (Exception,) as e:  # pragma : no cover
            ppp(os.environ, "os.environ")
            debug_expgot(exp, got)

            if cpdb():
                pdb.set_trace()
            raise


# di = dict(lzrt_template_dirname="/Users/jluc/kds2/out/tests/LazyMixin/%(subject)s")

livetests_dir = os.environ.get("lzrt_livetests_dir", "")

has_directory_to_write_to = os.path.isdir(livetests_dir)

di_livetest = {}

NO_TESTWRITES_MSG = """skipping Live Tests. no writeable test directory provided in environment variable $lzrt_livetests_dir """

if has_directory_to_write_to:

    # flush the tmp directory
    dirtgt = os.path.join(livetests_dir, "tmp")

    if os.path.isdir(dirtgt):
        shutil.rmtree(dirtgt)

    lzrt_template_dirname = os.path.join(dirtgt, lzrt_default_t_subdir)

    live_seed = dict(
        lzrt_template_dirname=lzrt_template_dirname,
        lzrt_template_basename=lzrt_default_t_basename,
        lzrt_template_dirname_exp=lzrt_template_dirname,
        lzrt_template_dirname_got=lzrt_template_dirname,
    )

    # pdb.set_trace()
    ppp(live_seed, "live_seed")


class BaseHtmlFilter(LazyMixinBasic, unittest.TestCase):

    patre_manual_remove = re.compile("csrfmiddlewaretoken|var\ssettings|nodiff")

    _li_remove = [
        RegexRemoveSaver("var\ssettings\s=\s", hitname="settings"),
        re.compile("var\scsrfmiddlewaretoken\s=\s"),
    ]

    def format_exp(self):
        exp = []
        for line in self.data.split("\n"):
            if not self.patre_manual_remove.search(line):
                exp.append(line)

        res = "\n".join(exp)

        self.exp = self.mock_exp = bs(res).prettify()
        if pyver == 3:
            self.mock_exp = str.encode(self.exp)

    def setUp(self):

        try:
            if self.__class__ == BaseHtmlFilter:
                return

            super(BaseHtmlFilter, self).setUp()

            li_remove = self._li_remove + getattr(self, "li_remove", [])

            self.lazy_filter_html = RemoveTextFilter(
                li_remove, f_notify=self.lazy_filter_notify
            )

            self.format_exp()

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    di = di_livetest.copy()

    @mock.patch.dict(os.environ, di)
    def test(self):
        try:
            if self.__class__ == BaseHtmlFilter:
                return

            with mock.patch(funcpath_open, mock.mock_open(read_data=self.mock_exp)):
                if rpdb():  # pragma : no cover
                    pdb.set_trace()
                self.assertLazy(self.data, extension="html")
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise


class TestCssFilter(BaseHtmlFilter):
    data = """
<script>
var csrfmiddlewaretoken = 'wTNDVhWQHWzbf0Yb7mWo7PG03SgE9rpWfNXD3ZpbPm9IaZXAs3DuBUbOzI8oFutW';
var settings = {"li_user_message": []};
</script>
<div class="row">
    <div>keep ante</div>
    <div class="nodiff">remove this</div>
    <div>keep post</div>
</div>

    """

    li_remove = [CSSRemoveFilter(".nodiff")]


@unittest.skipUnless(has_directory_to_write_to, NO_TESTWRITES_MSG)
class TestLive(LazyMixin, unittest.TestCase):

    debug_env = debug_env

    def setUp(self):
        # raise NotImplementedError("%s.setUp" % (self))
        self.old_seed = self.lazy_environ.seed

        self.lazy_environ.seed = live_seed
        self.lazy_environ.clear()

    def tearDown(self):
        self.lazy_environ.seed = self.old_seed
        # raise NotImplementedError("%s.tearDown" % (self))
        self.lazy_environ.clear()

    lazy_filename = lazy_filename

    lazy_message_formatter = DiffFormatter()

    # this will be used, if found, in the directory names.
    lazy_dirname_extras = "rdbname"

    @mock.patch.dict(os.environ, di_livetest)
    def test_001_basic(self):
        got = "something"
        # this will warn only first time, because exp does not exist
        self.assertLazy(got, onIOError=LazyIOErrorCodes.pass_missing)

        # and will pass the 2nd because it was just created
        self.assertLazy(got)

        # and now it should fail
        try:
            got2 = "different"
            self.assertLazy(got2)
            self.fail("should have gotten %s<>%s AssertionError" % (got, got2))
        except (AssertionError,) as e:
            self.assertTrue(got in str(e))
            self.assertTrue(got2 in str(e))
        except (Exception,) as e:  # pragma : no cover
            self.fail("should have gotten %s<>%s AssertionError" % (got, got2))

    @mock.patch.dict(os.environ, di_livetest)
    def test_002_html(self):
        data = lorem

        self.assertLazy(data, "html", onIOError=LazyIOErrorCodes.pass_missing)

        # and will pass the 2nd because it was just created
        self.assertLazy(data, "html")

    @mock.patch.dict(os.environ, di_livetest)
    def test_003_suffix(self):
        got1 = "<div><span>got1</span></div>"
        got2 = "<div><span>got2</span></div>"

        self.assertLazy(
            got1, "html", onIOError=LazyIOErrorCodes.pass_missing, suffix="suffix1"
        )
        self.assertLazy(
            got2, "html", onIOError=LazyIOErrorCodes.pass_missing, suffix="suffix2"
        )

        self.assertLazy(got1, "html", suffix="suffix1")
        self.assertLazy(got2, "html", suffix="suffix2")

    di = di_livetest.copy()
    di.update(lzrt_directive=OnAssertionError.baseline)

    @mock.patch.dict(os.environ, di)
    def test_004_baseline(self):

        got = "something"
        got2 = "different"

        # OnAssertionError.baseline suppresses everything...
        self.assertLazy(got)

        with open(self.lazytemp.fnp_exp) as fi:
            self.assertEqual(got, fi.read())

        self.assertLazy(got2)

        # now check that exp == got2
        with open(self.lazytemp.fnp_exp) as fi:
            self.assertEqual(got2, fi.read())

    di = di_livetest.copy()
    di.update(lzrt_directive="skip")

    @mock.patch.dict(os.environ, di)
    def test_0041_skip(self):

        got = "something"
        got2 = "different"

        # OnAssertionError.baseline suppresses everything...
        self.assertLazy(got)

    @mock.patch.dict(os.environ, di_livetest)
    def test_005_rdbname_in_directory(self):
        got = "something"
        got2 = "different"
        db1 = "db1"
        db2 = "db2"

        self.rdbname = db1
        self.assertLazy(got, onIOError=LazyIOErrorCodes.pass_missing)

        self.assertTrue(db1 in self.lazytemp.fnp_exp)
        self.assertTrue(db1 in self.lazytemp.fnp_got)

        # and this should fail with an IOError because it's not the
        # same rdbname so File.exp is missing.
        self.rdbname = db2
        try:
            self.assertLazy(got)
            self.fail("should have gotten %s<>%s AssertionError" % (got, got2))
        except (IOError,) as e:
            logger.info("got my IOError")
            self.assertTrue(db2 in str(e))
        except (Exception,) as e:  # pragma : no cover
            self.fail("should have gotten %s<>%s AssertionError" % (got, got2))

        # now this should work
        self.rdbname = db1
        self.assertLazy(got)

    @mock.patch.dict(os.environ, di_livetest)
    def test_006_dict(self):
        try:
            data = dict(a=1, b=2, c=3)
            self.assertLazy(data, "json", onIOError=LazyIOErrorCodes.pass_missing)
            data.update(d=4)
            try:
                self.assertLazy(data, "json")
            except (AssertionError,) as e:
                # pdb.set_trace()
                pass
                found = False
                lines = [line for line in str(e).splitlines() if line.startswith("+")]
                # pdb.set_trace()
                for line in lines:
                    if '"d"' in line:
                        found = True
                        break
                self.assertTrue(
                    found, "lines:%s, should have included the extra d=4 item" % (lines)
                )

            else:
                self.fail("should have had an AssertionError")

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_livetest)
    def test_007_filter(self):

        try:
            data = """
            blah blah
            skip
            dude
            """

            ignore = "skip"

            self.lazy_filter_html = RemoveTextFilter(
                [ignore], f_notify=self.lazy_filter_notify
            )

            self.assertLazy(data, "html", onIOError=LazyIOErrorCodes.pass_missing)

            with open(self.lazytemp.fnp_exp) as fi:
                written = fi.read()
            self.assertFalse(ignore in written, written)

            # check what the filter stripped out
            # self.assertTrue(ignore in list(self.lazytemp.filterhits.values())[0].found)

            data = data.replace(ignore, "%s this" % (ignore))

            self.assertLazy(data, "html")

            self.lazy_filter_txt = KeepTextFilter(
                ["a", "b", "c"], f_notify=self.lazy_filter_notify
            )

            data = """a
            a
            b
            d
            """

            self.assertLazy(data, "txt", onIOError=LazyIOErrorCodes.pass_missing)

            with open(self.lazytemp.fnp_exp) as fi:
                written = fi.read()
            self.assertFalse("d" in written)

            data = """a
            a
            b
            e
            """
            self.assertLazy(data, "txt")

            filter_ = KeepTextFilter(["a", "b"])

            self.assertLazy(
                data, "text", onIOError=LazyIOErrorCodes.pass_missing, filter_=filter_
            )
            with open(self.lazytemp.fnp_exp) as fi:
                written = fi.read()

            exp = """a
            a
            b
            """

            self.assertEqual(written.strip(), exp.strip())
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_livetest)
    def test_0071_filter_regex(self):

        try:
            data = """
var debug_chart = 2;

// settings are set up by <settings object>.resolve_as_json_on_context;
var settings = {"tags": [{"disable_override": true, "checked": null, "description": "manage security", "choices_value2": null, "hide_message": true, "allow_entry_ivalue1": false, "system_write": true, "allow_entry_cvalue2": false, "ivalue1": null, "tagtype": "M_SEC", "cvalue2": null, "override": null, "message_value": ""}, {"disable_override": true, "checked": true, "description": "User count", "choices_value2": null, "hide_message": false, "allow_entry_ivalue1": false, "system_write": true, "allow_entry_cvalue2": false, "ivalue1": 139, "tagtype": "M_UCN", "cvalue2": " ", "override": null, "message_value": "139"}], "portalname": "EMPLOYEE", "li_rdbname": ["pgfin92"], "is_superuser": false, "tracker": {"projectname": "", "main": {"objectvalue1": "PeopleSoft User", "projectname": "", "objecttype": -1}, "psprsmdefn_detail": {"objectvalue1": "", "objectvalue2": "", "objectvalue3": "", "projectname": "", "objecttype": 55}}, "li_user_message": [], "objectvalue01": "PeopleSoft User", "ROLENAME": "PeopleSoft User", "rdbname": "hcm91dmo"};
var csrfmiddlewaretoken = 'wTNDVhWQHWzbf0Yb7mWo7PG03SgE9rpWfNXD3ZpbPm9IaZXAs3DuBUbOzI8oFutW';
var csrf_token = 'wTNDVhWQHWzbf0Yb7mWo7PG03SgE9rpWfNXD3ZpbPm9IaZXAs3DuBUbOzI8oFutW';

    <script>
    
    // settings are set up by <ViewManager>.calc_json_settings()
    var settings = {"li_user_message": [], "rdbname_0": "hcm91dmo", "rdbname_1": "pgfin92", "objectvalue01": "FEDTBHADMN1", "objectvalue11": "AMARTIN", "xdb_mode": true, "rdbname_r": "pgfin92", "rdbname_l": "hcm91dmo"};
    
    </script>


// require( ["pssecurity/detail_require"], function(module){
// module.init();
// });
"""

            li_remove = [
                # re.compile("var\ssettings\s=\s"),
                # RegexRemoveSaver saves the hit in list temp.filterhis[hitname]
                RegexRemoveSaver("var\ssettings\s=\s", hitname="settings"),
                re.compile("var\scsrfmiddlewaretoken\s=\s"),
                re.compile("var\scsrf_token\s=\s"),
            ]

            self.lazy_filter_html = RemoveTextFilter(
                li_remove, f_notify=self.lazy_filter_notify
            )

            temp = self.assertLazy(
                data, "html", onIOError=LazyIOErrorCodes.pass_missing
            )

            self.assertTrue(
                self.lazytemp.filterhits["settings"][0].found.startswith("var settings")
            )

            with open(self.lazytemp.fnp_exp) as fi:
                written = fi.read()

            self.assertFalse("csrf" in written, written)
            self.assertFalse("var settings" in written, written)

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_livetest)
    def test_010_unequal_string(self):

        try:

            exp = "foo"
            got = exp + ".unexpected"

            self.assertLazy(exp, onIOError=LazyIOErrorCodes.pass_missing)
            try:
                self.assertLazy(got)
            except (AssertionError,) as e:
                pass
            else:
                self.fail("should have failed")

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise


class TestThrottling(LazyMixin, unittest.TestCase):
    def setUp(self):
        self.lazy_message_formatter = DiffFormatter(maxlines=5)

    def test_it(self):
        exp = "\n".join([str(i) for i in range(0, 100)])
        got = "\n".join([str(i + 100) for i in range(0, 100)])

        message = self.lazy_message_formatter.format(exp, got)

        print(message)


class TestFilters(unittest.TestCase):

    matchers = ["csrf", "sysdate"]
    _data = dict(csrf="skip.csrf", sysdate="skip.sysdate", keep1="keep1", keep2="keep2")

    def setUp(self):
        self.watcher = _Filter(self.matchers)
        self.data = self._data.copy()

    def test_001_create(self):
        self.assertTrue(self.watcher)

    def test_002_scan(self):

        try:
            msg = None
            res = self.watcher.scan(self.data)

            for key in self.matchers:
                # if self.data.has_key(key):
                if key in self.data:
                    found = None
                    for f_ in res.finds:
                        if key == f_.found[0]:
                            found = True

                    msg = "did not find %s in res.finds:%s" % (key, res.finds)
                    self.assertTrue(found, msg)

        except (Exception,) as e:  # pragma : no cover
            logger.info(msg)
            logger.error(str(e))
            if cpdb():
                pdb.set_trace()
            raise

    def test_003_remove(self):

        try:
            msg = None
            self.watcher = DictionaryKeyFilter(self.matchers)
            # self.watcher.callback = worker.process
            exp = self.data.copy()

            res = self.watcher.scan(self.data)

            self.assertTrue(
                self.watcher.callback,
                "DictionaryKeyFilter.callback should self.worker.process",
            )

            for key in self.matchers:
                try:
                    del exp[key]
                except (KeyError,) as e:
                    pass

            self.assertEqual(exp, self.data)

        except (Exception,) as e:  # pragma : no cover
            logger.info(msg)
            logger.error(str(e))
            if cpdb():
                pdb.set_trace()
            raise


class TestFilters_Absent(TestFilters):

    matchers = ["xcsrf", "xsysdate"]
    _data = dict(csrf="skip.csrf", sysdate="skip.sysdate", keep1="keep1", keep2="keep2")


if __name__ == "__main__":

    set_cpdb(cpdb, remove=True)
    set_rpdb(rpdb, remove=True)

    sys.exit(unittest.main())
