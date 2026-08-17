"""validate HTTP stuff"""

import copy
import json
import os
import unittest
from logging import getLogger
from typing import Any, Callable, Iterable

import bs4

#################################################################
# Dependencies
#################################################################
import pydantic
import requests

import lazy_regression_tests.providers as providers
from lazy_regression_tests.common import (
    BFilter,
    Checker,
    ConfigurationException,
    Filter,
    LazyTemp,
    RawFilter,
    ValidatorTemp,
    check_equal,
    check_exp_in_data,
    select_by_provider,
)
from lazy_regression_tests.utils import first
from lazy_regression_tests.validators import Validator, ValidatorMgr

bs = bs4.BeautifulSoup
undefined = NotImplemented
logger = getLogger("lazy")
log = logger.debug


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


class CSSFilter(RawFilter):
    """ancestor of `raw` (non-text) filters"""

    f: str

    @pydantic.validator("f", pre=True)
    def build_filter(cls, selector, values):
        """prep the filter wrapper"""

        name = values.get("name")
        if breakpoints("build_filter", {"name": name}):  # pragma: no cover
            print(f"\n\n!!!name:{name}")  # debugging
            breakpoint()

        if not isinstance(selector, str):
            raise ConfigurationException(
                f"{cls=}.build_filter.unsupported selector {selector=}[{type(selector)}]"
            )
        values["f"] = selector
        return selector

    def filter(self, temp: "ValidatorTempHttp") -> Any:
        """mutate data in place"""
        # need to work with the soup, not the response
        li = temp.soup.select(self.f)

        if self.name:
            found = [copy.copy(v) for v in li]
            if self.scalar:
                found = first(found)
            if self.formatter:
                found = self.formatter(found)

            di = {self.name: found}
            temp.filtered = di
        for hit in li:
            hit.decompose()


class ValidatorTempHttp(ValidatorTemp):
    "work/temp area"

    _html_in = _soup = _html = _raw_html = None
    _formatted_got = undefined

    @property
    def formatted_got(self):
        "format data on demand, after filtering"
        if self._formatted_got is undefined:

            # apply filters if not done yet
            if self._filtered is None:
                # with a textfilter active this will side-effect self._formatted_got
                _ = self.filtered

            if self.checker.ext == "html":
                # this a textfilter so it is happening after soup.prettify

                if self._formatted_got is undefined:
                    self._formatted_got = self.soup.prettify()

            else:
                if self._formatted_got is undefined:
                    self._formatted_got = self.checker.provider.datain_to_str(
                        self.rawdata, checker=self.checker
                    )

        return self._formatted_got

    @property
    def soup(self):
        """BeautifulSoup from response html"""
        if self._soup is None:
            self._soup = bs(self.raw_html, "lxml")
        return self._soup

    @property
    def html_in(self):
        """prettified raw response html"""
        if self._html_in is None:
            self._html_in = bs(self.raw_html, "lxml").prettify()
        return self._html_in

    @property
    def raw_html(self):
        """raw response html"""
        if self._raw_html is None:
            if isinstance(self.data_in, str):
                self._raw_html = self.data_in
            else:
                self._raw_html = self.data_in.content.decode("utf-8")
        return self._raw_html

    @property
    def html(self):
        "prettified final html, after filtering"
        if self._html is None:
            self._html = self.soup.prettify()
        return self._html


class HTTP_Provider(providers.PAbstractExtProvider):
    def status_code(self, data: requests.models.Response):
        "get status code"
        try:
            return data.status_code
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def content_type(self, data: requests.models.Response):
        """get content-type"""
        headers = getattr(data, "_headers", None)
        if headers is not None:
            res = headers["content-type"][1]
            return res

        return data.headers["content-type"]


class HttpJson_Provider(HTTP_Provider, providers.JsonExtProvider):
    """handles json http responses"""

    TYPE_RAW = dict

    def prep_rawdata(self, checker: Checker, data: Any) -> Any:
        """convert data if needed"""
        try:
            if isinstance(data, str):
                res = json.loads(data)
                return res

            for name in ["json", "getvalue"]:
                f = getattr(data, name, None)
                if callable(f):
                    res = f()
                    if isinstance(res, (str, bytes)) and name in ("json", "getvalue"):
                        res = json.loads(res)
                    if not isinstance(res, dict):
                        raise ConfigurationException(f"""
data type {type(res)}, returned by data.{name}() not supported by {self}.
known extensions for testcase: {','.join(checker._lz.extensions)}"""
                        )

                    return res
            raise ConfigurationException(f"""
data type {type(data)} not supported by {self}.
known extensions for testcase: {','.join(checker._lz.extensions)}"""
            )

        except (json.decoder.JSONDecodeError):
            raise
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def select_by_string(
        self,
        validator: "Validator",
        data_in: Any,
        testee: Any,
        selector: str,
        temp: Any,
        rawdata: Any,
    ):
        """select data by string selector"""
        try:

            data = rawdata

            if "." not in selector:
                try:
                    res = data[selector]
                except (KeyError,) as e: # noqa F841
                    msg = f"{repr(self)} validator={validator.name} : {e}:  Known keys : {list(data.keys())}"
                    raise ConfigurationException(msg)
            else:
                path = ""
                for part in selector.split("."):
                    path += f".{part}"
                    try:
                        data = data[part]
                    except (KeyError,) as e: # noqa F841
                        msg = f"{repr(self)} : {validator.name} {e}:  {path=} Known keys : {list(data.keys())}"
                        raise ConfigurationException(msg)

                res = data

            return res
        # pragma: no cover
        except (ConfigurationException,) as e: # noqa F841
            raise
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


