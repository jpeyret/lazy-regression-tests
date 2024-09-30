""" docstring"""

from typing import Any, NamedTuple

import sqlalchemy
import polars as pl

# pylint: disable=unused-import
from bemyerp.lib.utils import set_cpdb, set_rpdb, set_breakpoints3, cprint
# pylint: enable=unused-import
from bemyerp.lib.utils import fill_template, Subber

POLARS_ERR_DIM_MISMATCH = ('DataFrame dimensions do not match',)
LOG_PREFIX ="🐻‍❄️polars"



def cpdb(*args, **kwargs):
    "disabled"

rpdb = breakpoints = cpdb


class PLReadSubber(Subber): # !!!TODO!!! move to polars_utils

    prefix = ":"

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._data = {}

    def __getitem__(self, keyname):

        res = f"{self.prefix}{keyname}"

        self._data[keyname] = super().__getitem__(keyname)
    
        return res


    def as_dict(self):
        return self._data


class PolarsPrepared(NamedTuple):  # !!!TODO!!! move to polars_utils
    """ tqry_for_polars : %(varname)s gets replaced with :varname 
        parameters      : {"varname" : somevalue }"""
    tqry_for_polars : str
    parameters_for_polars : dict[str,Any]
    colnames : list[str]


def prep_polars_query_params(tqry, *args, colnames : list[str]|None=None) -> tuple[str,dict[str,Any]]: # !!!TODO!!! move to polars_utils
    """
    formats the query to conform to pl.read_database requirements i.e. :varname
    preps all %(var)s as a dict  {<varname> :  <value>}
    """
    try:
        subber = PLReadSubber(*args)
        if colnames is None:
            colnames = get_colnames(tqry)
        tqry_for_polars = fill_template(tqry, subber)
        parameters_for_polars = subber.as_dict()
        return PolarsPrepared(tqry_for_polars,parameters_for_polars,colnames)
    #pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e: 
        if cpdb():
            breakpoint()
        raise



def read_df(db : Any, tqry, *args, colnames : list[str]|None=None):
    try:


            # use :varname rather than %(varname)s coming in, but also return a parameters dict as well as the select-clause aliases/colnames
            lo_tqry, parameters, colnames = prep_polars_query_params(tqry,*args, colnames=colnames)

            sqa_qry = sqlalchemy.text(lo_tqry)

            dftmp = pl.read_database(sqa_qry,db,execute_options={"parameters": parameters})

            renames = {old:new for old,new in zip(dftmp.schema.keys(),colnames)}
            df = dftmp.rename(renames)


            return df

    #pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e: 
        if cpdb():
            breakpoint()
        raise
