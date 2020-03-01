import os
import pdb
import tempfile
import datetime
import random
import string

from traceback import print_exc as xp


from lazy_regression_tests.utils import ppp, getpath, UnavailableLibrary

#################################################################
# Depencies for test
#################################################################


class Foo:
    pass


dep_message = "👉 This is only requiry for lazy self-testing on http contents, not for normal use. 👈"


try:
    import responses
except (ImportError,) as e:
    # this will throw an InvalidConfigurationError on any access to bs
    # telling you to install BeautifulSoup

    responses = UnavailableLibrary(
        name=Foo.__module__, missing="responses", message=dep_message
    )


try:
    import requests
except (ImportError,) as e:
    # this will throw an InvalidConfigurationError on any access to bs
    # telling you to install BeautifulSoup
    requests = UnavailableLibrary(
        name=Foo.__module__, missing="requests", message=dep_message
    )

try:
    import jinja2
except (ImportError,) as e:
    # this will throw an InvalidConfigurationError on any access to bs
    # telling you to install BeautifulSoup
    jinja2 = UnavailableLibrary(
        name=Foo.__module__, missing="jinja2", message=dep_message
    )


try:
    import unittest.mock as mock
except (ImportError,) as ei:
    import mock  # python 2?


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


from lazy_regression_tests.http_validators import ResponseHTML


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


def get_fake_response_from_html(
    html, url=None, status=200, content_type="text/html; charset=utf8"
):
    try:

        url = url or "http://example.com/"

        @responses.activate
        def faker(html):
            # responses.add(responses.GET, 'http://twitter.com/api/1/foobar',
            #               json={'error': 'not found'}, status=404)

            responses.add(
                responses.GET, url, body=html, status=status, content_type=content_type
            )

            resp = requests.get(url)
            return resp

        response = faker(html)
        assert response
        return response

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise


def get_fake_response_from_template(
    testee, data={}, url=None, status=200, content_type="text/html; charset=utf8"
):
    """ return a pretend HttpResponse"""
    try:

        url = url or "http://example.com/"

        data = testee.get_data(seed=data)

        tmpl = jinja2.Template(testee.template)
        text = tmpl.render(**data)

        response = get_fake_response_from_html(html=text, url=url, status=status)

        assert response

        return response

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise


exp_fail_padder = "✅" * 40


def show_expected_fail(exc):
    """ show the error details on expected failures"""
    print(f"{exp_fail_padder}{exc}{exp_fail_padder}")


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

            tmpl = jinja2.Template(self.template)
            html = tmpl.render(**data)

            response = get_fake_response_from_html(html, url=url)
            return response

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


def main():
    @responses.activate
    def test_simple():
        # responses.add(responses.GET, 'http://twitter.com/api/1/foobar',
        #               json={'error': 'not found'}, status=404)

        responses.add(
            responses.GET,
            "http://twitter.com/api/1/foobar",
            body="<div>coucou</div>",
            status=200,
        )

        resp = requests.get("http://twitter.com/api/1/foobar")

        return resp

    response = test_simple()
    ppp(response, "response")

    pdb.set_trace()


if __name__ == "__main__":
    main()
