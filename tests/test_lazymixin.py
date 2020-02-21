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
import tempfile


import re
import shutil
import difflib

# pyver = sys.version_info.major
pyver = "?"


verbose = "-v" in sys.argv

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
from traceback import print_exc as xp  # pylint: disable=unused-import


from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
    fill_template,
    Subber,
    RescueDict,
    Dummy,
)


from lazy_regression_tests.lazy3.filters import (
    RegexSubstitHardcoded,
    RegexRemoveSaver,
    DictFilter,
    CSSRemoveFilter,
    FilterDirective,
    FilterManager,
)

from lazy_regression_tests.lazy3.core import OPT_DIRECTIVE_BASELINE


rescuedict = RescueDict()

import pdb


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


# from lazy_regression_tests.core import (
#     lzrt_default_t_basename,
#     lzrt_default_t_subdir,
#     LazyMixin,
#     LazyIOErrorCodes,
#     OnAssertionError,
#     DiffFormatter,
#     lzrt_default_t_basename,
# )

# from lazy_regression_tests.utils import (
#     DictionaryKeyFilter,
#     _Filter,
#     RemoveTextFilter,
#     RegexRemoveSaver,
#     KeepTextFilter,
# )

from lazy_regression_tests.lazy3 import LazyMixin

##########################################################
# tests
##########################################################

lzrt_default_t_basename = "%(filename)s %(classname)s %(_testMethodName)s %(lazy_basename_extras)s %(suffix)s %(extension)s"


dirtemp = tempfile.mkdtemp(prefix="lazy_regression_tests_")


# lzrt_template_dirname = os.path.join(dirtemp, "out/%(subject)s/%(lazy_dirname_extras)s")
# lzrt_template_dirname_got = os.path.join(dirtemp, "got/%(subject)s/%(lazy_dirname_extras)s")
# lzrt_template_dirname_exp = os.path.join(dirtemp, "exp/%(subject)s/%(lazy_dirname_extras)s")

lzrt_template_dirname = os.path.join(dirtemp, "out")
lzrt_template_dirname_got = os.path.join(dirtemp, "got")
lzrt_template_dirname_exp = os.path.join(dirtemp, "exp")


lzrt_template_basename = lzrt_default_t_basename


di_mock_env = dict(
    lzrt_template_dirname=lzrt_template_dirname,
    lzrt_template_dirname_got=lzrt_template_dirname_got,
    lzrt_template_dirname_exp=lzrt_template_dirname_exp,
    lzrt_template_basename=lzrt_template_basename,
)

di_mock_env_baseline = di_mock_env.copy()
di_mock_env_baseline.update(lzrt_directive=OPT_DIRECTIVE_BASELINE)


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

    cls_filters = dict(txt=FilterManager())

    debug_env = debug_env

    lazy_filename = lazy_filename

    tmp_formatted_data = None

    extension = "txt"

    data = """
somedata
var1
var2
"""

    subject = "<somesubject>"

    def _lazy_write(self, fnp, formatted_data):
        self.tmp_formatted_data = formatted_data

    def setUp(self):
        """not sure why needed, but need to reset the environment
            to make sure mocked values are taken into account
           This is probably due to some too aggressive optimization,
           i.e. we-dont-expect-env-variables to change during a test run
        """

        self.lazy_environ.acquired = False

    def seed(self, exp, extension, suffix=""):
        try:
            try:
                self.assert_exp(exp, extension, suffix=suffix)
            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                pass
            return self.lazytemp.fnp_exp

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def check_naming_convention(self):
        """        
        (under lzrt_template_dirname_exp/lzrt_template_dirname_got directory roots)        
        👇 exp and got files are written to $lzrt_template_dirname_exp, $lzrt_template_dirname_got 
           environment variables
        <root dir exp/got>
        |  👇 the class name is the last directory
        └──TestBasic/
           ├── test_lazymixin.TestBasic.test_001_equal_string.txt
           └── test_lazymixin.TestBasic.test_002_naming_convention.txt
                           👆        👆                         👆 
            the            class name, method name and extension are in the filename


        it is also possible to inject one or more extra parts into the directory, above, the classname
        this is done via the `lazy_dirname_extras` variable which results in an attribute lookup
        on the TestCase instance
        that is inserted into the path

        class MyTestClass:
            lazy_dirname_extras = ["site"]

            def test_site(self):
                self.site = "example.com"
            


        """
        try:
            t_msg = ":%s: not found in :%s:"

            classname = self.__class__.__name__

            for fnp, dir_root in zip(
                [self.lazytemp.fnp_got, self.lazytemp.fnp_exp],
                [lzrt_template_dirname_got, lzrt_template_dirname_exp],
            ):
                self.assertTrue(fnp.endswith(".%s" % (self.extension)))

                self.assertTrue(fnp.startswith(dir_root))

                dirname, fname = os.path.split(fnp)

                if getattr(self, "lazy_dirname_extras", None):
                    li = self._handle_dirname_extras([])

                    li2 = [classname] + [
                        fill_template(tmpl, self, rescuedict) for tmpl in li
                    ]

                    tail = os.path.join(*li2)

                    self.assertTrue(
                        dirname.endswith(tail),
                        "dir %s does end with %s extras/class" % (dirname, tail),
                    )

                    # raise NotImplementedError("%s.check_naming_convention(lazy_dirname_extras)" % (self))

                else:

                    self.assertTrue(
                        dirname.endswith(classname),
                        "dir %s does end with %s class" % (dirname, classname),
                    )

                # class name and method are both in the filename
                for part in [classname, self._testMethodName]:
                    msg = t_msg % (part, fname)
                    self.assertTrue(part in fname, msg)

                for part in [classname]:
                    msg = t_msg % (part, dirname)
                    self.assertTrue(part in dirname, msg)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


