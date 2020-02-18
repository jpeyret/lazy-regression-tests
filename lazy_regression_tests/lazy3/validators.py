import pdb
import sys
import re
import os

from operator import attrgetter

import logging

logger = logging.getLogger(__name__)

from lazy_regression_tests._baseutils import (
    debugObject,
    ppp,
    Dummy,
    getpath,
    InvalidConfigurationException,
)

from traceback import print_exc as xp


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    Union,
)


from lazy_regression_tests.utils import (
    nested_dict_get,
    first,
    fill_template,
    ppp,
    debug_write_validation_log,
)


#######################################################
# constants
#######################################################

verbose = "-v" in sys.argv

undefined = NotImplemented

# https://stackoverflow.com/questions/6102019/type-of-compiled-regex-object-in-python
# yeah, it is what it is, so be it...
type_regex_hack = re.compile("").__class__


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


class DoNotCheck:
    """use this to flag attributes that should not get checked """


class AutoExp:
    """ this class can be used to specify exp in 2 ways 

        at class level, `directive.exp is AutoExp` means that 

            directive.exp = getattr(testee, directive.name)

        at instance level `isistance(directive.exp, Autoexp)` will:

            for path in directive.exp.paths:
                try:

    """

    required = True

    @classmethod
    def get_exp_by_name(cls, testee, name):
        try:
            return getpath(testee, name)

        # pragma: no cover pylint: disable=unused-variable
        except (AttributeError,) as e:
            raise InvalidConfigurationException(
                "Attribute/Key %s not found on %s but expected via AutoExp.  either disable the validation or add this attribute"
                % (name, testee),
                ori=e,
            )

        # pragma: no cover pylint: disable=unused-variable

        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def get_exp(self, testee):
        try:

            for path in self.paths:
                try:
                    return getpath(testee, path)
                # pragma: no cover pylint: disable=unused-variable
                except (AttributeError,) as e:
                    pass
            else:
                # raise AttributeError(self.paths)
                raise InvalidConfigurationException(
                    "Attribute/Key %s not found on %s but expected via AutoExp.  either disable the validation or add this attribute"
                    % (self.paths, testee)
                )
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def __init__(self, paths: Union[list, tuple, str]):
        try:
            if isinstance(paths, tuple):

                self.paths = paths

            elif isinstance(paths, list):
                self.paths = tuple(list)

            elif isinstance(paths, str):
                self.paths = (paths,)

            else:
                TypeError("%s.__init__:paths should be tuple, list or str of str")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise


class OptAutoExp(AutoExp):
    required = False


#######################################################
# Validators
#######################################################