class HTML_Provider(HTTP_Provider):

    TYPE_RAW = bs4.BeautifulSoup

    def adjust_value_for_validation(
        self,
        checker: Checker,
        validator: "Validator",
        fn: Callable,
        value: Any,
        exc: Exception = None,
    ):
        """try to adjust for arbitrary validator functions"""
        try:
            if fn.__name__ in ("search", "match") and "re.Pattern" in str(fn):
                if isinstance(value, bs4.element.ResultSet):
                    return [v.text.strip() for v in value]

            raise NotImplementedError()
        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def prep_rawdata(self, checker: Checker, data: Any) -> Any:
        """convert data if needed"""
        try:

            if isinstance(data, str):
                soup = bs(data, "lxml")
                return soup

            if isinstance(data, bs4.element.ResultSet):
                v = "\n".join([str(v) for v in data])
                soup = bs(v, "lxml")
                return soup

            for name in ["content", "html"]:
                v = getattr(data, name, undefined)
                if v is not undefined:
                    soup = bs(v, "lxml")
                    return soup

            raise ConfigurationException(
                f"""data type {type(data)} not supported by {self}.
                known extensions for testcase: {','.join(checker._lz.extensions)}"""
            )

        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @classmethod
    def datain_to_str(cls, data: Any, checker: Checker, temp: LazyTemp = None) -> str:
        """data to str"""
        try:

            if isinstance(data, bs4.BeautifulSoup):
                return data.prettify().strip()

            if isinstance(data, str):
                return data.strip()

            if isinstance(data, dict):
                return json.dumps(data, indent=2, sort_keys=True).strip()

            if isinstance(data, bs4.element.ResultSet):
                li = [str(v) for v in data]
                return "\n".join(li).strip()

            d2 = getattr(data, "html", None)
            if isinstance(d2, str):
                return bs(d2, "lxml").prettify().strip()

            d2 = getattr(data, "content", None)
            if isinstance(d2, bytes):

                content_type = getattr(data, "content_type", None)
                if content_type is None:
                    headers = getattr(data, "headers", {}) or getattr(
                        data, "_headers", {}
                    )

                    content_type = headers.get("content-type")

                    if isinstance(content_type, tuple):
                        content_type = content_type[1]

                content_type = content_type or "?"

                if co.content_html in content_type:
                    soup = bs(d2, "lxml")
                    return soup.prettify().strip()
                elif content_type == co.content_json:
                    d3 = json.loads(d2)
                    return json.dumps(d3, indent=2, sort_keys=True).strip()

            raise ConfigurationException(
                f"""
data type {type(data)} not supported by {cls.__name__} which supports strings.
known extensions for testcase: {','.join(checker._lz.extensions)}"""
            )

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    cls_temp = ValidatorTempHttp

    def select_by_string(
        self,
        validator: "Validator",
        data_in: Any,
        testee: Any,
        selector: str,
        temp: Any,
        rawdata: Any,
    ):
        """select data by string selector"""
        if selector == "content_type":
            return self.content_type(data_in)

        temp = validator.mgr.temp
        res = temp.soup.select(selector)
        return res

    # 🎫004.lazy.052.polars_diffing - modify to pass in Checker, in order to access ValidatorMgr.config...
    def check_equal(
        self, testee: unittest.TestCase, validator: Validator, exp, got
    ) -> bool:
        """check if exp can be considered equal"""
        try:
            if isinstance(got, bs4.element.ResultSet):
                got = got[0].text.strip()

            is_iter = isinstance(exp, Iterable) and not isinstance(exp, str)
            if not isinstance(exp, type(got)):
                type_exp = type(exp)
                if is_iter:
                    type_exp = type(exp[0])

                got = type_exp(got)

            if is_iter:
                testee.assertTrue((got in exp), f"{got=} {exp=}")
                return True
            else:
                testee.assertEqual(exp, got, f"{got=} {exp=}")
                return True

        # pragma: no cover
        except (AssertionError,) as e: # noqa F841
            if os.getenv("cpdb"):
                breakpoint()
                pass
            raise
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def build_filter(self, v_in: Any) -> BFilter:
        "build filter"
        try:

            if isinstance(v_in, dict):
                raw = v_in.get("raw")
                if raw is None:
                    raw = True
                v_in["raw"] = raw
                if raw:
                    filter2 = CSSFilter(**v_in)
                else:
                    filter2 = Filter(**v_in)

            elif isinstance(v_in, str):
                filter2 = CSSFilter(f=v_in)
            else:
                raise ConfigurationException(f"unsupported {v_in}")

            return filter2

        # pragma: no cover
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def get_filtered_as_str(self, checker: Checker):
        "convert filtered to string"
        return self.datain_to_str(checker.temp.soup, checker)


providers.di_ext_provider["html"] = HTML_Provider()
providers.di_ext_provider["http_json"] = HttpJson_Provider()


class co:
    """constant"""

    status_code = "status_code"
    content_type = "content_type"

    content_html = "text/html"
    content_json = "application/json"


validator_http = ValidatorMgr(
    ext="html",
    validators=[
        dict(name=co.status_code, selector=select_by_provider, v=check_equal, exp=200),
        dict(name=co.content_type, selector=select_by_provider, v=check_exp_in_data),
    ],
)

validator_html = validator_http.extend(
    dict(name="content_type", exp=co.content_html),
    dict(name="title", selector="title", v=check_equal, scalar=True),
)

validator_json = validator_http.extend(
    dict(name="content_type", exp=co.content_json), ext="json"
)
validator_json.alias = alias = "http_json"