def get_subber_for_dirname(self, di_env={}):
    try:

        di_sub = dict(suffix="")
        subber = Subber(
            self,
            di_sub,
            {
                "filename": self.lazy_filename,
                "suffix": "",
                "classname": self.__class__.__name__,
                "exp_got": "exp",
                "extension": "txt",
            },
        )

        self.control = Dummy(env=di_env.copy())

        return subber

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise


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

                    subber = get_subber_for_dirname(self)

                    tdirname = self._lazy_get_t_dirname("exp", subber)

                    # tdirname = self._lazy_get_t_dirname("exp")
                except (ValueError, KeyError) as e:
                    message = str(e)
                    self.assertTrue("dirname" in message)

                # tbasename = self._lazy_get_t_basename("exp")
                # # should default to default
                # self.assertEqual(lzrt_default_t_basename, tbasename)

            finally:
                os.environ = ante

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class TestBasic(LazyMixinBasic, unittest.TestCase):
    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_equal_string(self):
        """sanity check - are we ok if exp == got"""

        try:
            self.seed(self.data, self.extension)
            self.assert_exp(self.data, self.extension)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class TestNamingConventions(LazyMixinBasic, unittest.TestCase):
    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_base_naming_convention(self):

        try:

            self.seed(self.data, self.extension)
            self.assert_exp(self.data, self.extension)
            self.check_naming_convention()

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_002_suffix(self):
        """
        TestBasic/
        └── test_lazymixin.TestBasic.test_003_suffix.mysuffix.txt
                    ends with .suffix.extension      👆 
        """

        suffix = "mysuffix"

        self.seed(self.data, self.extension, suffix=suffix)
        self.assert_exp(self.data, self.extension, suffix=suffix)

        self.check_naming_convention()

        t_msg = ":%s: does not end with :%s:"

        for fnp in [self.lazytemp.fnp_got, self.lazytemp.fnp_exp]:
            _, fname = os.path.split(fnp)
            should_end = ".%s.%s" % (suffix, self.extension)

            msg = t_msg % (fname, should_end)

            self.assertTrue(fname.endswith(should_end), msg)

    @mock.patch.dict(os.environ, di_mock_env)
    def test_003_dirname_extras_list(self):
        """
        
        The intent of `lazy_dirname_extras` is to partition tests by other attributes, like say 
        a site name or a test database name.

        .
        └── TestNamingConventions
            ├── example.com
            │   └── test_lazymixin.TestNamingConventions.test_003_dirname_extras_list.txt

        """

        self.lazy_dirname_extras = ["site"]

        self.site = "example.com"

        self.seed(self.data, self.extension)
        self.assert_exp(self.data, self.extension)

        self.check_naming_convention()

    @mock.patch.dict(os.environ, di_mock_env)
    def test_004_dirname_multiple_string(self):
        """
        .
        └── TestNamingConventions
            ├── example.com
            │   ├── testB
            │   │   └── test_lazymixin.TestNamingConventions.test_004_dirname_multiple_string.txt
        """

        self.lazy_dirname_extras = "site abtest"

        self.site = "example.com"
        self.abtest = "testB"

        self.seed(self.data, self.extension)
        self.assert_exp(self.data, self.extension)

        self.check_naming_convention()


