# -*- coding: utf-8 -*-
"""
test lazy-regression-tests
"""

import sys
import os

import unittest

try:
    import unittest.mock as mock
except (ImportError,) as ei:
    import mock  # python 2?

import json
import tempfile


import re


# pylint: disable=unused-import
#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
)
from bemyerp.pssystem.typing_ import T_options

# if TYPE_CHECKING:
#    from bemyerp.xxx import yyy

#######################################################
# pylint: enable=unused-import


verbose = "-v" in sys.argv


# pylint: disable=attribute-defined-outside-init

# pylint: disable=missing-function-docstring,missing-class-docstring  #🧨🧨🧨🧨 turn this back on later 🧨🧨🧨🧨

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
    set_breakpoints3,
    InvalidConfigurationException,
)

from lazy_regression_tests.lazy3 import DictValidator, ValidationDirective


from lazy_regression_tests.lazy3.filters import (
    RegexRemoveSaver,
    DictFilter,
    FilterDirective,
    FilterManager,
    JsonFilterManager,
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


def debug_env(self):
    ppp(self.lazy_environ, "lazyenv")


# pylint: disable=no-member
class LazyMixinBasic(LazyMixin):

    """
    basic support functionality for the rest of the tests
    similar in fact to how LazyMixin is normally used.

    """

    cls_filters = dict(txt=FilterManager())

    debug_env = debug_env

    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)

    tmp_formatted_data = None

    extension = "txt"

    data = """
somedata
var1
var2
"""

    def setUp(self):
        """not sure why needed, but need to reset the environment
            to make sure mocked values are taken into account
           This is probably due to some too aggressive optimization,
           i.e. we-dont-expect-env-variables to change during a test run
        """

        self.lazy_environ.acquired = False

    def seed(self, exp, extension=None, suffix=""):
        try:
            try:

                extension = extension or self.extension

                self.assert_exp(exp, extension=extension, suffix=suffix)
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


        It is also possible to inject one or more extra parts into the directory,
        above, the classname this is done via the `lazy_dirname_extras` 
        variable which results in an attribute lookup on the TestCase instance
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


# pylint: enable=no-member


def get_subber_for_dirname(self, di_env: Optional[dict] = None):
    try:

        di_env = di_env or {}

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


filtername23 = "var2and3"

filter_23 = FilterDirective(filtername23, RegexRemoveSaver("var2|var3", "var2and3"))

filtername1 = "var1"

filter_1 = FilterDirective(filtername1, RegexRemoveSaver("var1", "var1"))


class Test_Text_Filtering(LazyMixinBasic, unittest.TestCase):
    """
    filters are additive through a class's mro
    """

    filtername = filtername23

    cls_filters = dict(txt=filter_23)

    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_filter(self):
        try:

            changed_data = self.data.replace("var2", "var3")

            li_change = ["var2", "var3"]

            fnp_exp = self.seed(changed_data, self.extension)

            # test that lines matching the filter are removed from the file
            with open(fnp_exp) as fi:
                data = fi.read()

            for text in li_change:
                self.assertFalse(
                    text in data,
                    "%s should have been stripped out of %s" % (text, data),
                )

            # but the filtered data is still accessible through the filtered dictionary
            tmp = self.lazytemp
            # this is the value originally passed into seed
            self.assertEqual(tmp.filtered[self.filtername], ["var3"])

            # tmp is reset on each new instance but we are still on the same instance after seed
            # by default the filter results are put in a list
            tmp.filtered[self.filtername] = []

            tmp = self.assert_exp(self.data, self.extension)

            with open(tmp.fnp_got) as fi:
                data = fi.read()

            for text in li_change:
                self.assertFalse(
                    text in data,
                    "%s should have been stripped out of %s" % (text, data),
                )

            # this the unchanged value in self.data
            self.assertEqual(tmp.filtered[self.filtername], ["var2"])

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_002_filter_scalar(self):
        """
        instead of the standard, list-appending filtering we want to have a scalar result
        to do this we can modify the filter
        """

        try:

            scalar_filter = RegexRemoveSaver("var2|var3", "var2and3", scalar=True)

            # we can modify a filter if we know its name
            self.filters[self.extension].set_filter(
                self.filtername, filter_=scalar_filter
            )

            # did we change the filter?
            newfilter = self.filters[self.extension].filters[self.filtername].filter_

            self.assertTrue(scalar_filter is newfilter)

            # and it should be a scalar
            self.assertEqual(True, newfilter.scalar)

            changed_data = self.data.replace("var2", "var3")

            li_change = ["var2", "var3"]

            fnp_exp = self.seed(changed_data, self.extension)

            # test that lines matching the filter are removed from the file
            with open(fnp_exp) as fi:
                data = fi.read()

            for text in li_change:
                self.assertFalse(
                    text in data,
                    "%s should have been stripped out of %s" % (text, data),
                )

            # but the filtered data is still accessible through the filtered dictionary
            tmp = self.lazytemp

            # this is the value originally passed into seed, as a scalar
            self.assertEqual(tmp.filtered[self.filtername], "var3")

            tmp = self.assert_exp(self.data, self.extension)

            with open(tmp.fnp_got) as fi:
                data = fi.read()

            for text in li_change:
                self.assertFalse(
                    text in data,
                    "%s should have been stripped out of %s" % (text, data),
                )

            # this the unchanged value in self.data
            self.assertEqual(tmp.filtered[self.filtername], "var2")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


