""" basic test """
# -*- coding: utf-8 -*-
import os
import sys
import re
import unittest
from typing import Dict
from pathlib import Path
from operator import itemgetter

#################################################################
# Dependencies
#################################################################


import pytest
import pydantic


# disable noisy linting...
# the classes like Top, Level2, Level3... look unused, they are not
# pylint: disable=unused-variable,unused-import,c-extension-no-member,superfluous-parens
# pylint: disable=possibly-unused-variable,no-member


from lazy_regression_tests.utils import (
    set_cpdb,
    set_rpdb,
    set_breakpoints3,
    ppp,
    disable_cpdb,
    force_verbose
)


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

if __name__ == "__main__":
    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints

from lazy_regression_tests.core_assist2 import (
    _LazyMeta,
    Filter,
    FilterMgr,
    LazyMixin,
    Checker,
)
from lazy_regression_tests.filters import DictFilter

# from lazy_tstmixin import TstMixin
import lazy_regression_tests.core_assist2 as core_assist2
import lazy_regression_tests.validators as validators

import lazy_regression_tests.validators_http as validators_http
import lazy_regression_tests.common as common


from lazy_regression_tests.common import (
    parse_pydantic_validation_error,
    ConfigurationException,
    ValidationError,
    ExtAlias,
    Auto,
)
from lazy_regression_tests.tests.helper_tst import (
    TData,
    TstMixinSeeder,
    get_fake_response_from_html,
    TstMixin,
    check_keep,
)


# environment control of certain tests
do_test_json = os.getenv("do_test_json")
do_test_badfunc = os.getenv("do_test_badfunc")
do_test_validator = os.getenv("do_test_validator")
do_test_valstacking = os.getenv("do_test_valstacking")
do_test_fail = os.getenv("do_test_fail")

IS_PYTEST = sys.argv[0].endswith("pytest")

BAD_NONE = "none is not an allowed value"

LAZY_FILENAME = Path(__file__).stem

ext_alias_json = ExtAlias(alias="json")


class Base(TstMixin, TstMixinSeeder, unittest.TestCase):
    "pin any common functionality you need here"

    lazy_filename = LAZY_FILENAME

    def gen_test_classes(self) -> Dict[str, type]:
        """generate classes using LazyMeta gets tested"""
        try:

            class Top(metaclass=_LazyMeta):
                "testing"
                cls_filters = dict(txt=["abc", "def"])
                lazy_filename = self.lazy_filename

            class Level2(Top):
                "testing"

            class Level3(Level2):
                "testing"
                cls_filters = dict(
                    txt=[
                        "abc",
                        "ghi",
                        Filter(f="def", active=False),
                        dict(f="ghi", invert=1),
                    ]
                )

            class Level4(Top):
                "testing"
                cls_filters = dict(txt=[dict(f="ghi", invert=1), dict(f=len, invert=1)])

            class DirectTop(Top):
                "testing no cls_filters"
                cls_filters = dict(txt="qqq")

            class Named(Top):
                "testing"
                cls_filters = dict(txt=dict(f="ghi", name="named_ghi"))

            class NoList(metaclass=_LazyMeta):
                "testing no single-item filter"
                cls_filters = dict(txt="qqq")

            classes = self.get_classes_oi(locals())
            return {cls_.__name__: cls_ for cls_ in classes}

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class Test_Dict(Base):
    """test dict filtering with text representation"""

    def gen_test_classes(self) -> Dict[str, FilterMgr]:
        """generate classes using LazyMeta gets tested"""
        try:

            class Dico(metaclass=_LazyMeta):
                "testing"
                cls_filters = dict(dict=DictFilter(f=dict(skip_21=None, skip_22=None)))

                lazy_filename = self.lazy_filename

            class Top(metaclass=_LazyMeta):
                "testing"
                cls_filters = dict(txt=["abc", "def"])

            classes = self.get_classes_oi(locals())
            for cls in classes:
                cls._testMethodName = self._testMethodName

            res = {cls_.__name__: cls_ for cls_ in classes}
            return res

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    input1 = dict(
        skip_21=1, skip_22=2, c=3, pass_31="a", comp=dict(c1="c1", c2=200, c3="foo")
    )

    classnameoi = "Dico"
    ext = "dict"

    @unittest.skipUnless(*check_keep("json"))
    @unittest.skipUnless(
        not IS_PYTEST, "test is unreliable under pytest and fails with truncated output"
    )
    def test_same(self):
        try:

            if sys.argv[0].endswith("pytest"):
                print("skip test with pytest")
                return

            di_cls = self.gen_test_classes()
            self.cls_tst = di_cls[self.classnameoi]
            self.cls_tst._testMethodName = self._testMethodName
            testee = self.cls_tst()

            data = self.input1.copy()

            lz = testee.lz
            checker = getattr(lz, self.ext, None)
            if not checker:
                print(f"{self} {testee=}.lz has no {self.ext}")
                return

            self.seed(data, checker=checker, testee=testee)
            data["skip21"] = "?"
            checker.assert_same(data)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    @unittest.skipUnless(*check_keep("json"))
    def test_filter(self):
        "test filtering"
        try:

            di_gen = self.gen_test_classes()

            clsoi = di_gen[self.classnameoi]

            testee = clsoi()

            input_ = self.input1.copy()

            di_exp = {k: v for k, v in input_.items() if not k.startswith("skip")}

            checker = getattr(testee.lz, self.ext)

            filter_: FilterMgr = checker.f

            s_got = filter_(input_)

            s_exp = checker.provider.datain_to_str(di_exp, checker=checker)
            self.assertEqual(s_exp, s_got)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_named(self):
        "test named filters and their filtered temp results"
        try:

            di_gen = self.gen_test_classes()
            clsoi = di_gen[self.classnameoi]
            testee = clsoi()
            checker: Checker = getattr(testee.lz, self.ext)

            filter_: FilterMgr = checker.f

            nameoi = "named_filter"

            checker.filters[0].name = nameoi
            self.assertIs(checker.filters[0], checker.f.named_filters[nameoi])

            input_ = self.input1.copy()
            b_input = input_.copy()

            di_exp = {k: v for k, v in input_.items() if not k.startswith("skip")}
            s_got = filter_(input_)

            s_exp = checker.provider.datain_to_str(di_exp, checker)
            self.assertEqual(s_exp, s_got)
            self.assertTrue(checker.temp)
            tmp = checker.temp

            li_filt = tmp.filtered[nameoi]
            self.assertTrue(li_filt)
            for di in li_filt:
                for key in di.keys():
                    self.assertTrue(key.startswith("skip"))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class Test_Json(Test_Dict):
    """test dict filtering with json extensions"""

    ext = "json"

    def gen_test_classes(self) -> Dict[str, FilterMgr]:
        """generate classes using LazyMeta gets tested"""
        try:

            class Dico(metaclass=_LazyMeta):
                "testing"
                cls_filters = dict(json=DictFilter(f=dict(skip_21=None, skip_22=None)))
                lazy_filename = self.lazy_filename

            class Top(metaclass=_LazyMeta):
                "testing"
                cls_filters = dict(txt=["abc", "def"])
                lazy_filename = self.lazy_filename

            classes = self.get_classes_oi(locals())

            res = {cls_.__name__: cls_ for cls_ in classes}

            return res

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class Test_InvertActivate(Base):
    """used to test command line runs"""

    text1 = """
abc
def 
ghik
klm
abcdefxx
xabeca

careamouseghidef
"""

    ext = "txt"

    def test_bad_func(self):
        """testing if a direct pass to filters fails if the function
        signature doesnt match f(x:any):truthy
        """
        try:

            def bad_func(a: str, b: str) -> bool:
                """this should fail Filter validation"""
                return True

            try:

                with disable_cpdb():

                    with pytest.raises(
                        (
                            ConfigurationException,
                            pydantic.ValidationError,
                        )
                    ):

                        class Bad(metaclass=_LazyMeta):
                            """this should fail Filter validation"""

                            cls_filters = dict(txt=[dict(f=bad_func)])

                # self.fail(f"shoulda failed. bad function signature {bad_func}")
            # pragma: no cover pylint: disable=unused-variable
            except (ValueError, pydantic.ValidationError) as e:
                pass

            def bad_func2(a: str) -> dict:
                """this should fail Filter validation"""
                return {}

            try:

                with disable_cpdb() as con:
                    with pytest.raises(ConfigurationException):

                        class Bad2(metaclass=_LazyMeta):
                            """this should fail Filter validation"""

                            cls_filters = dict(txt=[dict(f=bad_func)])

            # pragma: no cover pylint: disable=unused-variable
            except (pydantic.ValidationError,) as e:
                pass
            except (ValueError,) as e:
                self.assertTrue("expecting" in str(e))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_filter(self):
        """test basic filtering up and down hierarchy"""
        try:

            di_gen = self.gen_test_classes()

            clsoi = di_gen["Top"]

            exp = self.get_filter_exp(
                self.text1, lambda line: ("abc" in line or "def" in line)
            )

            testee = clsoi()

            got = testee.lz.txt.f(self.text1)

            self.assertFalse("abc" in got)
            self.assertFalse("def" in got)
            self.assertTrue("ghi" in got)

            self.assertEqual(exp, got)

            # and a direct descendant of Top, no alterations to cls_filters, should work just like it.
            testee2 = di_gen["DirectTop"]()

            got = testee2.lz.txt.f(self.text1)
            self.assertEqual(exp, got)

            clsoi = di_gen["Level3"]
            testee = clsoi()

            got = testee.lz.txt.f(self.text1)

            exp = self.get_filter_exp(
                self.text1, lambda line: ("abc" in line) or not ("ghi" in line)
            )

            self.assertEqual(exp, got)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_named(self):
        """test name filters and filter tracking"""
        try:
            di_gen = self.gen_test_classes()
            clsoi = di_gen["Named"]

            exp = self.get_filter_exp(
                self.text1, lambda line: ("abc" in line) or not ("ghi" in line)
            )

            testee = clsoi()

            checker = testee.lz.txt

            got = checker.f(self.text1)

            filtereds = checker.temp.filtered["named_ghi"]
            for filtered in filtereds:
                self.assertTrue("ghi" in filtered)

            self.assertFalse("ghi" in got)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_it(self):
        """test inversions and activations as well as verbosity"""
        try:
            ori = core_assist2.verbose
            core_assist2.verbose = True

            class Top(metaclass=_LazyMeta):
                "testing"
                cls_filters = dict(txt=["abc", "def"])

            class NoFilter(Top):
                "testing"

            class Final(NoFilter):
                "testing"
                cls_filters = dict(
                    txt=[
                        "abc",
                        "ghi",
                        Filter(f="def", active=False),
                        dict(f="ghi", invert=1),
                    ]
                )

            self.assert_filter_exp(Top, "txt", "regex.def", dict(active=True))
            self.assert_filter_exp(Final, "txt", "regex.def", dict(active=False))
            self.assert_filter_exp(
                Final, "txt", "regex.ghi", dict(active=True, invert=True)
            )
            core_assist2.verbose = ori

        # pragma: no cover
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class Test_LazyRoot(Base):
    "testing LazyRoot behavior"

    def test_lazyroot(self):
        """test LazyRoot functionality"""
        try:
            # don't need to assume too much about the internals of core_assist
            # so lets keep this import limited to the test
            # pylint: disable=import-outside-toplevel
            from lazy_regression_tests.core_assist2 import LazyRoot

            classes = self.gen_test_classes()

            clsoi: LazyMixin = classes["Named"]

            lz: LazyRoot = clsoi.lz

            mgr = lz.txt

            self.assertIsInstance(mgr.f, FilterMgr)

            # check you can deep copy
            inst_root = lz.clone()
            self.assertEqual(inst_root.txt.ext, lz.txt.ext)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class Test_Actual(unittest.TestCase):
    """test "actual behavior" of a unitest.TestCase instance"""

    ext = "txt"
    test_funcs = ["abcdef"]

    def test_direct_tstcase(self):
        """check that instance-level stuff works"""
        try:

            class Tester(unittest.TestCase, metaclass=_LazyMeta):
                "check unittest functionality"
                cls_filters = {self.ext: self.test_funcs}

                def test_bad(self):
                    "check unittest functionality"
                    self.fail("baaaddd...")

                def test_good(self):
                    "check unittest functionality"
                    self.assertEqual(1, 1)

            tester = Tester()

            try:
                tester.test_bad()
                self.fail("Tester.test_bad() should have failed on ")
            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                pass

            tester.test_good()

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class BaseValidatorTst(Base):
    """set up base testing behavior
    - create classes dynamically
    - sets the default classname of interest
    """

    classnameoi = "Top"

    def gen_test_classes(self) -> Dict[str, type]:
        """generate classes using LazyMeta that can be tested"""
        try:

            class Top(metaclass=_LazyMeta):
                "testing"
                cls_filters = dict(txt=["abc", "def"])

            class TopVal(unittest.TestCase, Top):
                """test validator setup"""

                cls_validators = dict(
                    txt=[
                        dict(name="abc_in_data", v=lambda x: "abc" in x, selector=Auto)
                    ],
                    dict=[
                        dict(name="abc_in_data", v=lambda x: "abc" in x, selector=Auto)
                    ],
                )

            classes = self.get_classes_oi(locals())
            return {cls_.__name__: cls_ for cls_ in classes}

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class Test_Validator(BaseValidatorTst):
    """testing validations"""

    classnameoi = "TopVal"

    def test_mgr_nesting(self):
        """test class getting managers"""
        try:

            class TopVal(metaclass=_LazyMeta):
                """test validator setup"""

                cls_validators = dict(
                    txt=[
                        dict(
                            name="abc_in_data", v=lambda x: "abc" in x, selector="data"
                        )
                    ]
                )

            val1 = validators.Validator(
                name="val1",
                selector=validators.Selectors.name,
                v=validators.check_equal,
                exp="value1",
            )
            valmgr = validators.ValidatorMgr(ext="txt", validators=[val1])

            class Level2(TopVal):
                cls_validators = dict(txt=[valmgr], dict=[valmgr])

            class Level3(Level2):
                cls_validators = dict(
                    txt=[
                        dict(
                            name="val2",
                            exp=2,
                            v=validators.check_equal,
                            selector=validators.Selectors.name,
                        )
                    ]
                )

            data = TData(val1="value1", val2=2, data="abcd")
            testee = Level3()

            checker = testee.lz.dict

            lvalidators = checker.validators

            checker.v(data)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    @unittest.skipUnless(*check_keep("check_validator"))
    def test_basics(self):
        "test validators"
        try:
            testee = None

            di_gen = self.gen_test_classes()

            clsoi = di_gen[self.classnameoi]

            lz = clsoi.lz
            txt = lz.txt

            in_ = "xyz"
            got = txt.f(in_)
            self.assertEqual(in_, got)

            in_ = "abc"
            got = txt.f(in_)
            self.assertFalse(got)

            try:
                with disable_cpdb() as con:
                    missing = lz.missing
                    self.fail("`missing` should fail AttributeError")
            except (AttributeError,) as e:
                pass

            validator = lz.txt.v

            testee = clsoi()
            # testee.lz.txt.v.testee = testee

            try:
                data = "addxc"
                with disable_cpdb():
                    testee.lz.txt.v(data)
                self.fail(f"abc presence test shoulda failed on {data}")
            except (AssertionError,) as e:
                if verbose:
                    print(f"✅{self}.expected error: {e}")

            data = "abcd"
            v = testee.lz.txt.v
            v(data)

            data = TData(data="abc")

            checker = testee.lz.dict

            checker.validators["abc_in_data"].selector = "data"
            checker.v(data)

            checker.validators["abc_in_data"].selector = "data"

            data2 = dict(data="abcdef")

            checker.v(data2)

            checker.validators["abc_in_data"].selector = itemgetter("data")
            checker.v(data2)

            checker.validators["abc_in_data"].selector = ""
            try:
                with disable_cpdb():
                    checker.v(data2)
                self.fail(f"abc presence test shoulda failed on {data2}")
            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                if verbose:
                    print(f"✅{self}.expected error: {e}")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if testee:
                testee.lz.show()
            if cpdb():
                breakpoint()
            raise

    def test_dynamic(self):
        """more testing of dynamic class behavior"""
        try:
            di_gen = self.gen_test_classes()

            clsoi = di_gen[self.classnameoi]

            valname = "abc_in_data"

            class DynTest(clsoi):
                "check that you can build a class dynamically once more"
                cls_validators = dict(txt=[dict(name=valname, active=False)])

            self.assertTrue(DynTest.lz.txt.v)

            self.assertFalse(DynTest.lz.txt.validators[valname].active)

            testee = DynTest()

            self.assertFalse(testee.lz.txt.validators[valname].active)

            self.assertTrue(isinstance(testee, LazyMixin))

            self.assertTrue(testee.lz.txt.v.testee)

            testee.lz.txt.v("xxx")

            testee.lz.txt.validators["abc_in_data"].active = True

            raiser = getattr(self, "fail", AssertionError)

            try:
                with disable_cpdb():
                    testee.lz.txt.v("xxx")
                    raiser("abc presence validator has no validation function")
            except (AssertionError) as e:
                if verbose:
                    print(f"✅{self}.expected error: {e}")

            validator = testee.lz.txt.validators["abc_in_data"]

            validator.active = True

            validator.v = lambda x: "abc" in x

            try:
                with disable_cpdb():
                    testee.lz.txt.v("xxx")
            except (AssertionError,) as e:
                if verbose:
                    print(f"✅{self}.expected error: {e}")

            testee.lz.txt.v("xabcd")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    @unittest.skipUnless(*check_keep("tdata_html"))
    def test_val_checkers(self):
        """test some default validation functions"""
        try:

            valstatus = validators.Validator(
                name="status_code", selector=validators.Selectors.name
            )

            class TstBase(unittest.TestCase, metaclass=_LazyMeta):
                """we know we want to test a status code"""

                # status_code = 200
                cls_validators = dict(yaml=[valstatus])

            missing_validator = TstBase()
            missing_validator.status_code = 500
            foob = TData(status_code=200)

            checker = missing_validator.lz.yaml

            with disable_cpdb() as disabled:
                # with disable_cpdb() as disabled:
                with pytest.raises(
                    (ValidationError, pydantic.ValidationError)
                ):
                    # we expect an error because there is no validation function
                    checker.v(foob)

            # now we disable the test
            checker.validators["status_code"].active = False
            checker.v(foob)

            # reactivate the validator, set to check Validator.exp == data
            checker.validators["status_code"].active = True
            # checker.validators["status_code"].v = validators.check_equal

            with disable_cpdb() as disabled:
                with pytest.raises((AssertionError, ConfigurationException)):
                    # we expect an error we did not set exp, so it is None
                    checker.v(foob)

            checker.validators["status_code"].exp = 200
            checker.v(foob)

            # change to an expected set/list/tuple...
            checker.validators["status_code"].exp = (200, 302)
            checker.validators["status_code"].v = validators.check_in
            checker.v(foob)

            foo404 = get_fake_response_from_html(
                status=404, content_type="application/json"
            )
            with disable_cpdb() as disabled:
                with pytest.raises(AssertionError):
                    checker.v(foo404)

            foo404badtype = TData(status_code="404")

            with force_verbose(validators):
                with disable_cpdb() as disabled:
                    with pytest.raises(AssertionError):
                        checker.v(foo404badtype)

            checker.validators["status_code"].v = validators.check_not_in
            checker.v(foo404)

            # intentional missspelling
            response_missing_field = TData(statuscode=404)

            with pytest.raises(validators.ConfigurationException):
                checker.v(response_missing_field)

            with pytest.raises(validators.ConfigurationException):
                checker.v(dict(statuscode=404))

            checker.v(dict(status_code=404))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    @unittest.skipUnless(*check_keep("tdata_html"))
    def test_val_exp(self):
        """ """
        try:

            def equality_check(data, validator):
                try:
                    return validator.exp == data
                # pragma: no cover pylint: disable=unused-variable
                except (Exception,) as e:
                    if cpdb():
                        breakpoint()
                    raise

            valstatus = validators.Validator(
                name="status_code", v=equality_check, selector=validators.Selectors.name
            )

            class TstBase(metaclass=_LazyMeta):
                """we know we want to test a status code"""

                cls_validators = dict(html=[valstatus])

            ok = 200

            class TstOK(TstBase):
                "and now we expect status_code=200"
                cls_validators = dict(html=[dict(name="status_code", exp=ok)])

            self.assertEqual(ok, TstOK.lz.html.validators["status_code"].exp)

            testee = TstOK()
            checker = testee.lz.html

            response = get_fake_response_from_html(status=404)
            try:
                with disable_cpdb():
                    checker.v(response)
                raise AssertionError("shoulda failed on 404")
            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                pass

            response = get_fake_response_from_html()
            checker.v(response)

            valname = "status_code"

            class TstOKEqual(metaclass=_LazyMeta):
                # class TstOK(TstBase, unittest.TestCase):
                cls_validators = dict(
                    html=[
                        dict(
                            name=valname,
                            exp=200,
                            v=validators.check_equal,
                            selector="status_code",
                        )
                    ]
                )

            testee_equal = TstOKEqual()

            checker_cls = TstOKEqual.lz.html

            checker = testee_equal.lz.html

            v_cls = checker_cls.validators[valname]
            v_inst = checker.validators[valname]

            self.assertIsNot(v_cls, v_inst)
            self.assertEqual(v_cls.dict(), v_inst.dict())

            foo2 = get_fake_response_from_html(status=200)
            checker.v(foo2)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    @unittest.skipUnless(*check_keep("still_bad"))
    def test_val_regex(self):
        """regex validations"""
        try:

            patre = re.compile("abc")

            valtitle = validators.Validator(
                name="title", v=patre.search, selector="title"
            )

            class TstDirect(metaclass=_LazyMeta):
                """we know we want to test a status code"""

                cls_validators = dict(html=[valtitle])

            data = get_fake_response_from_html(title="xabcd")

            testee = TstDirect()
            checker = testee.lz.html
            checker.v(data)

            data = get_fake_response_from_html(title="xyz")

            data.title = "xyz"

            try:
                checker.v(data)
            # pragma: no cover pylint: disable=unused-variable
            except (AssertionError,) as e:
                if verbose:
                    print(f"✅ expected failure {e} for {data=}")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


