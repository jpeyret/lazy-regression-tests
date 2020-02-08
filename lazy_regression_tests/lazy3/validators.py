import pdb
import sys
import re

from operator import attrgetter

from traceback import print_exc as xp

#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
)


from lazy_regression_tests.utils import (
    nested_dict_get,
    nested_dict_pop,
    first,
    fill_template,
    ppp,
)


verbose = "-v" in sys.argv

undefined = NotImplemented

# https://stackoverflow.com/questions/6102019/type-of-compiled-regex-object-in-python
# yeah, it is what it is, so be it...
type_regex_hack = re.compile("").__class__


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


#######################################################
# Validators
#######################################################


class Validator:
    pass

    attrname: str
    sourcename: str

    def __repr__(self):
        return "%s[selector=%s]" % (
            self.__class__.__name__,
            getattr(self, "selector", "?"),
        )

    def __init__(self, selector, sourcename: Optional[str], scalar=True):
        try:
            self.selector = selector
            self.sourcename = sourcename
            self.scalar = scalar

            assert isinstance(sourcename, str) or sourcename is None
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def get_source(self, testee, **sources):

        # pdb.set_trace()

        if self.sourcename is None:

            source = (
                testee
            )  # if self.sourcename is None else getattr(testee, self.sourcename)

        else:

            sourcenames = self.sourcename.split(".", 1)
            sourcename = sourcenames[0]

            source0 = sources.get(sourcename) or getattr(testee, sourcename)
            if len(sourcenames) > 1:
                path = sourcenames[1]
                if isinstance(source0, dict):
                    # allow for nesteds?
                    source = source0[path]

                else:
                    # use nested operators
                    f_getter = attrgetter(path)
                    source = f_getter(source0)

            else:
                source = source0

        if source is None:
            raise ValueError(
                "you need to either pass in a dict in `source` or %s needs to have `%s` set"
                % (testee, self.sourcename)
            )
        return source

    def get_value(self, source):
        res = source.get(self.selector)
        if rpdb() and res is None:  # pragma: no cover
            pdb.set_trace()
        return res

    def check(
        self,
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
            got = self.get_value(source_)
            message = (
                fill_template(t_message, locals(), testee, self) if t_message else None
            )

            if isinstance(exp, type_regex_hack):
                self.test_regex(testee, exp, got, message)
                if verbose:
                    logger.info("%s checked %s" % (testee, self))

            elif not callable(exp):
                if "-v" in sys.argv:
                    print("\n\nvalidator.%s.checking(exp=%s,got=%s)" % (self, exp, got))
                self.test(testee, exp, got, message)
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

    def test_regex(self, testee, exp, got, message):
        try:

            if message is None:
                message = fill_template(
                    "%(name)s pattern:%(pattern)s:does not match:%(got)s:got",
                    locals(),
                    exp,
                    self,
                    {"name": self},
                )

            testee.assertTrue(exp.search(str(got)), message)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def test(self, testee, exp, got, message):
        try:

            if exp is undefined:
                raise ValueError("exp is undefined")

            if message is None:
                message = fill_template(
                    "%(name)s exp:%(exp)s<>%(got)s:got", locals(), self, {"name": self}
                )

            # correcting for unspecified scalars
            if not isinstance(exp, list) and isinstance(got, list) and len(got) == 1:
                got = first(got)

            testee.assertEqual(exp, got, message)
        except (AssertionError,) as e:  # pragma: no cover
            raise

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
    def get_value(self, source):
        """ get the value from  """
        try:
            res = nested_dict_get(source, self.selector)
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


class HeadersValidator(AttrNamedDictValidator):
    sourcename = "response.headers"


class MixinExpInGot:
    def test(self, testee, exp, got, message):

        if exp is undefined:
            raise ValueError("exp is undefined")
        try:
            testee.assertTrue(str(exp) in str(got), message)
            if verbose:
                logger.info("%s checked %s" % (testee, self))
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


class CSSValidator(Validator):

    sourcename = "response.selectable"

    to_text = False

    def __init__(self, selector, scalar=None, to_text=True):

        if scalar is None:
            scalar = selector.startswith("#")

        super(CSSValidator, self).__init__(
            selector, scalar=scalar, sourcename=self.sourcename
        )
        self.to_text = to_text

    def get_value(self, source):

        found = source.select(self.selector)
        if self.scalar:
            found = first(found)
            if found and self.to_text:
                return found.text.strip()
            return found
        else:
            if not self.to_text:
                return found
            else:
                return [elem.text.strip() for elem in found]


class TitleCSSValidator(FullyQualifiedNamesValidator, CSSValidator):
    selector = "title"
    scalar = True
    to_text = True


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

    def __init__(self, name, validator, exp, active):
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

    def prep_validation(self):
        try:
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

    def check_expectations(self, testee, **sources):
        try:

            self.prep_validation()

            if verbose:
                ppp(self, "check_expectations")

            for name, directive in self.validators.items():

                if breakpoints(
                    "check_expectations", {"name": directive.name}
                ):  # pragma: no cover
                    pdb.set_trace()

                if not directive.active or directive.active is undefined:
                    logger.info("inactive %s" % (directive))
                    continue

                exp = directive.exp

                # maybe it's built into the validator?
                if exp is undefined:
                    exp = getattr(directive.validator, "exp", undefined)

                if exp is undefined:
                    # let's see if we can get it
                    exp = getattr(testee, directive.name, undefined)

                if exp is undefined:
                    raise ValueError("%s has undefined exp" % (directive))

                directive.validator.check(testee, exp, sources)

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
                    logger.info("                  directive:%s" % (override))

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
        try:
            self.set_expectation(name, active=False)
        except (KeyError,) as e:  # pragma: no cover
            logger.warning(e)
            pass
        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise

    def set_expectation(self, name, exp=undefined, validator=None, active=None):

        try:

            if validator is None:
                existing = self.validators.get(name)

                if active is None:
                    active = exp is not undefined

                if existing is None:
                    possibles = ",".join(list(self.validators.keys()))

                    msg = f"unknown check `{name}`.  known checks are `{possibles}` on `{self}.validators`"
                    raise KeyError(msg)
                else:
                    self._add_override(
                        ValidationDirective(name, validator, exp, active)
                    )

            else:

                # pdb.set_trace()

                if active is None:
                    active = not (exp is undefined)

                self._add_override(ValidationDirective(name, validator, exp, active))

                # raise NotImplementedError("%s.set_expectation.withValidator(%s)" % (self, locals()))

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