#################################################################
# Test MRO-based additive filtering
# filters go from most-generic to most-specific, with named filter
# overriding precedings settings.
#################################################################


class AnyName:
    cls_filters = dict(txt=filter_23)


class AnotherName:
    cls_filters = dict(txt=filter_1)


class Test_Additive_Filtering(AnyName, AnotherName, LazyMixinBasic, unittest.TestCase):
    def change_data(self, data):
        li_change = ["var1", "var2", "var3"]

        changed_data = data
        for value in li_change:
            changed_data = changed_data.replace(value, "%sxxx" % (value))

        return changed_data

    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_everything_filteredout(self):
        try:

            changed_data = self.change_data(self.data)
            self.seed(changed_data, self.extension)

            self.assert_exp(self.data, self.extension)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_002_deactivated_filter_fail(self):
        try:

            changed_data = self.change_data(self.data)

            self.filters[self.extension].set_filter(filtername1, active=False)
            self.seed(changed_data, self.extension)

            try:
                self.assert_exp(self.data, self.extension)
                self.fail("should have failed on var1 difference")
            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                self.assertTrue("var1" in str(e))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_003_bad_activation(self):
        """
        you cant activate a filter that doesn't exist
        the error happens when assert_exp is called and filtering is attempted
        this supports the scenario where:

        # we know we need to filter out changing data, but we let the subclasses
        # decide how to do it
        cls_filters = dict(txt, FilterDirective("changing",active=True))

        #
        cls_filters = dict(txt, FilterDirective("changing",filter_=<some filter>))


        """
        try:

            # dont care so much if you try to deactivate a filter that doesnt exist
            self.filters[self.extension].set_filter("xyz", active=True)

            try:

                self.assert_exp(self.data, self.extension)
                self.fail("should have failed on due to xyz filter not existing")

            # pragma: no cover pylint: disable=unused-variable
            except (InvalidConfigurationException,) as e:
                self.assertTrue("xyz" in str(e))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_004_tolerate_bad_deactivation(self):
        """
        you can deactivate a filter that has not been set
        """
        try:

            # dont care so much if you try to deactivate a filter that doesnt exist
            self.filters[self.extension].set_filter("xxx", active=False)
            self.assert_exp(self.data, self.extension)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class BaseForJson:

    cls_filters = dict(json=JsonFilterManager())

    j_data = dict(
        var1=1,
        var2=dict(var21=21, var22=22, var23=dict(var231=231)),
        var3=3,
        var4=4,
        someval="xyz",
    )


class Test_JSON(BaseForJson, LazyMixinBasic, unittest.TestCase):

    extension = "json"

    def setUp(self):
        self.j_data = self.j_data.copy()
        self.lazy_environ.acquired = False

    @mock.patch.dict(os.environ, di_mock_env)
    def test_001_same(self):
        """sanity check"""
        try:
            self.seed(self.j_data, self.extension)
            self.assert_exp(self.j_data, self.extension)
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    changes = dict(var1="one")

    def change_data(self, changes=None):

        changes = changes or self.changes.copy()

        j_data = self.j_data.copy()
        j_data.update(**changes)
        return j_data

    @mock.patch.dict(os.environ, di_mock_env)
    def test_002_changes(self):
        """sanity check"""
        try:
            changed_data = self.change_data()
            self.seed(changed_data, self.extension)
            try:
                self.assert_exp(self.j_data, self.extension)
                self.fail("should have changed on %s" % (self.changes))

            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                # pdb.set_trace()
                self.assertTrue("var1" in str(e))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_JSON_DictFilter(Test_JSON):

    """
    a DictFilter is a way modify incoming data and takes a dictionary of its own
    as a specifier

    #anything found in a matching location with None is just taken out.
    var1=None

    #and a dictionary value recurses
    var2=dict(var22=None)

    """

    di_varying = dict(var1=None, var2=dict(var22=None))

    cls_filters = dict(
        json=FilterDirective("changing", DictFilter(di_varying, "changing"))
    )

    @mock.patch.dict(os.environ, di_mock_env)
    def test_002_changes(self):
        """sanity check"""
        try:

            changed_data = self.change_data()
            changed_data["var2"]["var22"] = "changed"

            fnp_exp = self.seed(changed_data, self.extension)
            with open(fnp_exp) as fi:
                data = fi.read()

            # should still be there...
            s_unwanted = {"var1", "var22"}

            s_wanted = set(self.j_data.keys()) - s_unwanted

            for key in s_wanted:
                self.assertTrue(key in data)

            for key in s_unwanted:
                self.assertFalse(key in data)

            self.assert_exp(self.j_data, self.extension)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    @mock.patch.dict(os.environ, di_mock_env)
    def test_003_text_stillworks(self):
        """
        `assert_exp` is built around extensions, on purpose.  
        You can run tests on several data formats.
        """

        try:

            fnp_exp = self.seed(self.j_data, self.extension)
            self.check_naming_convention()

            self.assert_exp(self.j_data, self.extension)

            fnp_exp = self.seed(self.data, "txt")
            self.assertTrue(fnp_exp.endswith(".txt"))
            self.assert_exp(self.data, "txt")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                ppp(di_debug, "\ndebug")
                pdb.set_trace()
            raise