lorem = """
<html><head><title></title></head><body>
<p>Lorem ipsum dolor sit amet, consectetur 
adipisicing elit. Consequatur Quidem, sint incidunt?</p></body></html>
"""


class Test_Error_Handling(LazyMixinBasic, unittest.TestCase):
    """
    if `self.lazytemp.fnp_exp` is not found, that means this is a first time run
    and `got` is written to both `self.lazytemp.fnp_exp` and `self.lazytemp.fnp_got`
    and assert_exp is automatically considered to be successful

    this is also the behavior with $lzrt_directive == "baseline" environment variable
    """

    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_exp_does_not_exist(self):

        try:

            # first time run, so exp does not exist
            self.assert_exp(self.data, self.extension)

            for fnp in [self.lazytemp.fnp_got, self.lazytemp.fnp_exp]:
                with open(fnp) as fi:
                    data = fi.read()
                self.assertEqual(self.data.strip(), data.strip())

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    #

    @mock.patch.dict(os.environ, di_mock_env_baseline)
    def test_002_baseline(self):
        """
        the environment has been mocked to tell lazy to consider the data
        as a baseline:

        - `got` is written to both `self.lazytemp.fnp_exp` and `self.lazytemp.fnp_got`
        - assert_exp is automatically considered to be successful

        """

        try:

            # we are changing the data to go into the seed, i.e. the `exp` side of things
            changed_data = self.data.replace("var2", "var3")

            self.assertFalse(changed_data.strip() == self.data.strip())

            self.seed(changed_data, self.extension)

            for fnp in [self.lazytemp.fnp_got, self.lazytemp.fnp_exp]:
                with open(fnp) as fi:
                    data = fi.read()
                self.assertEqual(changed_data.strip(), data.strip())

            # now we call assert_exp, but the data will be taken as baseline
            self.assert_exp(self.data, self.extension)

            for fnp in [self.lazytemp.fnp_got, self.lazytemp.fnp_exp]:
                with open(fnp) as fi:
                    data = fi.read()
                self.assertEqual(self.data.strip(), data.strip())

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_003_changed_data(self):
        """
        Here the data is changed, but the exp is already seeded and
        lzrt_directive is unset, i.e. it is not 'baseline'
        An assertionError should be thrown
        """

        try:

            # we are changing the data to go into the seed, i.e. the `exp` side of things
            changed_data = self.data.replace("var2", "var3")

            self.assertFalse(changed_data.strip() == self.data.strip())

            self.seed(changed_data, self.extension)

            for fnp in [self.lazytemp.fnp_got, self.lazytemp.fnp_exp]:
                with open(fnp) as fi:
                    data = fi.read()
                self.assertEqual(changed_data.strip(), data.strip())

            # expect an error now
            try:
                self.assert_exp(self.data, self.extension)
                self.fail("should have thrown an AssertionError")
            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                pass

            # it would be nice to re-mock os.environ and with
            # $lzrt_directive=baseline...  that should then pass

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


