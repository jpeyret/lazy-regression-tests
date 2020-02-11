from .validators import (
    ValidationManager,
    ValidationDirective,
    NamedTesteeAttributeValidator,
    FullyQualifiedNamesValidator,
    MixinExpInGot,
    HeadersValidator,
    Validator,
    AttrNamedDictValidator,
)


undefined = NotImplemented


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


from lazy_regression_tests.utils import (
    nested_dict_get,
    nested_dict_pop,
    first,
    fill_template,
    ppp,
)


class ContentTypeValidator(
    FullyQualifiedNamesValidator, MixinExpInGot, HeadersValidator
):
    selector = "content-type"


class StatusCodeValidator(NamedTesteeAttributeValidator):
    sourcename = "response"
    selector = "status_code"

    def test(self, testee, exp, got, message):
        try:

            if exp is undefined:
                raise ValueError("exp is undefined")

            if message is None:
                message = fill_template(
                    "%(name)s exp:%(exp)s<>%(got)s:got", locals(), self, {"name": self}
                )

            if isinstance(exp, (int, str)):
                exp = [exp]

            exp = [int(exp) for exp in exp]
            got = int(got)

            testee.assertTrue(
                got in exp, "%s , not in expected status_code to %s" % (got, exp)
            )

            # testee.assertEqual(exp, got, message)
        except (AssertionError,) as e:  # pragma: no cover
            raise

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class CSSValidator(Validator):

    sourcename = "response.selectable"

    to_text = False

    def __init__(self, selector, scalar=None, to_text=True):

        if scalar is None:
            scalar = selector.startswith("#")

        super(CSSValidator, self).__init__(
            selector, scalar=scalar, sourcename=self.sourcename
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
#
#######################################################

http_validations = ValidationManager("base")
http_validations.add_directive("status_code", 200, StatusCodeValidator())
http_validations.add_directive(
    "content_type", validator=ContentTypeValidator(), active=True
)


class HTTPValidationMixin:
    cls_validators = http_validations


#######################################################
# HTML-type validations
#######################################################
val = html_validations = ValidationManager("html")
val.add_directive("title", TitleCSSValidator(), active=True)


class HTMLValidationMixin(HTTPValidationMixin):
    cls_validators = [html_validations, ValidationDirective("content_type", exp="html")]


class JSONValidationMixin(HTTPValidationMixin):
    cls_validators = [ValidationDirective("content_type", exp="json")]