class Validator:
    """ base validator functionality 
    - get source during check_expectations, testee is used if sourcename is empty
    - retrieve got from get_value from the source
    - call a default assert exp == got
    """

    attrname: str
    sourcename: str

    def __repr__(self):
        return "%s[selector=%s]" % (
            self.__class__.__name__,
            getattr(self, "selector", "?"),
        )

    def __init__(self, selector, sourcename: Optional[str], scalar=True, cargo=None):
        try:
            self.selector = selector
            self.sourcename = sourcename
            self.scalar = scalar
            self.cargo = cargo

            assert isinstance(sourcename, str) or sourcename is None
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def get_source(self, testee, **sources):

        if self.sourcename is None:
            source_ = testee

        else:
            if "." in self.sourcename:
                try:
                    source_ = getpath(sources, self.sourcename)
                # pragma: no cover pylint: disable=unused-variable
                except (AttributeError,) as e:
                    raise ValueError(
                        "%s expects source:%s: which is not in the provided %s"
                        % (self, self.sourcename, ",".join(sources.keys()))
                    )
            else:
                try:
                    source_ = sources[self.sourcename]
                # pragma: no cover pylint: disable=unused-variable
                except (KeyError,) as e:
                    raise ValueError(
                        "%s expects source:%s: which is not in the provided %s"
                        % (self, self.sourcename, ",".join(sources.keys()))
                    )

        if source_ is None:
            raise ValueError(
                "you need to either pass in a dict in `source` or %s needs to have `%s` set"
                % (testee, self.sourcename)
            )
        return source_

    def get_value(self, source):
        res = source.get(self.selector)
        if rpdb() and res is None:  # pragma: no cover
            pdb.set_trace()
        return res

    def check(
        self,
        name: str,
        testee: "LazyMixin",
        exp: Any,
        sources: dict,
        t_message: str = None,
        source_: Any = None,
    ):
        """

        """

        try:

            source_ = source_ or self.get_source(testee, **sources)
            try:
                got = self.get_value(source_)
            # pragma: no cover pylint: disable=unused-variable
            except (KeyError, AttributeError) as e:
                logger.warning(
                    "%s.validation error: could not access data in source %s"
                    % (self, e)
                )
                # pdb.set_trace()
                got = undefined

            message = (
                fill_template(t_message, locals(), testee, self) if t_message else None
            )

            if isinstance(exp, type_regex_hack):
                self.test_regex(testee, exp, got, message, name=name)
                if verbose:
                    logger.info("%s checked %s" % (testee, self))

            elif not callable(exp):
                if "-v" in sys.argv:
                    print("\n\nvalidator.%s.checking(exp=%s,got=%s)" % (self, exp, got))
                self.test(testee, exp, got, message, name=name)
                if verbose:
                    logger.info("%s checked %s" % (testee, self))
                return got
            else:
                exp(testee=testee, got=got, validator=self)
                if verbose:
                    logger.info("%s checked %s" % (testee, self))
                return got
        except (AssertionError,) as e:  # pragma: no cover
            raise
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def test_regex(self, testee, exp, got, message, name=None):
        try:

            if message is None:
                message = fill_template(
                    "%(name)s pattern:%(pattern)s:does not match:%(got)s:got",
                    locals(),
                    exp,
                    self,
                    {"name": name or self},
                )

            testee.assertTrue(exp.search(str(got)), message)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def test(self, testee, exp, got, message, name=None):
        try:

            if exp is undefined:
                raise ValueError("exp is undefined")

            if message is None:
                message = fill_template(
                    "%(name)s exp:%(exp)s<>%(got)s:got",
                    locals(),
                    self,
                    {"name": name or self},
                )

            # correcting for unspecified scalars
            if not isinstance(exp, list) and isinstance(got, list) and len(got) == 1:
                got = first(got)

            testee.assertEqual(exp, got, message)
        # except (AssertionError,) as e:  # pragma: no cover
        #     raise

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class AttributeValidator(Validator):
    def __init__(self, selector, sourcename):
        super(AttributeValidator, self).__init__(selector, self.sourcename)
        self.f_getter = attrgetter(selector)

    def get_value(self, source_):
        try:
            res = self.f_getter(source_)
            if rpdb() and res is None:  # pragma: no cover
                pdb.set_trace()
            return res
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class FullyQualifiedNamesValidator(Validator):
    def __init__(self):
        Validator.__init__(self, self.selector, self.sourcename)


class DictValidator(Validator):
    def get_value(self, source_):
        """ get the value from  """
        try:
            res = nested_dict_get(source_, self.selector)
            return res
        except (KeyError,) as e:  # pragma: no cover
            raise
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class AttrNamedDictValidator(DictValidator):
    def __init__(self, selector):
        super(AttrNamedDictValidator, self).__init__(
            selector, scalar=True, sourcename=self.sourcename
        )


class MixinExpInGot:
    def test(self, testee, exp, got, message, name=None):

        if exp is undefined:
            raise ValueError("exp is undefined")
        try:

            if message is None:
                try:
                    message = "%s : exp:%s: is not in got:%s:" % (
                        name or self,
                        str(exp),
                        str(got),
                    )
                # pragma: no cover pylint: disable=unused-variable, broad-except
                except (Exception,) as ignore_:
                    # well, that didn't work
                    pass

            testee.assertTrue(str(exp) in str(got), message)
            if verbose:
                logger.info("%s checked %s" % (testee, self))

        # pragma: no cover pylint: disable=unused-variable
        except (AssertionError,) as e:
            pdb.set_trace()
            raise
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class NamedTesteeAttributeValidator(AttributeValidator):
    sourcename = None

    def __init__(self, selector=None):

        selector = selector or getattr(self, "selector", None)
        if selector is None:
            raise ValueError(
                "selector was not passed in and is not pre-set on class %s"
                % (self.__class__.__name__)
            )

        super(NamedTesteeAttributeValidator, self).__init__(
            selector, sourcename=self.sourcename
        )


