import pdb
import json
import sys
import os
import copy


#######################################################
# Dependencies
#######################################################


from .common import UnavailableLibrary

try:
    from bs4 import BeautifulSoup as bs

# pragma: no cover pylint: disable=unused-variable
except (ImportError,) as e:

    class Foo:
        pass

    # this will throw an InvalidConfigurationError on any access to bs
    # telling you to install BeautifulSoup
    bs = UnavailableLibrary(name=Foo.__module__, missing="Beautifulsoup")

#######################################################


verbose = "-v" in sys.argv


from .validators import (
    ValidationManager,
    ValidationDirective,
    NamedTesteeAttributeValidator,
    FullyQualifiedNamesValidator,
    MixinExpInGot,
    Validator,
    AttrNamedDictValidator,
)

from .filters import FilterManager, RawFilter, DataMatcher

from traceback import print_exc as xp

undefined = NotImplemented


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


from lazy_regression_tests.utils import first, fill_template, ppp, getpath, debugObject

#################################################################
# the Filters
#################################################################


class CSSRemoveFilter(RawFilter, DataMatcher):
    """ this belongs in the http_validators module """

    def __init__(self, pattern, name, keep=True, scalar=False, *args):
        self.selector = pattern
        self.name = name
        self.scalar = scalar
        self.keep = keep

    def pre_format(self, data):
        try:
            data = bs(data)
            return data
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def filter(self, options, tmp, data, callback):
        try:

            if isinstance(data, str):
                data = self.pre_format(data)

            li = []

            keep = self.keep

            hits = data.select(self.selector)

            if not hits:

                # if it's an empty list, it can be assigned as a scalar.  if None, ditto
                tmp.add_filtered(self.name, hits, scalar=True)
                return data

            for hit in hits:

                if keep:
                    hit2 = copy.copy(hit)
                    self.add_to_filter_hit(tmp, hit2)
                li.append(hit)

            if callback:
                callback(self.name, data, li)

            for hit in li:
                hit.decompose()

            return data

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class HeadersValidator(AttrNamedDictValidator):
    """specifies source for HTTP headers """

    sourcename = "response.headers"


class ContentTypeValidator(
    FullyQualifiedNamesValidator, MixinExpInGot, HeadersValidator
):
    """ check response headers for content type.   
        not that `exp` is checked for being within the actual content type, not for equality
        exp:json matches application/json
    """

    selector = "content-type"


class StatusCodeValidator(NamedTesteeAttributeValidator):
    """ check an http status code .  you can provide 
        multiple codes in exp, ex: `exp = [200,302, "404"]`
    """

    sourcename = "response"
    selector = "status_code"

    def test(self, testee, exp, got, message, name=None):
        try:

            if message is None:
                message = fill_template(
                    "%(name)s exp:%(exp)s<>%(got)s:got",
                    locals(),
                    self,
                    {"name": name or self},
                )

            if isinstance(exp, (int, str)):
                exp = [exp]

            exp = [int(exp) for exp in exp]

            got = int(got)

            testee.assertTrue(got in exp, message)

        except (AssertionError,) as e:  # pragma: no cover
            raise

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class CSSValidator(Validator):
    """ responsible for getting DOM data out, typically via Beautifulsoup
        but anything provising CSS selectors could be used.

        this class expects response to be in sources during check_expectations calls
        on that it wants a selectable attribute with select on it.

        calling code may look like this.

            response = request.get(url)
            response.selectable = BeautifulSoup(response.content)
            self.check_expectations(response=response)

    """

    sourcename = "response.selectable"

    to_text = False

    def __init__(self, selector, scalar=None, to_text=True, cargo=None):

        if scalar is None:
            scalar = selector.startswith("#")

        super(CSSValidator, self).__init__(
            selector, scalar=scalar, sourcename=self.sourcename, cargo=cargo
        )
        self.to_text = to_text

    def get_value(self, source):

        found = source.select(self.selector)
        if self.scalar:
            found = first(found)
            if found and self.to_text:
                return found.text.strip()
            return found
        else:
            if not self.to_text:
                return found
            else:
                return [elem.text.strip() for elem in found]


class TitleCSSValidator(FullyQualifiedNamesValidator, CSSValidator):
    selector = "title"
    scalar = True
    to_text = True


#######################################################
# Compose base validations/expectations
#######################################################


class HTTPValidationMixin:
    """ sets basic expectations 
        - http is expected to return a status_code, typically 200 (exp can be changed later)
        - and has a content_type, which changes depending on end points
    """

    cls_validators = [
        ValidationDirective("status_code", exp=200, validator=StatusCodeValidator()),
        ValidationDirective(
            "content_type", active=True, validator=ContentTypeValidator()
        ),
    ]


