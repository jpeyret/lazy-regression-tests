""" docstring"""

from typing import Any, NamedTuple

import sqlalchemy
import polars as pl
import re

# pylint: disable=unused-import
from bemyerp.lib.utils import set_cpdb, set_rpdb, set_breakpoints3, cprint
# pylint: enable=unused-import
from bemyerp.lib.utils import fill_template, Subber

POLARS_ERR_DIM_MISMATCH = ('DataFrame dimensions do not match',)
LOG_PREFIX ="🐻‍❄️polars"


class co:
    from_ = "from"
    select = "select"
    distinct = "distinct"

    s_keywords = {from_,select,distinct}

#🎫105.framework.008.remove_v1v2_scaffolding.dead - shared utils w lazy
def find_columns_with_nulls(df : pl.DataFrame) -> list[str]:
    """return colnames with null data"""
    li_di = df.describe().filter(statistic="null_count").drop("statistic").to_dicts()
    need_fill = [k for k,v in li_di[0].items() if int(v)>0]
    return need_fill


#🎫105.framework.008.remove_v1v2_scaffolding.dead - shared utils w lazy
def fill_nulls(df : pl.DataFrame):
    try:
        need_fill = find_columns_with_nulls(df)

        schema = dict(**df.schema)

        todo = [(name,str(schema[name])) for name in need_fill]

        di_fill = dict(
            String = "",
            Int64 = 0,
            Int8 = 0,
            Int32 = 0,
            Float64 = 0.0,
            Boolean = False,
        )

        dfo = df

        for colname, typename in todo:
            filler = di_fill.get(typename)
            if filler is None:
                type_ = df.schema[colname]
                log("🧨polars_utils:fill_nulls({df.schema=}).  no filler for {colname} with {type_}",flog=logger.error)
                continue

            dfo = dfo.with_columns(pl.col(colname).fill_null(filler))



        return dfo



    #pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e: 
        if cpdb():
            breakpoint()
        raise



def get_colnames(sql : str) -> list[str]:
    """return colnames, taking into account aliases
    !!!TODO!!! : seems fragile to embedded spaces and commas :  `select ',' as sep `
    """
    try:

        
        tmp = sql.replace("\n"," ")
        patre = re.compile("\sfrom\s",re.IGNORECASE)

        #split off from clause
        tmp2 = patre.split(tmp)[0]

        #split by , then keep only last bit (which nets either aliases or colname)
        tmp3 = tmp2.split(",")
        tmp4 = [v.split()[-1] for v in tmp3]
        #skip keywords
        tmp5 = [v for v in tmp4 if v.lower() not in co.s_keywords]

        return tmp5

    #pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e: 
        if cpdb():
            breakpoint()
        raise



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