#######################################################
# Managers
#######################################################


class ValidationDirective:
    def __repr__(self):
        return "%s:%s active:%s exp=%s with %s\n" % (
            self.__class__.__name__,
            self.name,
            self.active,
            (str(self.exp) if self.exp is not undefined else "undefined"),
            self.validator,
        )

    def __init__(self, name, validator=None, exp=None, active=None):
        try:
            self.name = name
            self.validator = validator
            self.exp = exp
            self.active = active

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def copy(self):
        return self.__class__(self.name, self.validator, self.exp, self.active)


class ValidationManager:
    def __repr__(self):

        if verbose:
            lines = ["  validators:"]
            lines += ["    %s" % str(val) for val in self.validators.values()]
            lines += ["  overrides:"]
            lines += ["    %s" % str(val) for val in self.overrides.values()]
            extra = "\n".join(lines)
        else:
            extra = ""

        return "%s%s" % (self.__class__.__name__, extra)

    def __init__(self, testee, *validator_managers):

        self.validators = {}

        self.overrides = {}

        for validatormgr in validator_managers:

            if isinstance(validatormgr, ValidationDirective):
                # remember, you need to copy shared directives because set_expectations modifies them
                self._add_baseline(validatormgr.copy())
            elif isinstance(validatormgr, ValidationManager):
                self.inject(validatormgr)

    def prep_validation(self, testee, names):
        try:

            for name in names:
                directive = self.validators[name]

                if directive.exp in (AutoExp, OptAutoExp):
                    try:
                        directive.exp = directive.exp.get_exp_by_name(testee, name)
                        continue
                    except (AttributeError,) as e:
                        if not directive.exp.required:
                            if not name in self.overrides:
                                logger.info("deactivating %s" % (name))
                                directive.active = False
                            else:
                                directive.exp = undefined
                            continue
                        raise

                elif isinstance(directive.exp, AutoExp):
                    try:
                        directive.exp = directive.exp.get_exp(testee)
                        continue
                    except (AttributeError,) as e:
                        if not directive.exp.required:
                            if not name in self.overrides:
                                logger.info("deactivating %s" % (name))
                                directive.active = False
                            else:
                                directive.exp = undefined
                            continue
                        raise

            if self.overrides:

                for name, override in self.overrides.items():
                    if not override.validator:

                        directive = self.validators[name]
                        if verbose:
                            logger.info("validator.ante:%s" % (directive))
                            logger.info("override      :%s" % (override))

                        directive.active = (
                            override.active
                            if override.active is not None
                            else directive.active
                        )
                        directive.exp = (
                            override.exp
                            if override.exp is not undefined
                            else directive.exp
                        )

                        if verbose:
                            logger.info("validator.post:%s" % (directive))

                    else:
                        self._add_baseline(override, name)
                        # raise NotImplementedError(
                        #     "%s.prep_validation(%s) with validator" % (self, locals())
                        # )

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def _get_names(
        self,
        seen: set,
        lazy_skip_except=None,
        lazy_skip=None,
        lazy_sourced_only: bool = True,
    ):

        try:

            keep_filter = None
            if lazy_skip_except:
                if isinstance(lazy_skip_except, str):
                    lazy_skip_except = [lazy_skip_except]

                if isinstance(lazy_skip_except, (dict, list, set)):

                    def keep_filter(name):
                        return name in lazy_skip_except

                elif isinstance(lazy_skip_except, type_regex_hack):

                    def keep_filter(name):
                        return bool(lazy_skip_except.search(name))

                else:
                    raise TypeError(
                        "lazy_skip_except supports dictionary, list, string, set and regex:.got(%s)"
                        % lazy_skip_except
                    )

            skip_filter = None
            if lazy_skip:
                if isinstance(lazy_skip, str):
                    lazy_skip = [lazy_skip]

                if isinstance(lazy_skip, (dict, list, set)):

                    def skip_filter(name):
                        return name in lazy_skip

                elif isinstance(lazy_skip, type_regex_hack):

                    def skip_filter(name):
                        return bool(lazy_skip.search(name))

                else:
                    raise TypeError(
                        "lazy_skip supports dictionary, list, string, set and regex:.got(%s)"
                        % lazy_skip
                    )

            res = []
            for name in self.validators:
                logname = name
                if name == "content_type":
                    directive = self.validators[name]
                    logname = "%s=%s" % (name, directive.exp)

                if skip_filter and skip_filter(name):
                    seen.add("%s.skipped" % (logname))
                    continue

                if keep_filter and not keep_filter(name):
                    seen.add("%s.skipped" % (logname))
                    continue
                res.append(name)

            return res

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

    def check_expectations(
        self,
        testee: "unittest.TestCase",
        lazy_skip=None,
        lazy_skip_except=None,
        lazy_sourced_only: bool = True,
        **sources,
    ):
        """
        loops through the validation directives and executives them if active
        errors if exp or validator is missing 
        :parm sources: a dictionary that provides data for each validator's sourcename
        note that a validator can leave sourcename empty which means testee is 
        the source
        :param lazy_sourced_only: use this if not all sources are ready yet

        """

        try:

            seen = set()
            names = self._get_names(
                seen=seen, lazy_skip_except=lazy_skip_except, lazy_skip=lazy_skip
            )

            self.prep_validation(testee, names)

            if verbose:
                print("🔬🧟‍♂️🧟‍♂️🧟‍♂️049.lazy.026.lazy3")

                if not hasattr(self, "fnp_val_log"):

                    dn_o = os.path.join(
                        os.environ["lzrt_template_dirname_got"], "v3.validations"
                    )

                    if not os.path.exists(dn_o):
                        os.makedirs(dn_o)

                    filename = testee.lazy_filename
                    # pdb.set_trace()
                    di_sub = dict(
                        filename=filename.rstrip("v3"),
                        dn_o=dn_o,
                        classname=testee.__class__.__name__,
                    )

                    t_fnp = "%(filename)s.%(classname)s.%(_testMethodName)s.txt"
                    self.fnp_val_log = os.path.join(
                        dn_o, fill_template(t_fnp, di_sub, testee)
                    )

            for name in names:
                directive = self.validators[name]

                logname = name
                if name == "content_type":
                    logname = "%s=%s" % (name, directive.exp)

                validator = directive.validator

                if not directive.active or directive.active is undefined:
                    logger.info("inactive %s" % (directive))
                    seen.add("%s.inactive" % (logname))
                    continue

                # sometimes, a test is done in several phases and not all sources are ready
                if lazy_sourced_only:
                    # takes into account dotted paths and empty sourcenames which point
                    # to testee
                    sourcename = (getattr(validator, "sourcename", "") or "").split(
                        "."
                    )[0]

                    if sourcename and not sourcename in sources:
                        logger.info("unsourced %s" % directive)
                        seen.add("%s.unsourced" % (logname))
                        continue

                if breakpoints(
                    "check_expectations", {"name": directive.name}
                ):  # pragma: no cover
                    pdb.set_trace()

                exp = directive.exp

                # maybe it's built into the validator?
                if exp is undefined:
                    exp = getattr(directive.validator, "exp", undefined)

                if exp is undefined:
                    # let's see if we can get it
                    exp = getattr(testee, directive.name, undefined)

                if exp is undefined:
                    raise ValueError("%s has undefined exp" % (directive))

                seen.add(logname)
                validator.check(name, testee, exp, sources)

            if verbose:
                debug_write_validation_log(self.fnp_val_log, seen)

        except (AssertionError,) as e:  # pragma: no cover
            raise
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def inject(self, validatormgr):

        for name, directive in validatormgr.validators.items():
            # remember, you need to copy shared directives because set_expectations modifies them
            self._add_baseline(directive.copy())

    def _add_baseline(self, directive, name=None):
        name = name or directive.name

        try:

            existing = self.validators.get(name)
            if existing:

                if verbose:
                    logger.info("_add_baseline:existing.ante:%s" % (directive))
                    # logger.info("                  directive:%s" % (override))

                if directive.active is not None:
                    existing.active = directive.active

                if directive.exp is not undefined:
                    existing.exp = directive.exp

                if directive.validator is not None:
                    existing.validator = directive.validator

                if verbose:
                    logger.info("_add_baseline:existing.post:%s" % (directive))

            else:
                self.validators[name] = directive

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def _add_override(self, directive, name=None):
        name = name or directive.name
        self.overrides[name] = directive

    def remove_expectation(self, name):
        """ set an expection's active to False, disabling it """
        try:
            self.set_expectation(name, active=False)
        except (KeyError,) as e:  # pragma: no cover
            logger.warning(e)
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def set_expectation(
        self,
        name,
        exp=undefined,
        validator: "Validator" = None,
        active: Optional[bool] = None,
    ):
        """ 
            note:  set_expectations is the instance-level method, add_directive works at class-level

            besides the name any of the other parameters can be unspecified
            however, come check_expectations, any `active` directive needs to 
            have a `validator` and `exp` set.

            :param name: logical name, ex: 'title'  it is used to allow successive
            adjustments to a given validation

            :param exp:  an expectation, which can pretty anything, a value, a regex to match, a callable...

            :param active: turns the expectation on and off.  left to None, it causes an error if unset


            going through the test hierarchy, each class copies expectations 
            from its mro and then qualifies them as needed.

            a test method has the final say, via `set_expectation`

            for example:

            class SuperClass(LazyMixin):
            #we want to check the title, but we don't know yet what any request is expected to return
                cls_validators = ValidationDirective("title", active=True, validator=CSSTitleValidator())

            class Test_1(Superclass):
                cls_validators = ValidationDirective("title", exp="Always Test1!")

                def test_different_after_all(self):
                    self.set_expectation("title","different title")

            class Test_DontWannaTestTitle(Superclass):
                cls_validators = ValidationDirective("title", active=False)

        """

        try:

            if validator is None:
                existing = self.validators.get(name)

                if active is None:
                    active = exp is not undefined

                if existing is None:

                    possibles = ",".join(list(self.validators.keys()))
                    msg = f"unknown check `{name}`.  known checks are `{possibles}` on `{self}.validators`"

                    if exp is undefined and active is False:
                        # deactivating an absent validator isn't a big deal
                        logger.warning("deactivating " + msg)
                        return

                    raise KeyError(msg)
                else:
                    self._add_override(
                        ValidationDirective(name, validator, exp, active)
                    )

            else:

                if active is None:
                    active = not (exp is undefined)

                self._add_override(ValidationDirective(name, validator, exp, active))

            if verbose:
                ppp(self, "after set_expectation")

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def add_directive(
        self,
        name: str,
        exp: Any = undefined,
        validator: Validator = None,
        active: Optional[bool] = None,
        sourcname: str = None,
        selector=None,
    ):
        """ hmmmm, looks a lot like set_expectations """

        try:

            # bit of shuffling around to fix likely config mistakes...
            if validator is None and isinstance(exp, Validator):
                validator = exp
                exp = undefined

            if isinstance(name, ValidationManager):
                for name, directive in name.validators.items():
                    # remember, you need to copy shared directives because set_expectations modifies them
                    self._add_baseline(directive.copy())
                return

            assert validator is None or isinstance(validator, Validator)

            assert not isinstance(exp, Validator)

            if active is None and exp is not undefined:
                active = True

            directive = ValidationDirective(name, validator, exp, active)
            self._add_baseline(directive)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if rpdb() or cpdb():
                ppp(locals())

                pdb.set_trace()
            raise


def build_validators_for_class(cls, li_revmro):
    """build filters for class, before instance overrides"""
    try:

        if rpdb():  # pragma: no cover
            pdb.set_trace()

        classname = cls.__name__
        print("\n\n👉build_validators_for_class cls.__name__:%s" % (classname))

        # breakpoints dont work for now as the class defs are an import time execution
        # not a call time execution
        if breakpoints(
            "build_filters_for_class", dict(classname=classname)
        ):  # pragma: no cover
            pdb.set_trace()

        final = []

        seen = set()

        for cls_ in li_revmro:

            validators = getattr(cls_, "cls_validators", None)

            if validators:
                # pdb.set_trace()
                print("validators:%s" % (validators))

                # now, what do we accept?
                if not isinstance(validators, list):
                    validators = [validators]

                validators = validators.copy()

                for validator in validators:
                    if not isinstance(
                        validator, (ValidationManager, ValidationDirective)
                    ):
                        raise ValueError(
                            "unexpected validation {validator} on class.{cls_.__name__}"
                        )

                    if not validator in seen:
                        final.append(validator)
                        seen.add(validator)

                # final.extend(validators)

        return final

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if 1 or cpdb():
            pdb.set_trace()
        raise