#######################################################
# HTML-type validations
#######################################################

title_validation = ValidationDirective(
    "title", active=True, validator=TitleCSSValidator()
)


class HTMLValidationMixin(HTTPValidationMixin):
    """ set `content_type` expectations
        always want to validate `title`, by default 
    """

    cls_validators = [title_validation, ValidationDirective("content_type", exp="html")]


class JSONValidationMixin(HTTPValidationMixin):
    """ sets the expected content type to JSON """

    cls_validators = [ValidationDirective("content_type", exp="json")]


class HtmlFilterManager(FilterManager):
    """Filter Manager for HTML"""

    def prep(self, tmp, data):
        try:
            if hasattr(data, "select"):
                return data
            else:
                return bs(data)
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def to_text(self, tmp, data):
        try:
            # pdb.set_trace()
            return data.prettify()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class Response:
    def _get_content_type(self, response):
        try:

            # headers ''
            # content-length=('Content-Length', '11147')
            # content-type=('Content-Type', 'text/html; charset=utf-8')
            # vary=('Vary', 'Cookie')

            if verbose:
                mode = os.getenv("bme_test_fetchmode", "unknownmode")
                with open("./debug.%s.response.txt" % (mode), "w") as fo:
                    for k in sorted(vars(response).keys()):
                        fo.write(f"{k}={str(getattr(response,k)):200.200}" + "\n")

                    fo.write(debugObject(self.headers, "\nheaders:"))

            # pdb.set_trace()

            part1 = self.headers.get("content-type") or self.headers.get(
                "Content-Type", {}
            )

            if isinstance(part1, tuple):

                if "/json" in part1[-1]:
                    return "json"

                if "text/html" in part1[-1]:
                    return "html"

            elif isinstance(part1, str):

                if part1.endswith("/json"):
                    return "json"

                if part1.endswith("/html"):
                    return "html"

            raise NotImplementedError("%s._get_content_type(%s)" % (self, locals()))

            content_type = part1[1].split(";")[0].split("/")[1]

            assert content_type in ("html", "json"), "unknown content_type:%s:" % (
                content_type
            )

            return content_type

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    wanteds = dict(
        headers=["headers", "_headers"],
        content=["content"],
        status_code=["status_code"],
    )

    def __init__(self, response):
        try:
            self._response = response

            for attrname, paths in self.wanteds.items():
                if isinstance(paths, str):
                    paths = [paths]

                # pdb.set_trace()
                for path in paths:
                    try:
                        value = getpath(response, path)
                        setattr(self, attrname, value)
                        break
                    # pragma: no cover pylint: disable=unused-variable
                    except (AttributeError,) as e:
                        pass
                else:
                    raise AttributeError(attrname)

            # pdb.set_trace()
            self.content_type = self._get_content_type(response)
            assert self.content_type, "missing self."
            # pdb.set_trace()
            self._init()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def _init(self):
        """do nothing"""


class ResponseJSON(Response):
    pass

    def _init(self, *args, **kwargs):
        """do nothing"""
        try:

            if not self.content_type in ("json"):
                self.json = None
                return
            self.json = json.loads(self.content)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class SnippetHTML(Response):
    """ supports testing of html snippets rather than full http response """

    def _get_content_type(self, response):
        return "html"

    wanteds = {}

    def __repr__(self):
        return "%s" % (self.__class__.__name__)

    _selectable = undefined

    @property
    def selectable(self):

        if self._selectable is undefined:
            self._selectable = bs(self.content)
        return self._selectable

    def _init(self):
        """do nothing"""

        assert isinstance(self._response, str)

        self.content = self._response


class ResponseHTML:
    def __repr__(self):
        return "%s" % (self.__class__.__name__)

    _selectable = undefined

    @property
    def selectable(self):

        if self._selectable is undefined:
            self._selectable = bs(self.content)
        return self._selectable

    wanteds = dict(headers=["headers", "_headers"])

    def __init__(self, response):
        try:
            self._response = response
            self.html = self.content = response.content
            self.status_code = response.status_code

            for attrname, paths in self.wanteds.items():
                if isinstance(paths, str):
                    paths = [paths]

                # pdb.set_trace()
                for path in paths:
                    try:
                        value = getpath(response, path)
                        setattr(self, attrname, value)
                        break
                    # pragma: no cover pylint: disable=unused-variable
                    except (AttributeError,) as e:
                        pass
                else:
                    raise AttributeError(attrname)

            if rpdb():  # pragma: no cover
                pdb.set_trace()

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise
