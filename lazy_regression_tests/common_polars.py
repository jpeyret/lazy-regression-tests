""" docstring"""

import re
from datetime import date, datetime
from typing import Any, NamedTuple

import polars as pl
import sqlalchemy

#
#
from lazy_regression_tests._baseutils import Subber, fill_template

POLARS_ERR_DIM_MISMATCH = ('DataFrame dimensions do not match',)
LOG_PREFIX ="🐻‍❄️polars"


class co:
    from_ = "from"
    select = "select"
    distinct = "distinct"

    s_keywords = {from_,select,distinct}


def find_columns_with_nulls(df : pl.DataFrame) -> list[str]:
    """return colnames with null data"""
    li_di = df.describe().filter(statistic="null_count").drop("statistic").to_dicts()
    need_fill = [k for k,v in li_di[0].items() if int(v)>0]
    return need_fill


def fill_nulls(df : pl.DataFrame):
    """fill all columns having nulls"""
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
            Datetime = datetime(year=7777,month=7,day=7),
            Date = date(year=7777,month=7,day=7),
        )

        dfo = df

        for colname, typename in todo:
            typename = typename.split("(")[0]
            filler = di_fill.get(typename)
            if filler is None:
                continue
            dfo = dfo.with_columns(pl.col(colname).fill_null(filler))
        return dfo

    #pragma: no cover
    except (Exception,) as _e:
        if cpdb():
            breakpoint()
        raise


def get_colnames(sql : str) -> list[str]:
    """return colnames, taking into account aliases
    !!!TODO!!! : seems fragile to embedded spaces and commas and comments :  `select ',' as sep `
    """
    try:


        tmp = sql.replace("\n"," ")
        patre = re.compile("\sfrom\s",re.IGNORECASE)

        #split off from clause
        tmp2 = patre.split(tmp)[0]

        #split by , then keep only last bit (which nets either aliases or colname)
        tmp3 = [v2 for v in tmp2.split(",") if (v2:=v.strip())]
        tmp4 = [v.split()[-1] for v in tmp3]
        #skip keywords
        tmp5 = [v for v in tmp4 if v.lower() not in co.s_keywords]

        return tmp5

    #pragma: no cover
    except (Exception,) as _e:
        if cpdb():
            breakpoint()
        raise



def cpdb(*args, **kwargs):
    "disabled"

rpdb = breakpoints = cpdb


class PLReadSubber(Subber):

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


def prep_polars_query_params(
    tqry, *args, colnames : list[str]|None=None) -> tuple[str,dict[str,Any]]:
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
    #pragma: no cover
    except (Exception,) as _e:
        if cpdb():
            breakpoint()
        raise



def read_df(db : Any, tqry, *args, colnames : list[str]|None=None):
    try:


            # use :varname rather than %(varname)s coming in,
            # but also return a parameters dict as well as the select-clause aliases/colnames
            lo_tqry, parameters, colnames = prep_polars_query_params(tqry,*args, colnames=colnames)

            sqa_qry = sqlalchemy.text(lo_tqry)

            dftmp = pl.read_database(sqa_qry,db,execute_options={"parameters": parameters})

            renames = {old:new for old,new in zip(dftmp.schema.keys(),colnames)}
            df = dftmp.rename(renames)


            return df

    #pragma: no cover
    except (Exception,) as _e:
        if cpdb():
            breakpoint()
        raise

class SplitExists(NamedTuple):
    exists : pl.DataFrame
    not_exists : pl.DataFrame



def reorder_as_other(df : pl.DataFrame, other : pl.DataFrame) -> pl.DataFrame:
    "used for concats.  will not fix datatype errors"
    return df.select(other.columns)


def split_on_exist_notexist(
    df : pl.DataFrame, dfcheck : pl.DataFrame,
    on : Any, left_on =None, right_on=None) -> tuple[pl.DataFrame, pl.DataFrame]:
    """ split on an existance check

    df:1,2,3,4 dfcheck:1,3
        => (df:1,3 , df:2,4)



    """
    try:
        df_exists = df.join(dfcheck, on=on, left_on=left_on,right_on=right_on, how="semi")
        df_notexists = df.join(dfcheck, on=on, left_on=left_on,right_on=right_on, how="anti")

        return SplitExists(df_exists, df_notexists)
    #pragma: no cover
    except (Exception,) as _e:
        if cpdb():
            breakpoint()
        raise



def check_for_duplicates(df: pl.DataFrame, on: Any, stop = False, keys_only = False,keep_counts = False):
    """check for duplicates.  mostly for debugging"""
    try:
        dfdupekeys = df.group_by(on).count().sort("count",descending=True).filter(pl.col("count").gt(1))

        if keys_only:
            return dfdupekeys

        if not keep_counts:
            dfwithdupes, _ = split_on_exist_notexist(df, dfdupekeys, on=on)

        else:
            dfwithdupes = df.join(dfdupekeys,on=on)
            pass


        dfwithdupes = dfwithdupes.sort(on)



        if stop:
            with pl.Config(fmt_str_lengths=60,tbl_rows=20, tbl_cols = 20):
                print(dfwithdupes)  # debugging
                breakpoint()
                pass

        return dfwithdupes

    #pragma: no cover
    except (Exception,) as _e:
        if cpdb():
            breakpoint()
        raise
