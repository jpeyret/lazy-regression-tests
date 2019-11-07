from lazy_regression_tests._baseutils import set_cpdb, set_rpdb, ppp, debugObject

import pdb
from bemyerp.lib.utils import set_cpdb, set_rpdb

from traceback import print_exc as xp


def cpdb(**kwds) -> bool:  # pragma: no cover
    if cpdb.enabled == "once":
        cpdb.enabled = False  # type : ignore
        return True
    return cpdb.enabled  # type : ignore


cpdb.enabled = False  # type : ignore


from lazy_regression_tests.utils import (
    _Filter,
    RemoveTextFilter,
    DataMatcher,
    ppp,
    fill_template,
    Subber,
    RescueDict,
    NamesMatchTemp,
)


class FormatterRemoveFilter(DataMatcher):
    """ Remove Filters operate at the level of the raw data, before it is formatted to strings
        for example, the CSS Remove filters below expect to receive DOM-type data, like a BeautifulSoup
        a Dict-remover might prune keys out of an incoming dictionary
    """

    raw_format_filter = True


class DictKeyRemoveFilter(FormatterRemoveFilter):

    raw_format_filter = True

    def __init__(self, path, *args, **kwds):
        """
        path is assumed to be in the form "a" or "a.b" where "a" means `dict_.pop("a", None)`
        and "a.b" means `dict_.get("a",{}).pop("b", None)`
        """
        self.path = path
        self.verbose = kwds.get("verbose")
        self.hitname = kwds.get("hitname")
        self.temp = NamesMatchTemp()

    def format(self, dict_, lazytemp, **kwds):
        try:
            keys_ = self.path.split(".")
            li_approach, final = keys_[0:-1], keys_[-1]
            di = dict_
            for key_ in li_approach:
                di = di.get(key_, {})
                if not di:
                    return dict_

            removed = di.pop(final, None)

            if self.hitname:
                lazytemp.notify(removed, self)

            return dict_

        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise


class CSSRemoveFilter(FormatterRemoveFilter):
    """ removes CSS matches """

    def __repr__(self):
        return "%s.%s[hitname:%s]:selector:%s" % (
            self.__module__,
            self.__class__.__name__,
            self.hitname,
            self.css,
        )

    def __init__(self, css, *args, **kwds):
        self.css = css
        self.verbose = kwds.get("verbose")
        self.hitname = kwds.get("hitname")
        self.temp = NamesMatchTemp()

    def format(self, soup, lazytemp, **kwds):

        try:

            if not hasattr(lazytemp, "soup"):  # 👈!!!TODO!!! 049.lazy.021.p4.v2 - hack
                lazytemp.soup = soup

            for hit in soup.select(self.css):

                if self.hitname:
                    lazytemp.notify(hit, self)

                hit.decompose()

            return soup
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    __call__ = format