def debug_expgot(exp, got, testee=None):

    li = ["\n"]
    if testee:
        li.append(str(testee))
    li.append("exp:%s:" % (exp))
    li.append("got:%s:" % (got))

    logger.info("\n  ".join(li))


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

    cls_filters = dict(
        html=[
            FilterDirective(
                "csrf", RegexRemoveSaver("var\s+csrf[a-zA-Z0-9_]+\s+=\s+", "csrf")
            )
        ]
    )

    # _li_remove = [
    #     RegexRemoveSaver("var\ssettings\s=\s", hitname="settings"),
    #     re.compile("var\scsrfmiddlewaretoken\s=\s"),
    # ]

    def format(self, do_filter=True):

        if do_filter:
            exp = []
            for line in self.data.split("\n"):
                if not self.patre_manual_remove.search(line):
                    exp.append(line)

            html = "\n".join(exp)

            res = bs(html).prettify()
            return res

        else:
            res = bs(self.data).prettify()
            return res

        # pdb.set_trace()
        # tmp = bs(res).prettify()
        # self.exp = self.mock_exp = res
        # if rpdb(): # pragma: no cover
        #     pdb.set_trace()
        # if pyver == 3:
        #     self.mock_exp = str.encode(self.exp)

    def setUp(self):

        try:
            if self.__class__ == BaseHtmlFilter:
                return

            super(BaseHtmlFilter, self).setUp()
            self.mock_exp = self.format()

            self.fmt_data = self.format(do_filter=False)

            return
            li_remove = self._li_remove + getattr(self, "li_remove", [])

            self.lazy_filter_html = RemoveTextFilter(
                li_remove, f_notify=self.lazy_filter_notify
            )

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():

                pdb.set_trace()
            raise

    di = di_livetest.copy()

    @mock.patch.dict(os.environ, di)
    def test(self):
        try:
            if self.__class__ == BaseHtmlFilter:
                return

            self.assert_exp(self.fmt_data, extension="html")
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                print("exp:\n%s" % (self.mock_exp))
                print("input:\n%s" % (self.fmt_data))

                print("fnp_exp:%s" % (self.lazytemp.fnp_exp))
                print("fnp_got:%s" % (self.lazytemp.fnp_got))

                print(
                    "\n\nksdiff %s %s\n\n"
                    % (self.lazytemp.fnp_exp, self.lazytemp.fnp_got)
                )

                with open("diff.sh", "w") as fo:
                    fo.write(
                        "ksdiff %s %s\n\n"
                        % (self.lazytemp.fnp_exp, self.lazytemp.fnp_got)
                    )

                # ppp(self)
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

    # li_remove = [CSSRemoveFilter(".nodiff")]

    cls_filters = dict(
        html=FilterDirective("nodiff", CSSRemoveFilter(".nodiff", name="nodiff"))
    )


#################################################################
# Do we still want DiffFormatter?
#################################################################


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
        except (Exception,) as e:  # pragma: no cover
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

        except (Exception,) as e:  # pragma: no cover
            raise


