from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
)

import pdb

def cpdb():
    return cpdb.enabled
cpdb.enabled = False


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

    def format(self, soup):
        try:
            for hit in soup.select(self.css):
                hit.decompose()
            return soup
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    __call__ = format
