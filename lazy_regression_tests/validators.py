#######################################################
# Typing
#######################################################
from typing import (
    Optional,
    # TYPE_CHECKING,
    Any,
    cast,
)

from operator import attrgetter
import sys
import re
import os

from traceback import print_exc as xp  # pylint: disable=unused-import

try:
    from loguru import logger
except (ImportErrro,) as e:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)


#######################################################
# constants
#######################################################
undefined = NotImplemented

verbose = "-v" in sys.argv

# just to track regexes
tmp = re.compile("")
regex_class = tmp.__class__


def breakpoints(*args, **kwargs):
    return False


import pdb


def cpdb(*args, **kwargs):
    "disabled"


def rpdb() -> bool:  # pragma: no cover
    try:
        from django.core.cache import cache
    except (Exception,) as e:
        cache = {}
    import sys

    in_celery = sys.argv[0].endswith("celery") and "worker" in sys.argv
    if in_celery:
        return False
    return bool(cache.get("rpdb_enabled") or getattr("rpdb", "enabled", False))


rpdb.enabled = False  # type : ignore


from lazy_regression_tests.utils import (
    nested_dict_get,
    nested_dict_pop,
    first,
    fill_template,
    ppp,
    debug_write_validation_log,
)


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

    def get_source(self, testee):
        source = testee if self.sourcename is None else getattr(testee, self.sourcename)

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
        self, testee: "LazyMixin", exp: Any, t_message: str = None, source_: Any = None
    ):
        """

        """

        try:

            source_ = source_ or self.get_source(testee)
            got = self.get_value(source_)
            message = (
                fill_template(t_message, locals(), testee, self) if t_message else None
            )

            if isinstance(exp, regex_class):
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


class FullyQualifiedNamesValidator(Validator):
    def __init__(self):
        Validator.__init__(self, self.selector, self.sourcename)


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


class AttributeValidator(Validator):
    def __init__(self, selector, sourcename):
        super(AttributeValidator, self).__init__(selector, self.sourcename)
        self.f_getter = attrgetter(selector)

    def get_value(self, source):
        try:
            res = self.f_getter(source)
            if rpdb() and res is None:  # pragma: no cover
                pdb.set_trace()
            return res
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


class StatusCodeValidator(NamedTesteeAttributeValidator):
    selector = "status_code"

    def test(self, testee, exp, got, message):
        try:

            if exp is undefined:
                raise ValueError("exp is undefined")

            if message is None:
                message = fill_template(
                    "%(name)s exp:%(exp)s<>%(got)s:got", locals(), self, {"name": self}
                )

            if isinstance(exp, (int, str)):
                exp = [exp]

            exp = [int(exp) for exp in exp]
            got = int(got)

            testee.assertTrue(
                got in exp, "%s , not in expected status_code to %s" % (got, exp)
            )

            # testee.assertEqual(exp, got, message)
        except (AssertionError,) as e:  # pragma: no cover
            raise

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise


class CSSValidator(Validator):

    sourcename = "selectable"

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


class JsonValidator(AttrNamedDictValidator):
    sourcename = "json"


class HeadersValidator(AttrNamedDictValidator):
    sourcename = "headers"


class ContentTypeValidator(
    FullyQualifiedNamesValidator, MixinExpInGot, HeadersValidator
):
    selector = "content-type"


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

    def check_expectations(self, testee):
        try:

            self.prep_validation()

            if verbose:
                print("🔬🧟‍♂️🧟‍♂️🧟‍♂️049.lazy.026.lazy3")
                # if cpdb(): pdb.set_trace()

                if not hasattr(self, "fnp_val_log"):

                    dn_o = os.path.join(
                        os.environ["lzrt_template_dirname_got"], "v2.validations"
                    )

                    if not os.path.exists(dn_o):
                        os.makedirs(dn_o)

                    filename = testee.lazy_filename
                    di_sub = dict(
                        filename=filename.rstrip("v2"),
                        dn_o=dn_o,
                        classname=testee.__class__.__name__,
                    )

                    t_fnp = "%(lazy_filename)s.%(classname)s.%(_testMethodName)s.txt"
                    self.fnp_val_log = os.path.join(
                        dn_o, fill_template(t_fnp, di_sub, testee)
                    )

            # if verbose:
            #     ppp(self, "check_expectations")

            seen = set()
            for name, directive in self.validators.items():

                logname = name
                if name == "content_type":
                    logname = "%s=%s" % (name, directive.exp)

                if breakpoints(
                    "check_expectations", {"name": directive.name}
                ):  # pragma: no cover
                    pdb.set_trace()

                if not directive.active or directive.active is undefined:
                    logger.info("inactive %s" % (directive))
                    seen.add("%s.inactive" % (logname))
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

                seen.add(logname)
                directive.validator.check(testee, exp)

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


class ValidatorMixin:

    _validationmgr = undefined

    @property
    def validationmgr(self):
        if self._validationmgr is undefined:

            # first... is anything set on the instance?
            res = None

            self._validationmgr = res = ValidationManager(self)

            items_ = vars(self).items()

            found = False

            for attrname, value in items_:

                if value == res:
                    continue

                if attrname.startswith("validator"):
                    if not isinstance(value, list):
                        value = [value]

                    val1 = first(value)
                    if isinstance(val1, ValidationManager):
                        # ok, we can work with this

                        if verbose:
                            logger.info(
                                "validationmgr.setting from instance validator:%s"
                                % (attrname)
                            )
                        res = self._validationmgr = res or ValidationManager(self)
                        for valmgr in value:
                            found = True
                            res.add_directive(valmgr)

            if found:
                return res

            if breakpoints("validationmgr", {"any": True}):  # pragma: no cover
                pdb.set_trace()

            validatormgrs = getattr(self, "validatormgrs", []) or []

            for valmgr in validatormgrs:
                res.add_directive(valmgr)

            # and now add extra class-level validators if found...
            for attrname, value in vars(self.__class__).items():
                if attrname.startswith("validator") and isinstance(
                    value, ValidationManager
                ):
                    res.add_directive(value)

        return self._validationmgr

    def remove_expectation(self, name):
        self.validationmgr.remove_expectation(name)

    def set_expectation(self, *args, **kwargs):
        validationmgr = self.validationmgr

        name = args[0]
        if breakpoints("set_expectation", {"name": name}):  # pragma: no cover
            pdb.set_trace()

            # put this in your breakpoints.json

        validationmgr.set_expectation(*args, **kwargs)

    def check_expectations(self):
        try:

            validationmgr = self.validationmgr
            validationmgr.check_expectations(self)

        except (
            Exception,
        ) as e:  # pragma: no cover pylint: disable=unused-variable, broad-except
            if cpdb():
                pdb.set_trace()
            raise
