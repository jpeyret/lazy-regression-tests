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

from .common import *


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


from lazy_regression_tests.utils import nested_dict_get, first, fill_template, ppp


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

    def __repr__(self):
        return "%s[%s]" % (self.__class__.__name__, getattr(self, "paths", ""))

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

    def __init__(
        self, selector, sourcename: Optional[str] = None, scalar=True, cargo=None
    ):
        try:
            self.selector = selector
            if sourcename:
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
        if self.selector is None:
            return source
        else:
            res = source.get(self.selector)
        if rpdb() and res is None:  # pragma: no cover
            pdb.set_trace()
        return res

    def check(self, name: str, testee: "LazyMixin", exp: Any, sources: dict):
        """

        """

        try:

            source_ = self.get_source(testee, **sources)
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

            t_message = getattr(self, "t_message", None)
            message = (
                fill_template(t_message, locals(), testee, self) if t_message else None
            )

            if isinstance(exp, type_regex_hack):
                self.test_regex(testee, exp, got, message, name=name)

            elif not callable(exp):
                self.test(testee, exp, got, message, name=name)
                return got
            else:
                exp(testee=testee, got=got, validator=self)
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

            if not isinstance(got, (list, set)):
                testee.assertTrue(exp.search(str(got)), message)
            else:
                for igot in got:
                    hit = exp.search(str(igot))
                    if hit is None:
                        message = f"validation:{name or ''} failure: data:'{str(igot)}': does not match regex:'{exp.pattern}':"
                        testee.fail(message)

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

    sourcename = "data"

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


class DirectValidator(AttributeValidator):
    """ this is intended to check attributes/data on unittest.Testcase instance """

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


NamedTesteeAttributeValidator = DirectValidator


#######################################################
# Managers
#######################################################


class ValidationDirective:
    def __repr__(self):

        try:

            exp = getattr(self, "exp", undefined)
            if exp is undefined:
                exp = "undefined"
            elif isinstance(exp, type):
                exp = exp.__name__
            else:
                exp = str(exp)

            return f"{self.__class__.__name__:20.20}:{self.name:30.30} active:{self.active} exp:{exp:30.30}"

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            return self.__class__.__name__

    def __init__(
        self,
        name: str,
        validator: Optional[Validator] = None,
        exp=None,
        active: Optional[bool] = None,
    ):
        try:
            self.name = name
            self.validator = validator
            self.exp = exp

            # if we know exp and we have a validator
            # assume active unless it has been set to True or False
            if active is None and exp and validator:
                active = True

            assert validator is None or isinstance(validator, Validator)

            self.active = active

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if 1 or cpdb():
                pdb.set_trace()
            raise

    def copy(self):
        return self.__class__(self.name, self.validator, self.exp, self.active)


class ValidationManager:
    def __repr__(self):

        extra = f" for {self.testee}"

        if verbose:

            lines = ["", "  validators:"]
            lines += ["    %s" % str(val) for val in self.validators.values()]
            extra += "\n".join(lines)

        return "%s%s" % (self.__class__.__name__, extra)

    def __init__(self, testee, *validator_managers):

        self.validators = {}
        self.testee = testee

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
                            directive.active = False
                            continue
                        raise

                elif isinstance(directive.exp, AutoExp):
                    try:
                        directive.exp = directive.exp.get_exp(testee)
                        continue
                    except (AttributeError,) as e:
                        if not directive.exp.required:
                            directive.active = False
                            continue
                        raise

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

            name = validator = None

            self.prep_validation(testee, names)

            for name in names:
                directive = self.validators[name]

                logname = name
                if name == "content_type":
                    logname = "%s=%s" % (name, directive.exp)

                validator = directive.validator

                if not directive.active or directive.active is undefined:
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
                        seen.add("%s.unsourced" % (logname))
                        continue

                exp = directive.exp

                # maybe it's built into the validator?
                if exp is undefined:
                    exp = getattr(directive.validator, "exp", undefined)

                if exp is undefined:
                    # let's see if we can get it
                    exp = getattr(testee, directive.name, undefined)

                if exp is undefined:
                    raise InvalidConfigurationException(
                        "%s has undefined exp" % (directive)
                    )

                seen.add(logname)
                validator.check(name, testee, exp, sources)

        except (AssertionError,) as assert_exc:  # pragma: no cover
            format_assertion_error(self, assert_exc, validator=validator, name=name)
            raise
        # pragma: no cover pylint: disable=unused-variable, broad-except
        except (Exception,) as e:  #
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

                if directive.active is not None:
                    existing.active = directive.active

                if directive.exp is not undefined:
                    existing.exp = directive.exp

                if directive.validator is not None:
                    existing.validator = directive.validator

            else:
                self.validators[name] = directive

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if cpdb():
                pdb.set_trace()
            raise

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


        """

        try:

            if validator is not None:
                if not isinstance(validator, Validator):
                    raise InvalidConfigurationException(
                        "%s. validator %s is not an instance of Validator"
                        % (name, validator)
                    )

            return self.add_directive(
                name=name, exp=exp, validator=validator, active=active, final=True
            )

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
        final=False,
    ):
        """ hmmmm, looks a lot like set_expectations """

        try:

            if isinstance(name, ValidationDirective):
                self._add_baseline(name)
                return

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

    def debug(self):
        try:
            padder = "⚙️" * 6 + "  lazy-tests configuration  " + "⚙️" * 6
            print(f"\n{padder}\n{self}  validators:")
            for key in self.validators:
                value = self.validators[key]
                print(
                    f"  {key:20.20}: active:{value.active} exp:{str(value.exp) if not isinstance(value.exp, type) else value.exp.__name__:10.10} {value.validator.__class__.__name__:30.30}"
                )

            li_revmro = list(reversed(self.testee.__class__.mro()))

            li_info = [
                f"{cls.__module__}.{cls.__name__}"
                for cls in li_revmro
                if getattr(cls, "cls_validators", None)
            ]

            print("\n\n ⚙️class-level inheritance:\n%s\n" % "\n".join(li_info))

            for cls in li_revmro:
                cls_validators = getattr(cls, "cls_validators", None)
                # print(f" {cls.__name__}:{cls_validators}")
                if cls_validators:
                    print(f"\nfrom class {cls.__name__}:")
                    if isinstance(cls_validators, list):

                        for item in cls_validators:
                            if hasattr(item, "validators"):
                                print(f"   {item.validators:60.60}")
                            else:
                                print(f"   {item}")

                    elif hasattr(cls_validators, "validators"):
                        print(f"   {cls_validators.validators:60.60}")
                    else:
                        print(f"   {cls_validators:60.60}")

            print(f"\n{padder}\n")

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e:
            if 1 or cpdb():
                pdb.set_trace()
            raise


def build_validators_for_class(cls, li_revmro):
    """build filters for class, before instance overrides"""
    try:

        classname = cls.__name__

        final = []

        seen = set()

        for cls_ in li_revmro:

            validators = getattr(cls_, "cls_validators", None)

            if validators:

                # now, what do we accept?
                if not isinstance(validators, list):
                    validators = [validators]

                validators = validators.copy()

                for validator in validators:
                    if not isinstance(
                        validator, (ValidationManager, ValidationDirective)
                    ):
                        raise InvalidConfigurationException(
                            f"unexpected validation {validator} on class.{cls_.__name__}"
                        )

                    if not validator in seen:
                        final.append(validator)
                        seen.add(validator)

                # final.extend(validators)

        return final

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            pdb.set_trace()
        raise
