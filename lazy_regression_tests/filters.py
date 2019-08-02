from lazy_regression_tests._baseutils import (
    set_cpdb,
    set_rpdb,
    ppp,
    debugObject,
)

import pdb
from bemyerp.lib.utils import set_cpdb, set_rpdb

def cpdb(**kwds) -> bool:   # pragma : no cover
    if cpdb.enabled == "once":
        cpdb.enabled = False # type : ignore
        return True
    return cpdb.enabled # type : ignore
cpdb.enabled = False # type : ignore



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
    raw_format_filter = True

class CSSRemoveFilter(FormatterRemoveFilter):

    def __init__(self, css, *args, **kwds):
        pdb.set_trace()
        self.css = css
        self.verbose = kwds.get("verbose")
        self.hitname = kwds.get("hitname")    

    def format(self, soup):
        try:
            pdb.set_trace()
            for hit in soup.select(self.css):
                hit.decompose()
            return soup
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    __call__ = format
