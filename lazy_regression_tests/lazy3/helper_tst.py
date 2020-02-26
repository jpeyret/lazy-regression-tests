import os
import pdb
import tempfile
import datetime
import random
import string

try:
    import unittest.mock as mock
except (ImportError,) as ei:
    import mock  # python 2?


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


from django.http import HttpResponse, JsonResponse

from jinja2 import Template


#################################################################
# 💀💀💀💀💀 GUARD SINGLETON THIS OR ELSE CREATES THESE EVERYTIME


# 💀💀💀💀💀
#################################################################


from lazy_regression_tests.lazy3.http_validators import ResponseHTML


def get_mock_env(seed={}):
    """
        this is used to mock the environment variables and 

        also determines whether temp files are:
        - used     : useful for self-testing the lazy-test itself
        - not used : pretty much required for actual lazy-test usage

        Note the self-caching 
    """

    try:

        # to use temp files or not?
        USE_TEMP_FILE = not (os.getenv("lzrt_TESTING_NO_TEMP_FILE"))

        if USE_TEMP_FILE:

            di_mock_env = getattr(get_mock_env, "di_mock_env", None)
            if di_mock_env:
                res = di_mock_env.copy()
                res.update(**seed)
                return res

            dirtemp = tempfile.mkdtemp(prefix="lazy_regression_tests_")

            lzrt_default_t_basename = "%(filename)s %(classname)s %(_testMethodName)s %(lazy_basename_extras)s %(suffix)s %(extension)s"

            lzrt_template_dirname = os.path.join(dirtemp, "out")
            lzrt_template_dirname_got = os.path.join(dirtemp, "got")
            lzrt_template_dirname_exp = os.path.join(dirtemp, "exp")
            lzrt_template_dirname_report = os.path.join(dirtemp, "report")

            lzrt_template_basename = lzrt_default_t_basename

            res = get_mock_env.di_mock_env = dict(
                lzrt_template_dirname=lzrt_template_dirname,
                lzrt_template_dirname_got=lzrt_template_dirname_got,
                lzrt_template_dirname_exp=lzrt_template_dirname_exp,
                lzrt_template_basename=lzrt_template_basename,
                lzrt_template_dirname_report=lzrt_template_dirname_report,
            )

            res = res.copy()
            res.update(**seed)

            return res
        else:
            res = os.environ.copy()
            res.update(**seed)
            return res

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise


choice_csrf = string.ascii_letters + string.digits


def get_fake_html_response(testee, data={}):
    try:

        data = testee.get_data(seed=data)

        tmpl = Template(testee.template)
        text = tmpl.render(**data)
        return HttpResponse(text)

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise


class Helper:

    fail_on_validate = None
    fail_on_change = None

    def simulate_previous_pass(self):
        """ this simulates a first run"""

        http_response = self.get_raw_response()
        response = ResponseHTML(http_response)
        self.assert_exp(response.content, self.extension)

    def get_raw_response(self, url=None, data={}):
        try:

            data = self.get_data(seed=data)

            tmpl = Template(self.template)
            text = tmpl.render(**data)
            return HttpResponse(text)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def get_data(self, seed={}):
        data = dict(vars(self.__class__))
        data.update(timestamp=datetime.datetime.now())

        csrf = "".join([random.choice(choice_csrf) for ix in range(0, 20)])

        data.update(csrf=csrf)
        data.update(**vars(self))
        data.update(**getattr(self, "data", {}))

        data.update(**seed)

        return data

    def get_response(self, url=None, data={}):
        try:

            data = data or self.get_data(seed=data)

            tmpl = Template(self.template)
            text = tmpl.render(**data)
            return ResponseHTML(HttpResponse(text))

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class HelperHTML(Helper):
    def get_response(self, url=None, data={}):
        try:

            http_response = self.get_raw_response(url=url, data=data)
            return ResponseHTML(http_response)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class CheckitMixin:

    di_mock_env = get_mock_env()

    @mock.patch.dict(os.environ, di_mock_env)
    def test_it(self):
        """get response"""
        try:

            # first pass
            response = self.get_response()
            self.assert_exp(response.content, self.extension)

            response = self.get_response()

            if self.fail_on_validate:
                try:
                    self.check_expectations(response=response)
                # pragma: no cover pylint: disable=unused-variable
                except (AssertionError,) as e:
                    self.assertTrue(str(self.fail_on_validate) in str(e))
                else:
                    self.fail(
                        "should have failed validation with %s"
                        % (self.fail_on_validate)
                    )

            else:
                self.check_expectations(response=response)

            if self.fail_on_change:
                try:
                    tmp = self.assert_exp(response.content, self.extension)
                # pragma: no cover pylint: disable=unused-variable
                except (AssertionError,) as e:
                    self.assertTrue(str(self.fail_on_change) in str(e))
                else:
                    self.fail(
                        "should have failed change checks with %s"
                        % (self.fail_on_change)
                    )

            else:
                tmp = self.assert_exp(response.content, self.extension)

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise
