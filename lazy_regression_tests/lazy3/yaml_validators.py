from yaml import dump as ydump

from .filters import FilterManager

import pdb
from traceback import print_exc as xp


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


class YAMLFilter(FilterManager):
    """ note dont try to `prep(data)` on incoming yaml 
        the reason is that a dump in yaml will not safe_load back

    """

    def to_text(self, tmp, data):
        try:

            if isinstance(data, str):
                raise NotImplementedError("%s.to_text(data is a string)" % (self))

            return ydump(data, default_flow_style=False)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise
