"""
support testing 
"""
import bs4

bs = bs4.BeautifulSoup
import jinja2
import responses
import requests
import json
import os
import unittest
import unittest.mock as mock
import sys

# from lazy_tstmixin import TstMixin

from typing import Callable

from lazy_regression_tests.constants import OPT_DIRECTIVE_BASELINE

from lazy_regression_tests.basics import ConfigurationException

import lazy_regression_tests.core_assist2 as core_assist2
from lazy_regression_tests.core_assist2 import _LazyMeta, Filter


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


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
        USE_TEMP_FILE = not (os.getenv("lzrt_TESTING_NO_TEMP_FILE")) and not (
            os.getenv("lzrt_livetests_dir")
        )

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
            breakpoint()
        raise


di_mock_env = get_mock_env()
di_mock_env_baseline = di_mock_env.copy()
di_mock_env_baseline.update(lzrt_directive=OPT_DIRECTIVE_BASELINE)


def get_fake_response_from_html(
    data=None, url=None, status=200, content_type="text/html; charset=utf8", title=None
):

    try:

        url = url or "http://example.com/"

        if "json" in content_type:
            data = data or {"objectvalue01": "PTPT1000"}

            @responses.activate
            def faker(data):
                # responses.add(responses.GET, 'http://twitter.com/api/1/foobar',
                #               json={'error': 'not found'}, status=404)

                responses.add(
                    responses.GET,
                    url,
                    json=data,
                    status=status,
                    content_type=content_type,
                )

                resp = requests.get(url)
                return resp

        else:
            data = data or DUMMY_HTML

            if title:
                soup = bs(data)
                tag = soup.select("title")
                tag[0].string.replace_with(title)

            @responses.activate
            def faker(data):

                responses.add(
                    responses.GET,
                    url,
                    body=data,
                    status=status,
                    content_type=content_type,
                )

                resp = requests.get(url)
                return resp

        response = faker(data)

        return response

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            breakpoint()
        raise


def get_fake_response(
    html_in: str, data={}, url=None, status=200, content_type="text/html; charset=utf8"
):
    """ return a pretend HttpResponse"""
    try:

        if data:
            tmpl = jinja2.Template(html_in)
            html = tmpl.render(**data.as_dict())
        else:
            html = html_in

        url = url or "http://example.com/"

        @responses.activate
        def faker(html):

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
            breakpoint()
        raise


class TData:
    """ Wrapper to simulate test data objects"""

    def json(self):
        return json.dumps(self.__dict__, indent=2, sort_keys=True)

    def dict(self):
        return self.__dict__.copy()

    def __init__(self, **kwargs):
        "init"
        self.__dict__.update(**kwargs)

    def __repr__(self):
        "repr"
        return f"{self.__class__.__name__}:{str(self.__dict__)}"


class TstMixinSeeder:
    @mock.patch.dict(os.environ, di_mock_env_baseline)
    def seed(self, data, testee: unittest.TestCase, checker: "Checker"):
        try:
            try:
                data = data.copy()
                res = checker.assert_same(data)
                return res
            except (AssertionError,) as e:
                pass

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise


DUMMY_BODY = """
<body>

  <!-- Add your site or application content here -->
  <p>Hello world! This is HTML5 Boilerplate.</p>
  <script src="js/vendor/modernizr-3.11.8.min.js"></script>
  <script src="js/app.js"></script>

</body>
"""

DUMMY_TITLE = "dummy title"

DUMMY_HTML = f"""
<!doctype html>
<html class="no-js" lang="">

<head>
  <meta charset="utf-8">
  <title>{DUMMY_TITLE}</title>
  <meta name="description" content="">
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <meta property="og:title" content="">
  <meta property="og:type" content="">
  <meta property="og:url" content="">
  <meta property="og:image" content="">

  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" href="/icon.svg" type="image/svg+xml">

  <link rel="apple-touch-icon" href="icon.png">
  <!-- Place favicon.ico in the root directory -->

  <link rel="stylesheet" href="css/normalize.css">
  <link rel="stylesheet" href="css/style.css">

  <link rel="manifest" href="site.webmanifest">
  <meta name="theme-color" content="#fafafa">
</head>

{DUMMY_BODY}

</html>
"""


class TstMixin(unittest.TestCase):
    """ functions to test Lazy frame work itself """

    def get_classes_oi(self, vars):
        """filter lazymeta-d classes from a locals/globals"""
        classes = [v for v in vars.values() if type(v) == _LazyMeta]

        return classes

    def get_filter_by_label(self, src, ext: str, label: str) -> Filter:
        """ gets a filter by label"""

        mgr = src.cls_filters[ext]
        known = ""
        for filter in mgr.filters:
            known += f"{filter.label}/"
            if filter.label == label:
                return filter
        raise ValueError(f"unknown Filter {ext=} {label=}.  known labels={known}")

    def get_filter_exp(self, text: str, f_skip: Callable[[str], bool]):
        """ apply hand-written filter to some text
        Example:
        exp = self.get_filter_exp(self.text1, lambda line:  ("abc" in line or "def" in line) )    
        """
        lines = text.splitlines()
        lines = [line for line in lines if not f_skip(line)]
        return "\n".join(lines).strip()

    def assert_filter_exp(self, src, ext: str, label: str, di_exp: dict):

        filter = self.get_filter_by_label(src, ext, label)
        di_got = {k: getattr(filter, k) for k in di_exp.keys()}

        try:
            self.assertEqual(di_exp, di_got)
        # pragma: no cover pylint: disable=unused-variable
        except (AssertionError,) as e:
            msg = f"\nFilter:{ext=}{label=}\n{e.args[0]}"
            e.args = (msg, filter)
            raise
