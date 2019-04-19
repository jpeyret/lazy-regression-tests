from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
)


from lazy_regression_tests.utils import (
    _Filter,
    RemoveTextFilter,
    ppp,
    fill_template,
    Subber,
    RescueDict,
)

class FormatterRemoveFilter(_Filter):
    formatter_filter = True


class CSSRemoveFilter(FormatterRemoveFilter):
    pass

    