class CustomDictValidator(DictValidator):
    """  let's write our own

         for keys prefixed with `<selector>`, 'var' in this example 
         check that value ends with what comes after the prefix
         numeric if applicable

         var2 : 2 ✅
         var3 : 5 ❌
         varfoo : "foo" ✅
    """

    def check(self, name: str, testee: "LazyMixin", exp: Any, sources: dict):
        """

        """

        try:
            source_ = self.get_source(testee, **sources)
            got = self.get_value(source_)

            for key, value in got:

                expvalue = key.split(self.selector)[1]
                try:
                    expvalue = int(expvalue)
                # pragma: no cover pylint: disable=unused-variable
                except (ValueError,) as e:
                    pass

                testee.assertEqual(expvalue, value)

        except (AssertionError,) as e:  # pragma: no cover
            raise
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def get_value(self, source, res=None):
        """ we are getting a dict and we recurse into 
            because this is what this validator wants to do
            we could have used any number of data selection
            strategies
        """
        try:
            if res is None:
                res = []
            for key, value in source.items():
                if key.startswith(self.selector):
                    if isinstance(value, dict):
                        self.get_value(value, res)
                    else:
                        res.append((key, value))
            return res
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Test_JSON_Validation(BaseForJson, LazyMixinBasic, unittest.TestCase):

    cls_validators = [
        ValidationDirective("var3", DictValidator("var3"), exp=3),
        ValidationDirective("nested", DictValidator("var2.var23.var231"), exp=231),
    ]

    def test_001_expects(self):
        try:
            self.check_expectations(data=self.j_data)
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def test_002_fail231(self):
        try:
            self.set_expectation("nested", exp=232)
            try:
                self.check_expectations(data=self.j_data)
                self.fail("should have errored 231<>232")
            except (AssertionError,) as e:
                self.assertTrue("232" in str(e) and "231" in str(e))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def test_003_add_expected_fail(self):
        try:
            self.set_expectation(
                ValidationDirective("var22", DictValidator("var22"), exp=23)
            )
            try:
                self.check_expectations(data=self.j_data)
                self.fail("should have errored 22<>23")
            except (AssertionError,) as e:
                self.assertTrue("22" in str(e) and "23" in str(e))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def test_004_custom(self):
        try:
            self.set_expectation(
                "custom", validator=CustomDictValidator("var"), exp="N/A", active=True
            )
            self.check_expectations(data=self.j_data)

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


if __name__ == "__main__":

    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints
    rc = 0

    tmpl_source = """
alias _lcdgot=1
alias _lcdexp=2
alias _ldiffexpgot=3

unalias _lcdgot
unalias _lcdexp
unalias _ldiffexpgot
alias _lcdexp='cd %(lzrt_template_dirname_exp)s'
alias _lcdgot='cd %(lzrt_template_dirname_got)s'
alias _ldiffexpgot='ksdiff %(lzrt_template_dirname_exp)s %(lzrt_template_dirname_got)s'
"""

    try:
        rc = unittest.main()
    finally:
        with open("/Users/jluc/kds2/wk/bin/lsource.sh", "w") as fo:

            fo.write(
                fill_template(
                    tmpl_source,
                    dict(
                        lzrt_template_dirname_exp=lzrt_template_dirname_exp,
                        lzrt_template_dirname_got=lzrt_template_dirname_got,
                    ),
                )
            )

        sys.exit(rc)
