from typing import Any, Callable
import lazy_regression_tests.providers as providers
from lazy_regression_tests.common import LazyTemp, ConfigurationException, Checker, Validator, ValidatorMgr

import unittest

from pathlib import Path


import polars as pl

from lazy_regression_tests.common import ValidatorTemp, BFilter

from lazy_regression_tests.common_polars import find_columns_with_nulls, fill_nulls, read_df, check_for_duplicates

from bemyerp.websec.log_settings import getLogger

import bemyerp.pssystem.constants as dbgconstants

def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"

LOG_PREFIX ="🐻‍❄️polars"

POLARS_ERR_DIM_MISMATCH = ('DataFrame dimensions do not match',)

rpdb = breakpoints = cpdb


undefined = NotImplemented


logger = getLogger(__name__, "debuglog")

FLOG = logger.warning

def log(msg, *args, flog=None, **kwargs): #custom lazy
    flog = flog or FLOG
    flog(f'{LOG_PREFIX}{msg}', *args, **kwargs)



class ValidatorTempPolars(ValidatorTemp):
    "adjust for polars.DataFrame"

    compare : pl.DataFrame

    _data_in = undefined
    @property
    def data_in(self):
        return self._data_in

    @data_in.setter
    def data_in(self, value):
        try:
            self.checker.provider.set_data(self.checker, self, value)
            if value is not None:
                assert isinstance(value, pl.DataFrame)
                assert isinstance(self.rawdata, pl.DataFrame)
                assert isinstance(self.data_in, pl.DataFrame)
            
        #pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: 
            if cpdb():
                breakpoint()
            raise
        
    @property
    def filtered(self):
        return self.data_in


from typing import Type

    
class Diffs:

    # def __set_name__(self, owner, name):
    #     self.name = name

    def __get__(self, inst, objtype=None):
        ...
        return inst.df.filter(
            pl.col("_lazydiff_compare").str.contains_any(["<",">"])
        )

    # def __set__(self, obj, value):
    #     ...

    

class DiffView:

    diff = Diffs()

    def __init__(self,df) -> None:
        self.df = df

    


def view_diffs(testee, source):
    df = get_diffs(source)
    if df is not None:

        with pl.Config(fmt_str_lengths=120,tbl_rows=20):

            print(df.group_by("_lazydiff_compare").count())

            print(df)
            dv = DiffView(df)

            breakpoint() #🛑
            pass            



class Polars_Provider(providers.PAbstractExtProvider):
    """compare and validate polars.DataFrame"""

    text_based = False

    TYPE_RAW = pl.DataFrame

    def prep_rawdata(self, checker: "Checker", data: pl.DataFrame) -> pl.DataFrame:
        """convert data if needed"""
        try:
            assert isinstance(data,pl.DataFrame), f"only polars.DataFrame are supported.  {type(data)=}"
            return data
        #pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: 
            if cpdb():
                breakpoint()
            raise
        
    cls_temp = ValidatorTempPolars


    @classmethod
    def datain_to_str(cls, data: pl.DataFrame, checker: "Checker", temp: LazyTemp = None) -> pl.DataFrame:
        """data to str"""
        try:
            assert isinstance(data,pl.DataFrame), f"only polars.DataFrame are supported.  {type(data)=}"
            log(f"{cls}.datain_to_str.  conversion to str is not supported. returning unchanged as {type(data)}",flog=logger.info)
            return data
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise



    def build_filter(self, v_in: Any) -> BFilter:
        "build filter"
        try:
            log(f"{type(self)}.build_filter: filtering is not yet supported")
            assert isinstance(self.data_in,pl.DataFrame), f"only polars.DataFrame are supported.  {type(self.data_in)=}"
            self._filtered = self.data_in
            # return self
        #pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: 
            if cpdb():
                breakpoint()
            raise


    #🎫004.lazy.052.polars_diffing - modify to pass in Checker, in order to access ValidatorMgr.config...
    def assert_equal(
        self, checker : "Checker", testee: unittest.TestCase, exp : pl.DataFrame, got: pl.DataFrame, message = None, **kwargs
    ) -> bool:


        """check if exp can be considered equal"""
        try:

            assert isinstance(exp, pl.DataFrame)
            assert isinstance(got, pl.DataFrame)

            #what are the join keys for polars equivalence check?

            join_on = kwargs.get("join_on")
            if not join_on:

                config = kwargs.get("config") or checker.v.config
                if callable(config):
                    config = config(testee)


                join_on = config["join_on"]

            colstatus = "_lazydiff_compare"

            df_compare = compare_df(df0=exp,df1=got,colkey=join_on, colstatus=colstatus)

            check = LazyCompareOptions()
            is_equal, msg = check.is_same(df_compare, compare_df_options, colstatus)

            checker.temp.compare = df_compare

            if not is_equal:
                checker.temp.errors["assert_equal"] = df_compare
        
            testee.assertEqual(True, is_equal, msg)


        # pragma: no cover pylint: disable=unused-variable
        except (AssertionError,) as e:
            raise

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                breakpoint()
            raise

    def write(self, fnp : str|Path, data : pl.DataFrame, header : Any = None):
        if header:
            print(f"{self}.write:{header=} not supported:ignoring")
        data.write_parquet(fnp)
        
    def read(self, fnp : str|Path) -> pl.DataFrame:
        df = pl.read_parquet(fnp)
        return df

    def adjust_value_for_validation(
        self,
        checker: "Checker",
        validator: "Validator",
        fn: Callable,
        value: Any,
        exc: Exception = None,
    ):
        return value



def check_unique(data : pl.DataFrame, testee : "unittest.TestCase", validator : Validator) -> bool:
    """check that a dataframe is unique on its keys"""
    try:

        if not len(data):
            log(f"check_unique({data=}) is empty",flog=logger.warning)
            return True

        keys = validator.mgr.config["join_on"]
        df_dupekeys : pl.DataFrame = data.group_by(keys).count().sort("count",descending=True).filter(pl.col("count").gt(1))

        if len(df_dupekeys) > 0:
            df_dupes = data.join(df_dupekeys, on=keys, how="semi").sort(keys)
            validator.mgr.temp.errors[validator.name] = df_dupes
            testee.assertFalse(f"{len(df_dupekeys)} duplicate rows", df_dupes)

        return True
    #pragma: no cover pylint: disable=unused-variable
    except (AssertionError,) as e: 
        e.args += (df_dupekeys,)
        raise
    #pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e: 
        if cpdb():
            breakpoint()
        raise

class compare_df_options:
    status_left = "<<"
    status_right = ">>"
    status_leftdiff = "< "
    status_rightdiff = "> "
    status_same = "__"

    # internal computationn column names
    csame = "__compare_df_same"
    cindex = "__compare_df_index"
    cdebug = "__compare_df_debug"

    fill_nulls = True


    @classmethod
    def get_counts(cls, df : pl.DataFrame, colstatus : str) -> "CompareCounts":
        """move from symbols in the status column to a name-based.  i.e `<<` become `left` `<` `leftdiff` """
        try:
            di_symbol_count = {}
            total = -1
            di_name_symbol = {name.removeprefix("status_"):val for name,val in vars(cls).items() if name.startswith("status_")}
            if df is not None:          
                total=len(df)
                df_counts = df.group_by(colstatus).count().rename({colstatus:"status"})

                di_symbol_count = {di["status"] : di["count"] for di in df_counts.to_dicts()}

            di_status = {name :  di_symbol_count.get(symbol,0) for name,symbol in di_name_symbol.items()}
            res = CompareCounts(**di_status, total=total)

            return res            


        #pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: 
            if cpdb():
                breakpoint()
            raise



def compare_df(
    df0: pl.DataFrame,
    df1: pl.DataFrame,
    colkey: str | tuple[str],
    colstatus: str,
    options: Type[compare_df_options] = compare_df_options,
    exclude_compare: list[str] | str | None = None,
    alias_left : str = "",
    alias_right : str = ""
) -> pl.DataFrame:
    """

        🧨🧨🧨 - nulls always return False when compared in df0 == df1.  caller needs to prefill with no-data values, other than null. otherwise those rows are LOST

        given two dataframes of identical shape, will use column (s?) `colkey` to determine differences which will be flagged in column `colstatus`

    colkey:    directory,
    colstatus: status,
    df0:
    ┌───────────┬─────┐
    │ directory ┆ foo │
    │ ---       ┆ --- │
    │ str       ┆ i64 │
    ╞═══════════╪═════╡
    │ a         ┆ 1   │
    │ b         ┆ 12  │
    │ c         ┆ 3   │
    └───────────┴─────┘,
    df1:
    ┌───────────┬─────┐
    │ directory ┆ foo │
    │ ---       ┆ --- │
    │ str       ┆ i64 │
    ╞═══════════╪═════╡
    │ a         ┆ 1   │
    │ b         ┆ 22  │
    │ d         ┆ 4   │
    └───────────┴─────┘,

    =>

    ┌───────────┬─────┬────────┐
    │ directory ┆ foo ┆ status │
    │ ---       ┆ --- ┆ ---    │
    │ str       ┆ i64 ┆ str    │
    ╞═══════════╪═════╪════════╡
    │ a         ┆ 1   ┆ _      │
    │ b         ┆ 12  ┆ <      │
    │ b         ┆ 22  ┆ >      │
    │ c         ┆ 3   ┆ <<     │
    │ d         ┆ 4   ┆ >>     │
    └───────────┴─────┴────────┘

    """

    # check for empty dataframe on either side
    lendf0 = len(df0)
    lendf1 = len(df1)
    if lendf0 and not lendf1:
        res = df0.with_columns(pl.lit(options.status_left).alias(colstatus))
        return res 
    if lendf1 and not lendf0:
        res = df0.with_columns(pl.lit(options.status_right).alias(colstatus))
        return res 
    
    if not lendf0 and not lendf1:
        return df0


    def logerr(msg, *args,**kwargs):
        msg = f"⚙️🧨⚙️🧨⚙️🧨 compare_df {msg}"
        eprint(msg,*args,**kwargs)

    
    oi = False
    if breakpoints("df_compare", {"always": 1}):  # pragma: no cover
        print(f"\n\n🔬🔬🔬always:{1}")
        oi = True
        breakpoint()
        pass

    if exclude_compare:
        if isinstance(exclude_compare, str):
            exclude_compare = [exclude_compare]
    else:
        exclude_compare = []

    if isinstance(colkey, str):
        colkey = [colkey]

    #catch a tuple...
    colkey = list(colkey)

    try:

        dfdiff = None

        # first things first, Struct fields need different handling on nulls...
        if options.fill_nulls:
                colnames_w_nulls = set(find_columns_with_nulls(df0) + find_columns_with_nulls(df1))
                colnames_struct_w_nulls = {colname for colname in colnames_w_nulls if isinstance(df0.schema.get(colname),(pl.Struct,))}
                if oi:
                    breakpoint() #🛑
                    pass
                df0 = df0.unnest(colnames_struct_w_nulls)
                df1 = df1.unnest(colnames_struct_w_nulls)

        # isolate rows on only one side...
        dfonly0 = df0.join(df1, on=colkey, how="anti").with_columns(pl.lit(options.status_left).alias(colstatus))
        dfonly1 = df1.join(df0, on=colkey, how="anti").with_columns(pl.lit(options.status_right).alias(colstatus))

        excludes = colkey + [options.cindex, colstatus] + exclude_compare

        # now identify common rows, on either side
        dfboth0 = df0.join(df1, on=colkey, how="semi").sort(colkey)
        dfboth1 = df1.join(df0, on=colkey, how="semi").sort(colkey)


        #check the shapes...
        if not (dfboth0.shape == dfboth1.shape):

            if not len(dfboth0) == len(dfboth1):
                df_dup0 = check_for_duplicates(df0, on=colkey, keys_only=True)
                df_dup1 = check_for_duplicates(df1, on=colkey, keys_only=True)

                msg = ""
                if len(df_dup0):
                    msg += f"df0[{df0.shape}] has {len(df_dup0)} duplicate rows on {colkey}"
                if len(df_dup1):
                    msg += f"df1[{df1.shape}] has {len(df_dup1)} duplicate rows on {colkey}"

                raise CompareException(msg)

            else:

                raise CompareException(f" shape mismatch {df0.shape=}<>{df1.shape}:")



        try:

            # df7 = df6.with_columns(pl.col(cosided.visright).fill_null(0))
            # import polars.selectors as cs
            # dfboth000 = dfboth0.with_columns(pl.col(cs.numeric)).fill_null(0)


            if options.fill_nulls:


                # ok, thing is 
                #🎫004.lazy.060.batch_diffing_polars
                dfboth0 = fill_nulls(dfboth0)
                dfboth1 = fill_nulls(dfboth1)


            # flag differences, and keep track of their indexes
            dfdiff = (dfboth0 == dfboth1).with_row_index(name=options.cindex)

        #pragma: no cover pylint: disable=unused-variable
        except (ValueError,) as e: 

            chk = POLARS_ERR_DIM_MISMATCH
            if e.args == chk:
                # marker invalid dimensions which probably indicates non-unique on colkeys

                errlines = [f"compare_df duplicate keys on {colkey=}", "{e}"]

                # marker invalid dimensions which probably indicates non-unique on colkeys
                for name, alias in zip("df0 df1".split(), (alias_left, alias_right)):
                    df = locals()[name]
                    dfdupes = df.group_by(colkey).count().sort("count",descending=True).filter(pl.col("count").gt(1))

                    if (totlen:=len(dfdupes)):
                        li = list(dfdupes.head().iter_rows(named=1))


                        logerr("")
                        msg = f"{alias or name} has dupes : first {len(li)} / {totlen} "
                        errlines.append(msg)
                        logerr(f"{msg}")
                        li = list(dfdupes.head().iter_rows(named=1))
                        for di in li:
                            info = f"  {di}"
                            logerr(info)
                            errlines.append(info)
                        logerr("")


                if cpdb():
                    breakpoint()
                raise CompareException("\n".join(errlines))

        # bring in the indexes which would have confused the comparison above with multiple occurences
        dfboth0 = dfboth0.with_row_index(name=options.cindex)
        dfboth1 = dfboth1.with_row_index(name=options.cindex)

        res = None

        if dfdiff is not None:

            # flag differences across any of the non-work columns.  careful:  nulls will always compare False
            dfdiff = dfdiff.with_columns(pl.all_horizontal(pl.col("*").exclude(*excludes)).alias(options.csame))



            # OK, now who had differences and who was the same?
            dfdiffsame = dfdiff.filter(pl.col(options.csame) == True)
            dfdiffdiff1 = dfdiff.filter(pl.col(options.csame) == False)
            #grrrr... nulls...
            dfdiffdiff2 = dfdiff.filter(pl.col(options.csame).is_null())

            dfdiffdiff = pl.concat([dfdiffdiff1,dfdiffdiff2])

            assert len(dfdiff) == len(dfdiffsame) + len(dfdiffdiff), "losing rows from dfdiff"

            # if they are the same, doesn't matter which dataframe you get them from...  maybe parameter that as pick from df0, pick from df1
            dfsame = (
                dfboth0.join(dfdiffsame, on=options.cindex, how="semi")
                .drop(options.cindex)
                .with_columns(pl.lit(options.status_same).alias(colstatus))
            )

            # now bring back sides of the difference
            dfdiff0 = (
                dfboth0.join(dfdiffdiff, on=options.cindex, how="semi")
                .with_columns(pl.lit(options.status_leftdiff).alias(colstatus))
                .drop(options.cindex)
            )
            dfdiff1 = (
                dfboth1.join(dfdiffdiff, on=options.cindex, how="semi")
                .with_columns(pl.lit(options.status_rightdiff).alias(colstatus))
                .drop(options.cindex)
            )

            res = pl.concat([dfonly0, dfonly1, dfsame, dfdiff0, dfdiff1]).sort(colkey + [colstatus])


        return res

    # pragma: no cover pylint: disable=unused-variable
    #pragma: no cover pylint: disable=unused-variable
    except (CompareException,) as e: 
        # breakpoint() #🛑
        pass
        raise
    except (Exception,) as e:
        if cpdb():
            breakpoint()
        raise

#🎫105.framework.008.remove_v1v2_scaffolding.dead - move to lazy
class CompareException(AssertionError):
    ...

from dataclasses import dataclass

@dataclass 
class CompareCounts:
    """represent compare count data by name and number, starting from a status column"""
    left : int
    right : int
    leftdiff : int
    rightdiff : int 
    same : int
    total : int

    is_equal : bool = None

    def __post_init__(self):
        self.is_equal = (self.same == self.total)




class LazyCompareOptions(compare_df_options):

    _lookup = undefined

    identity_status = "same"
    identity = "identity"
    
    @property
    def lookup(self):
        try:

            prefix = "status_"
            res = {}

            if type(self)._lookup is undefined:
                keys = [(k,v) for k,v in vars(compare_df_options).items() if k.startswith(prefix)]
                for key, value in keys:
                    meaning = key.removeprefix(prefix)
                    if meaning == self.identity_status:
                        res[self.identity] = value

                    res[meaning] = value

                type(self)._lookup = res
            return type(self)._lookup
        #pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: 
            if cpdb(): 
                breakpoint()
            raise
    


    def is_same(self, df : pl.DataFrame, compare_df_options : Type[compare_df_options], colstatus : str) -> tuple[bool,str]:
        try:

            counts = compare_df_options.get_counts(df, colstatus)
            return counts.is_equal, str(counts)
            
        #pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: 
            if cpdb():
                breakpoint()
            raise
        
def get_diffs(source : ValidatorMgr|ValidatorTemp|Checker) -> pl.DataFrame|None:
    try:
        temp = None
        if isinstance(source, ValidatorTemp):
            temp = source
        elif isinstance(source, (Validator,Checker)):
            temp = source.temp

        errors = getattr(temp, "errors", None) or {}

        diff = errors.get("assert_equal")
        if diff is not None and isinstance(diff,pl.DataFrame):
            return diff

        



    #pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e: 
        if cpdb():
            breakpoint()
        raise


providers.di_ext_provider["parquet"] = Polars_Provider()
