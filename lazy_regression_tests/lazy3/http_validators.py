import pdb
import json

#######################################################
# Dependencies
#######################################################

from bs4 import BeautifulSoup as bs

from .validators import (
    ValidationManager,
    ValidationDirective,
    NamedTesteeAttributeValidator,
    FullyQualifiedNamesValidator,
    MixinExpInGot,
    Validator,
    AttrNamedDictValidator,
)

from .filters import FilterManager

from traceback import print_exc as xp

undefined = NotImplemented


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


from lazy_regression_tests.utils import first, fill_template, ppp


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

http_validations = ValidationManager("base")
http_validations.add_directive("status_code", 200, StatusCodeValidator())
http_validations.add_directive(
    "content_type", validator=ContentTypeValidator(), active=True
)


class HTTPValidationMixin:
    """ sets basic expectations 
        - http is expected to return a status_code, typically 200 (exp can be changed later)
        - and has a content_type, which changes depending on end points
    """

    cls_validators = http_validations


#######################################################
# HTML-type validations
#######################################################
val = html_validations = ValidationManager("html")
val.add_directive("title", TitleCSSValidator(), active=True)


class HTMLValidationMixin(HTTPValidationMixin):
    """ 
        - we now our content type now
        - and we always want to validate titles, by default 
          but, again, we don't yet know what to expect here.

        add/qualify the expectations on HTTPValidationMixin 
        mixing and matching validations is done by the metaclass that is connected
        to LazyMixin
    """

    cls_validators = [html_validations, ValidationDirective("content_type", exp="html")]


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


class ResponseHTML:
    def __repr__(self):
        return "%s" % (self.__class__.__name__)

    _selectable = undefined

    @property
    def selectable(self):

        if self._selectable is undefined:
            self._selectable = bs(self.content)
        return self._selectable

    def __init__(self, response):
        try:
            self._response = response
            self.content = response.content
            self.status_code = response.status_code
            self.headers = response._headers

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise
