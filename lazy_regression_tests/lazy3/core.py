import pdb

from pathlib import Path

undefined = NotImplemented


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb

from lazy_regression_tests._baseutils import debugObject, ppp, Dummy

from traceback import print_exc as xp

from .validators import ValidationManager, NamedTesteeAttributeValidator


class _LazyMeta(type):
    def __new__(mcls, name, bases, attrs, **kwargs):
        cls_ = super(_LazyMeta, mcls).__new__(mcls, name, bases, attrs)
        return cls_

    def __init__(cls, name, bases, attrs, **kwargs):
        """ 
        intercepting the newly created class allows stacking of the 
        ancestral validators and formatters in reverse mro order
        i.e. top of ancestors go first

        👆 TODO: filters too

        """

        try:

            # we want to build out the validators by running the basic ancestral ones first
            # ex:  check status=200 and content_type = html before checking <title>
            li_bases2current = reversed(cls.mro())

            # pick _this_ class's validators
            li_ori = getattr(cls, "cls_validators", [])
            if li_ori and not isinstance(li_ori, list):
                li_ori = [li_ori]
            else:
                li_ori = li_ori.copy()

            li_new = []

            # and now add the bases' validators
            for basecls in li_bases2current:
                validators = getattr(basecls, "cls_validators", [])

                if validators:
                    if not isinstance(validators, list):
                        validators = [validators]
                    li_new.extend(validators)

            cls.cls_validators = li_new + li_ori

            #!!!TODO!!! 049.lazy.026.lazy3 👇
            # add same for filters, by extension

            #!!!TODO!!! 049.lazy.026.lazy3 👆

            return super().__init__(name, bases, attrs)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class LazyMixin(metaclass=_LazyMeta):
    cls_filters = {}
    cls_validators = []
    add_lazy_dirname = []

    lazytemp = None

    @classmethod
    def get_basename(cls, name_, file_, module_):
        cls.lazy_pa = pa = Path(file_)
        return pa.stem

    #######################################################
    # dubious
    #######################################################

    def preformat(self, data, options: "LazyCheckerOptions"):

        pdb.set_trace()

        return  # 🧨049.lazy.026.lazy3

        try:

            env = self.lazy_environ
            if not self.lazy_environ.acquired:
                env.clear()
                env.acquire(self.ENVIRONMENT_VARNAME_ROOT)

            self.control = control = _Control(self, env, options)

            tmp = self.lazytemp = self.lazytemp or LazyTemp(control, env, self)

            # 🤔 ahhh, but we need this to BeautifulSoup or do other stuff...
            return options.format(tmp, data)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    #######################################################
    # validator related
    #######################################################

    _validationmgr = undefined

    @property
    def validationmgr(self):
        if self._validationmgr is undefined:
            res = None
            self._validationmgr = res = ValidationManager(self, *self.cls_validators)

        return self._validationmgr

    def check_expectations(self, **sources):
        try:
            self.validationmgr.check_expectations(self, **sources)
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def set_expectation(self, *args, **kwargs):
        validationmgr = self.validationmgr

        name = args[0]
        if breakpoints("set_expectation", {"name": name}):  # pragma: no cover
            pdb.set_trace()

            # put this in your breakpoints.json

        validationmgr.set_expectation(*args, **kwargs)


class LazyCheckerOptions:
    pass