#################################################################


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
        self.assert_exp(got, onIOError=LazyIOErrorCodes.pass_missing)

        # and will pass the 2nd because it was just created
        self.assert_exp(got)

        # and now it should fail
        try:
            got2 = "different"
            self.assert_exp(got2)
            self.fail("should have gotten %s<>%s AssertionError" % (got, got2))
        except (AssertionError,) as e:
            self.assertTrue(got in str(e))
            self.assertTrue(got2 in str(e))
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            self.fail("should have gotten %s<>%s AssertionError" % (got, got2))

    @mock.patch.dict(os.environ, di_livetest)
    def test_002_html(self):
        data = lorem

        self.assert_exp(data, "html", onIOError=LazyIOErrorCodes.pass_missing)

        # and will pass the 2nd because it was just created
        self.assert_exp(data, "html")

    @mock.patch.dict(os.environ, di_livetest)
    def test_003_suffix(self):
        got1 = "<div><span>got1</span></div>"
        got2 = "<div><span>got2</span></div>"

        self.assert_exp(
            got1, "html", onIOError=LazyIOErrorCodes.pass_missing, suffix="suffix1"
        )
        self.assert_exp(
            got2, "html", onIOError=LazyIOErrorCodes.pass_missing, suffix="suffix2"
        )

        self.assert_exp(got1, "html", suffix="suffix1")
        self.assert_exp(got2, "html", suffix="suffix2")

    di = di_livetest.copy()
    # di.update(lzrt_directive=OnAssertionError.baseline)

    @mock.patch.dict(os.environ, di)
    def test_004_baseline(self):

        got = "something"
        got2 = "different"

        # OnAssertionError.baseline suppresses everything...
        self.assert_exp(got)

        with open(self.lazytemp.fnp_exp) as fi:
            self.assertEqual(got, fi.read())

        self.assert_exp(got2)

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
        self.assert_exp(got)

    @mock.patch.dict(os.environ, di_livetest)
    def test_005_rdbname_in_directory(self):
        got = "something"
        got2 = "different"
        db1 = "db1"
        db2 = "db2"

        self.rdbname = db1
        self.assert_exp(got, onIOError=LazyIOErrorCodes.pass_missing)

        self.assertTrue(db1 in self.lazytemp.fnp_exp)
        self.assertTrue(db1 in self.lazytemp.fnp_got)

        # and this should fail with an IOError because it's not the
        # same rdbname so File.exp is missing.
        self.rdbname = db2
        try:
            self.assert_exp(got)
            self.fail("should have gotten %s<>%s AssertionError" % (got, got2))
        except (IOError,) as e:
            logger.info("got my IOError")
            self.assertTrue(db2 in str(e))
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            self.fail("should have gotten %s<>%s AssertionError" % (got, got2))

        # now this should work
        self.rdbname = db1
        self.assert_exp(got)

    @mock.patch.dict(os.environ, di_livetest)
    def test_006_dict(self):
        try:
            data = dict(a=1, b=2, c=3)
            self.assert_exp(data, "json", onIOError=LazyIOErrorCodes.pass_missing)
            data.update(d=4)
            try:
                self.assert_exp(data, "json")
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

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
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

            self.assert_exp(data, "html", onIOError=LazyIOErrorCodes.pass_missing)

            with open(self.lazytemp.fnp_exp) as fi:
                written = fi.read()
            self.assertFalse(ignore in written, written)

            # check what the filter stripped out
            # self.assertTrue(ignore in list(self.lazytemp.filterhits.values())[0].found)

            data = data.replace(ignore, "%s this" % (ignore))

            self.assert_exp(data, "html")

            self.lazy_filter_txt = KeepTextFilter(
                ["a", "b", "c"], f_notify=self.lazy_filter_notify
            )

            data = """a
            a
            b
            d
            """

            self.assert_exp(data, "txt", onIOError=LazyIOErrorCodes.pass_missing)

            with open(self.lazytemp.fnp_exp) as fi:
                written = fi.read()
            self.assertFalse("d" in written)

            data = """a
            a
            b
            e
            """
            self.assert_exp(data, "txt")

            filter_ = KeepTextFilter(["a", "b"])

            self.assert_exp(
                data, "text", onIOError=LazyIOErrorCodes.pass_missing, filter_=filter_
            )
            with open(self.lazytemp.fnp_exp) as fi:
                written = fi.read()

            exp = """a
            a
            b
            """

            self.assertEqual(written.strip(), exp.strip())
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
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

            temp = self.assert_exp(
                data, "html", onIOError=LazyIOErrorCodes.pass_missing
            )

            self.assertTrue(
                self.lazytemp.filterhits["settings"][0].found.startswith("var settings")
            )

            with open(self.lazytemp.fnp_exp) as fi:
                written = fi.read()

            self.assertFalse("csrf" in written, written)
            self.assertFalse("var settings" in written, written)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_livetest)
    def test_010_unequal_string(self):

        try:

            exp = "foo"
            got = exp + ".unexpected"

            self.assert_exp(exp, onIOError=LazyIOErrorCodes.pass_missing)
            try:
                self.assert_exp(got)
            except (AssertionError,) as e:
                pass
            else:
                self.fail("should have failed")

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
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


@unittest.skipUnless(False, "v2 049.lazy.026.lazy3")
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

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
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

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            logger.info(msg)
            logger.error(str(e))
            if cpdb():
                pdb.set_trace()
            raise


class TestFilters_Absent(TestFilters):

    matchers = ["xcsrf", "xsysdate"]
    _data = dict(csrf="skip.csrf", sysdate="skip.sysdate", keep1="keep1", keep2="keep2")


if __name__ == "__main__":

    cpdb = set_cpdb()
    rpdb = set_rpdb()
    rc = 0
    try:
        rc = unittest.main()
    finally:
        with open("./diff.sh", "w") as fo:
            msg = "ksdiff %s %s\n" % (
                lzrt_template_dirname_exp,
                lzrt_template_dirname_got,
            )
            print("\n\n\n", msg)
            fo.write(msg)
        sys.exit(rc)
