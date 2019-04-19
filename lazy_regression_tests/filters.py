from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
)


from lazy_regression_tests.utils import (
    _Filter,
    RemoveTextFilter,
    DataMatcher,
    ppp,
    fill_template,
    Subber,
    RescueDict,
)

class FormatterRemoveFilter(DataMatcher):
    formatter_filter = True


class CSSRemoveFilter(FormatterRemoveFilter):

    def __init__(self, css, *args, **kwds):
        self.css = css
        self.verbose = kwds.get("verbose")
        self.hitname = kwds.get("hitname")    

    def filter(self, soup):
        try:
            raise NotImplementedError("filter(%s)" % (locals()))
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    __call__ = filter