@unittest.skipUnless(*check_keep("valstacking"))
class Test_ValidatorMgr_Stacking(Base):
    """
    rather than having to subclass LazyMeta managed classes
        Mixin_Test_Http, Mixin_Test_Html
    explicitly combine ValidorMgr instances
        validation_manager_http, validation_manager_html

    """

    name_status = "status_code"
    name_contenttype = "content_type"
    name_valjson = "json_schema"

    missing = 404
    ok = 200
    content_html = "text/html"
    content_json = "application/json"

    ext_json = "json"
    ext_html = "html"
    ext_http = "http"

    def setUp(self) -> None:
        "setup a base Http Mgr"
        try:
            self.validation_manager_http = validators.ValidatorMgr(
                ext=self.ext_http,
                validators=[
                    dict(
                        name=self.name_status,
                        v=validators.check_equal,
                        selector=validators.Selectors.name,
                        exp=self.ok,
                    ),
                    dict(
                        name=self.name_contenttype,
                        v=validators.check_equal,
                        selector=validators.Selectors.name,
                    ),
                ],
            )

            self.di_vbase = {v.name: v for v in self.validation_manager_http.validators}

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_base(self):
        try:
            di = self.di_vbase
            self.assertEqual(None, di[self.name_contenttype].exp)
            self.assertEqual(self.ok, di[self.name_status].exp)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_validatormgr(self):
        """test stacking with ValidatorMgr"""
        try:
            html = "html"

            partial1 = validators.ValidatorMgr(
                ext=self.ext_http,
                validators=[dict(name=self.name_status, exp=self.missing)],
            )

            partial2 = validators.ValidatorMgr(
                ext=self.ext_json,
                validators=[dict(name=self.name_contenttype, exp=self.content_json)],
            )

            partial_json_validator = validators.ValidatorMgr(
                ext=self.ext_json, validators=[dict(name=self.name_valjson)]
            )

            mgr = self.validation_manager_http.extend(
                partial1, partial2, partial_json_validator, ext=html
            )

            self.assertEqual(html, mgr.ext)

            di_v = {v.name: v for v in mgr.validators}

            self.assertEqual(self.content_json, di_v[self.name_contenttype].exp)
            self.assertEqual(self.missing, di_v[self.name_status].exp)

            self.assertEqual(None, di_v[self.name_valjson].v)
            self.assertEqual(True, di_v[self.name_valjson].active)

            #################################################################
            # now test the testing...
            #################################################################

            class Test(unittest.TestCase, metaclass=_LazyMeta):
                cls_validators = dict(json=mgr)

            testee = Test()

            data = TData(content_type=self.content_json, status_code=404)

            # The ValidationMgr of interest
            v = testee.lz.json.v

            testee.status_code = 200

            # Configuration ought to fail on testee has no `json_schema` attribute
            with pytest.raises(ConfigurationException) as tmp:
                v(data)

            # di_error = parse_pydantic_validation_error(tmp)
            # msg = di_error.get("v", {}).get("msg")
            # self.assertIn("v is missing", msg)

            # deactivate json validation
            testee.lz.json.validators[self.name_valjson].active = False

            # now we are missing status_code on data
            delattr(testee, "status_code")

            # with pytest.raises(validators.ConfigurationException) as tmp:
            v(data)

            self.assertEqual(tmp._excinfo[0], validators.ConfigurationException)
            self.assertIn(self.name_status, str(tmp._excinfo[1]))

            # we should now fail on exp 404 does not match got 200 on status_code
            data = TData(content_type=self.content_json, status_code=self.ok)

            tu_exp_exc = (AssertionError,)
            with pytest.raises(tu_exp_exc) as tmp:
                v(data)

            # self.assertEqual(tmp._excinfo[0], validators.ValidationError)
            self.assertIn(self.name_status, str(tmp._excinfo[1]))

            # should pass
            data.status_code = 404
            v(data)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    @unittest.skipUnless(*check_keep("tdata_html"))
    def test_stacking_validator(self):
        """test stacking with Validator"""
        try:
            mgr = self.validation_manager_http.extend(
                validators.Validator(name=self.name_contenttype, exp=self.content_html),
                # ext=self.ext_html,
            )

            # self.assertEqual(self.ext_html, mgr.ext)

            di_v = {v.name: v for v in mgr.validators}

            self.assertEqual(self.content_html, di_v[self.name_contenttype].exp)
            self.assertEqual(self.ok, di_v[self.name_status].exp)

            # are we keeping base selectors?
            for name in [self.name_status, self.name_contenttype]:
                self.assertTrue(
                    di_v[name].selector, f"selector missing on {di_v[name]}"
                )

            #################################################################
            # now test the testing...
            #################################################################

            class Test(metaclass=_LazyMeta):
                cls_validators = dict(html=mgr)

            testee = Test()

            checker = testee.lz.html

            data = get_fake_response_from_html(
                status=self.ok, content_type=self.content_html
            )
            checker.v(data)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_stacking_dict(self):
        """test stacking with dict"""
        try:
            html = "html"
            mgr = self.validation_manager_http.extend(
                dict(name=self.name_contenttype, exp=self.content_html), ext=html
            )

            self.assertEqual(html, mgr.ext)

            di_v = {v.name: v for v in mgr.validators}

            self.assertEqual(self.content_html, di_v[self.name_contenttype].exp)
            self.assertEqual(self.ok, di_v[self.name_status].exp)

            # are we keeping base selectors?
            for name in [self.name_status, self.name_contenttype]:
                self.assertTrue(
                    di_v[name].selector, f"selector missing on {di_v[name]}"
                )

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


