import os
import sys
import unittest
import unittest.mock as mock

#################################################################
# various helpers to simulate an http server
#################################################################

from lazy_regression_tests.helper_tst import (
    Helper,
    get_mock_env,
    get_fake_response_from_template,
)

from lazy_regression_tests._baseutils import set_cpdb, ppp

verbose = "-v" in sys.argv

di_mock_env = get_mock_env()


#################################################################

# generic lazy functionality
from lazy_regression_tests import (
    LazyMixin,
    ValidationDirective,
    FilterDirective,
    AutoExp,
    RegexRemoveSaver,
)

# specific to HTTP/HTML validations
from lazy_regression_tests.http_validators import (
    HTMLValidationMixin,
    ResponseHTML,
    HtmlFilterManager,
    CSSRemoveFilter,
    CSSValidator,
)


class LazyMixinBasic(LazyMixin):
    """ base Mixin class for the lazy test framework """

    lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)
    cls_filters = dict(html=HtmlFilterManager())


filter_variables = [
    FilterDirective(
        "timestamp", filter_=CSSRemoveFilter("span.timestamp", "timestamp", scalar=True)
    ),
    FilterDirective("csrf", filter_=RegexRemoveSaver("csrf_token", "csrf_token")),
]


class Test_Features(Helper, HTMLValidationMixin, LazyMixinBasic, unittest.TestCase):

    cls_filters = dict(html=filter_variables)  # 👈 This is how we add the filters

    name = "Mr. Rabbit"  # picked up by `AutoExp` below

    # 👇 setting up the validations
    cls_validators = [
        ValidationDirective("title", exp="Your order"),
        ValidationDirective("name", exp=AutoExp, validator=CSSValidator("#name")),
    ]

    @mock.patch.dict(os.environ, di_mock_env)
    def test_it(self):
        try:
            # could come from Django test server, requests....
            http_response = get_fake_response_from_template(self)

            # "adapt" standard http_response by tracking content_type, status_code, headers...
            response = ResponseHTML(http_response)
            # Check validation such as content_type and status code
            self.check_expectations(response=response)
            # Regression test - did we get the same contents as the last time?
            tmp = self.assert_exp(response.content, "html")

        except (Exception,) as e:
            raise

    #################################################################
    # template and configuration
    #################################################################

    line1 = "Item 1"
    line2 = "Item 2"
    line3 = "Item 3"

    # the template used to generate the fake html
    template = """
<title>Your order</title>
<script>
const csrf_token = '{{csrf}}';
</script>
<body>
    Hi&nbsp;<span id="name">{{ name }}</span>&nbsp;!<br/> 
    It is now<span class="timestamp">{{ timestamp }}</span>.<br/>
    Your order is:
    <ul>
        <li class="orderline">{{line1}}</li>
        <li class="orderline">{{line2}}</li>
        <li class="orderline">{{line3}}</li>
    </ul>
</body>
    """


if __name__ == "__main__":

    cpdb = set_cpdb()
    rc = 0
    try:
        rc = unittest.main()
    finally:
        sys.exit(rc)