class Test_Aliasing(Base):
    """allowing ext_provider different from the Checker's name"""

    dummy_objectvalue01 = "<objectvalue01>"

    def gen_test_classes(self, testclassname: str) -> Dict[str, type]:
        """generate classes using LazyMeta gets tested"""
        try:

            li_val = [
                dict(
                    name="objectvalue01",
                    v=validators.check_equal,
                    selector="objectvalue01",
                )
            ]
            filters = [DictFilter(f=dict(skip_21=None, skip_22=None))]

            if testclassname == "TNoAlias":

                class TNoAlias(metaclass=_LazyMeta):
                    "basic check of non-aliased behavior"
                    cls_validators = dict(json=li_val)

                    cls_filters = dict(json=filters)

                    lazy_filename = self.lazy_filename
                    _testMethodName = self._testMethodName

            elif testclassname == "TSettingsAliasValidatorMgr":

                validator_settings = [
                    ExtAlias(alias="json"),
                    common.Validator(
                        name="objectvalue01",
                        v=common.check_equal,
                        selector="objectvalue01",
                    ),
                ]

                class TSettingsAliasValidatorMgr(metaclass=_LazyMeta):
                    """check we can drop in validator lists with aliases"""

                    cls_validators = dict(settings=validator_settings)

                    cls_filters = dict(settings=[ext_alias_json] + filters)

                    lazy_filename = self.lazy_filename
                    _testMethodName = self._testMethodName

            elif testclassname == "TSettingsAlias":

                class TSettingsAlias(metaclass=_LazyMeta):
                    "test that `settings` can be aliased to `json`"
                    cls_validators = dict(settings=[ext_alias_json] + li_val)

                    cls_filters = dict(settings=[ext_alias_json] + filters)

                    lazy_filename = self.lazy_filename
                    _testMethodName = self._testMethodName

            elif testclassname == "TSettingsAliasChild":

                class TSettingsAlias(metaclass=_LazyMeta):
                    "test that `settings` can be aliased to `json`"
                    cls_validators = dict(settings=[ext_alias_json] + li_val)

                    cls_filters = dict(settings=[ext_alias_json] + filters)

                    lazy_filename = self.lazy_filename
                    _testMethodName = self._testMethodName

                class TSettingsAliasChild(TSettingsAlias):
                    cls_validators = dict(settings=dict(name="c", selector="c", exp=3))

            classes = self.get_classes_oi(locals())

            res = {cls_.__name__: cls_ for cls_ in classes}
            return res

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    input1 = dict(
        skip_21=1,
        objectvalue01=dummy_objectvalue01,
        skip_22=2,
        c=3,
        pass_31="a",
        comp=dict(c1="c1", c2=200, c3="foo"),
    )

    classnameoi = "TBase"
    ext = "dict"

    def get_testee_data(
        self, testclassname, data=None, di_exp=dict(objectvalue01=dummy_objectvalue01)
    ):
        """build a testee by classname, prep data and set expectations for AutoExp"""
        try:
            di_cls = self.gen_test_classes(testclassname)
            self.cls_tst = di_cls[testclassname]
            testee = self.cls_tst()
            testee.__dict__.update(**di_exp)

            data = data or self.input1.copy()

            return testee, data
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_settings_alias_badexp(self):
        try:

            testee, data = self.get_testee_data(
                "TSettingsAlias", di_exp=dict(objectvalue01="badexp")
            )
            checker = testee.lz.settings
            with pytest.raises(common.ValidationError):
                checker.v(data)

            # raise NotImplementedError()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_settings_alias_child(self):

        try:

            testee, data = self.get_testee_data("TSettingsAliasChild")
            checker = testee.lz.settings
            checker.v(data)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_settings_alias_with_validatormgr(self):
        try:

            testee, data = self.get_testee_data("TSettingsAliasValidatorMgr")
            checker: Checker = testee.lz.settings
            self.assertEqual(checker.alias, "json")
            checker.v(data)

            # raise NotImplementedError()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_settings_alias(self):
        try:

            testee, data = self.get_testee_data("TSettingsAlias")
            checker: Checker = testee.lz.settings
            self.assertEqual(checker.alias, "json")
            checker.v(data)

            # raise NotImplementedError()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_no_alias_bad_exp(self):
        try:

            testee, data = self.get_testee_data(
                "TNoAlias", di_exp=dict(objectvalue01="badexp")
            )
            checker = testee.lz.json

            with pytest.raises(common.ValidationError):
                checker.v(data)

            # raise NotImplementedError()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def test_no_alias(self):
        try:

            testee, data = self.get_testee_data("TNoAlias")
            checker = testee.lz.json
            checker.v(data)

            # raise NotImplementedError()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


def custom_imports_for_pdb():
    """import modules on which you want to turn on pdb"""


custom_imports_for_pdb()

verbose = False

if __name__ == "__main__":

    # if __name__ == "__main__":
    cpdb = set_cpdb()
    rpdb = set_rpdb()

    if "-v" in sys.argv or "--verbose" in sys.argv:
        verbose = core_assist2.verbose = validators.verbose = True

    sys.exit(unittest.main())
