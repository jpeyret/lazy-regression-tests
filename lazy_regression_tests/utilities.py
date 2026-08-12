import re
import sys
import types
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional, Tuple

import click
import pydantic
from rich.console import Console

from lazy_regression_tests.common import (
    FunctionCheck,
    Validator,
    ValidatorMgr,
    get_lazy_logger,
)
from lazy_regression_tests.constants import undefined
from lazy_regression_tests.core_assist2 import _LazyMeta
from lazy_regression_tests.utils import set_breakpoints3, set_cpdb, set_rpdb

verbose = "-v" in sys.argv
logger = get_lazy_logger()

console = Console()

PALETTE_MODULE = """#87E911
#8931EF
#F2CA19
#FF00BD
#0057E9
#E11845
#00876c
#67a872
""".splitlines()

PALETTE = """#add8e6
#aec67f
#f4e398
#efb169
#e67a52
#d43d51
#ffffff
#7777ff
#9dc6e0""".splitlines()


def debug_ancestors(header, ancestors):
    newline = "\n"
    logger.debug(header, ":")
    logger.debug(f"{newline.join([anc.__name__ for anc in ancestors])}")
    logger.debug("\n")


def filter_lz_cls(li: List[type], ext: str) -> List[type]:
    """filter any classes that contribute to the extension either as
    - _LazyMeta-based
    - or having cls_validators/cls_filters
    """
    res = []
    for cls in li:
        lz = getattr(cls, "_lz", None)

        if lz and ext in lz.extensions:
            res.append(cls)
        di = getattr(cls, "cls_validators", {}) or getattr(cls, "cls_filters", {})
        if ext in di:
            res.append(cls)
    return res


def filter_val(li_cls: List[type], ext: str, name: str) -> List[Tuple[type, Any]]:
    """filter all classes with given extension and the named validator"""
    res = []

    seen = set()

    for cls in li_cls:
        if cls in seen:
            continue
        else:
            seen.add(cls)

        defined_on_class = None
        if hasattr(cls, "_lz"):
            ori_validators = cls._LazyMeta__lz_ori["cls_validators"].get(ext)

            if ori_validators is None:
                defined_on_class = None
            elif isinstance(ori_validators, dict):
                defined_on_class = ori_validators.get(name)

            elif isinstance(ori_validators, list):
                for ori in ori_validators:
                    if isinstance(ori, dict):
                        if ori.get(name):
                            defined_on_class = True
                            break

            elif isinstance(ori_validators, ValidatorMgr):
                defined_on_class = [ov for ov in ori_validators.validators if ov.name == name]
                if defined_on_class:
                    defined_on_class = defined_on_class[-1]
            else:
                logger.debug(f"{ori_validators=}{type(ori_validators)=}")

            if defined_on_class:
                res.append((cls, defined_on_class))
                continue
        else:
            cls_validators = getattr(cls, "cls_validators", {})
            validators = cls_validators.get(ext)
            if not validators:
                continue

            if isinstance(validators, dict):
                if "name" in validators:
                    if validators["name"] == name:
                        res.append((cls, validators))
                        continue
                    else:
                        # not found
                        continue
            elif isinstance(validators, ValidatorMgr):
                v = [v for v in validators.validators if v.name == name]
                if v:
                    res.append((cls, v[-1]))
                    continue
                else:
                    continue

    return res

class Palette(dict):
    def __init__(self, colors=List[str], seed: Optional[Dict[Any, str]] = None) -> None:
        seed = seed or {}
        super().__init__(**seed)
        self.colors = colors

    def __missing__(self, key: Any):
        if isinstance(key, str) and key.startswith("style-"):
            raise KeyError(key)
        color = self.colors.pop(0)
        self[key] = color
        return color


class Cargo(pydantic.BaseModel):
    testee_cls: type

    palette: Palette
    print: Callable
    indent1: str = " " * 4
    indent2: str = " " * 8
    validator_attribute_names: list[str] = "active selector exp v".split()


class PrinterClassValidatorContributions:
    def __init__(self, cargo: Cargo, name: str):
        self.cargo = cargo
        self.name = name

    def _get_module_style(self, module: str):
        res = f"[{self.cargo.palette[module]}]"
        # pass
        return res

    def _print(self, val: Validator, ancestor: type, to_print=List[Tuple[str, Any]]):
        """print class info, as well as validator attribute values in to_print"""

        try:
            cargo = self.cargo

            NoneType = type(None)
            searchdoc = re.compile("").search.__doc__

            classname = self._getclass_print(ancestor)
            if not to_print:
                cargo.print(classname, ",,")
                return

            for tu in to_print:
                style_start = style_end = ""
                attr_name = tu[0]
                attr_value = tu[1]

                if isinstance(attr_value, tuple):
                    if type(attr_value[0]) is _LazyMeta:
                        attr_value = attr_value[1]

                if isinstance(attr_value, FunctionCheck):
                    attr_value = attr_value.f

                module = getattr(attr_value, "__module__", None)
                if module:
                    style_start = self._get_module_style(module)
                    style_end = "[/]"

                if type(attr_value) is types.FunctionType:
                    saval = attr_value.__name__

                elif isinstance(attr_value, str):
                    saval = f"{attr_value:60.60}"
                elif isinstance(attr_value, (bool, int, float, NoneType, list)):
                    saval = attr_value

                elif callable(attr_value) and attr_value.__doc__ == searchdoc:
                    saval = "regex.search"

                elif type(attr_value) is type:
                    saval = attr_value.__name__

                elif attr_name in ("exp",):
                    saval = attr_value

                else:
                    logger.debug(f"validator attribute:{attr_name}={attr_value}{type(attr_value)=}")
                    # we shouldn't be here, I think...

                    saval = attr_value

                cargo.print(classname, f"{attr_name:10.10}", f"{style_start}{saval}{style_end}")
                classname = cargo.indent2 + " " * 20
        # pragma: no cover
        except (Exception,) as e:  # noqa F841
            if cpdb():
                breakpoint()
            raise

    def _getclass_print(self, ancestor):
        cargo = self.cargo
        return f"{cargo.indent2}[{cargo.palette[ancestor.__module__]}]{ancestor.__name__:20.20}[/]"

    def _print_testcase(self, val: Validator, ancestor, di_print):
        """print information on the actual TestCase instance"""
        cargo = self.cargo
        cargo.print("-" * 80)
        cargo.print(f"\n[{cargo.palette['style-valname']}]{cargo.indent1}{self.name}[/]")

        to_print = []
        for aname in cargo.validator_attribute_names:
            attr_value = di_print.get(aname, undefined)
            if attr_value is undefined:
                continue
            to_print.append((aname, attr_value))

        self._print(val, ancestor, to_print=to_print)
        cargo.print(cargo.indent2, "." * 20, sep="")

    def _print_ancestor(self, val: Validator, ancestor, got_from: dict):
        try:
            to_print = []

            for attrname, tu in got_from.items():
                if tu[0] == ancestor:
                    attr_value = tu[1]
                    res = (attrname, attr_value)
                    to_print.append(res)

            if breakpoints("print_validator", {"validator_name": self.name}):  # pragma: no cover
                print(f"\n\nvalidator_name:{self.name} {ancestor=}") # debugging
                print("to_print:") # debugging
                for tu in to_print:
                    print("  ", tu) # debugging
                print("") # debugging
                breakpoint()
                pass

            self._print(val, ancestor, to_print=to_print)

        # pragma: no cover
        except (Exception,) as e:  # noqa F841
            if cpdb():
                breakpoint()
            raise

    def print(self, val: Validator, ancestor: type, di_print: dict): # debugging
        try:
            meth_print = self._print_ancestor
            is_testcase = ancestor == self.cargo.testee_cls
            if is_testcase:
                meth_print = self._print_testcase

            meth_print(val, ancestor, di_print)

        # pragma: no cover
        except (Exception,) as e:  # noqa F841
            if cpdb():
                breakpoint()
            raise


def print_validator(
    cls: type,
    name: str,
    val: Validator,
    ancestors: List[Tuple[type, Any]],
    cargo: Cargo,
):
    try:
        printer = PrinterClassValidatorContributions(cargo=cargo, name=name)

        attrnames = cargo.validator_attribute_names
        checker_vals = {wname: getattr(val, wname) for wname in attrnames}

        got_from: Dict[str, Tuple[type, Any]] = {}
        li_calc = reversed(ancestors)
        for anc, aval in li_calc:
            if verbose:
                logger.debug(f"{anc=} , {aval=}")

            for attrname in attrnames:
                if isinstance(aval, dict):
                    attrvalue = aval.get(attrname, undefined)
                else:
                    attrvalue = getattr(aval, attrname, undefined)

                if attrvalue == checker_vals[attrname]:
                    if attrname not in got_from:
                        got_from[attrname] = (anc, attrvalue)

        if breakpoints("print_validator", {"validator_name": name}):  # pragma: no cover
            print(f"\n\nvalidator_name:{name}") # debugging
            breakpoint()
            pass

        if verbose:
            for attrname, ori in got_from.items():
                logger.debug(f"{attrname:10.10} ancestor:{ori[0]} {ori[1]}")

        printer.print(val, cls, checker_vals)
        for ancestor in ancestors:
            printer.print(val, ancestor[0], got_from)

    # pragma: no cover
    except (Exception,) as e:  # noqa F841
        if cpdb():
            breakpoint()
        raise


def trace_ancestry(cls: type, ext: str, name: str = None, show=False, subj="v"):
    """show ancestry / origin of configuration"""
    try:
        colors = PALETTE_MODULE.copy()
        di_color = {cls.__module__: "#ffffff", "style-valname": "#ffffff"}

        palette = Palette(colors=colors, seed=di_color)

        print = console.print

        s = "\n\n"
        for v in palette:
            s += f"[{v}]{v}[/]\n"
        sys.stdout.write(s + "\n\n.")
        logger.debug(s)

        cargo = Cargo(palette=palette, print=print, testee_cls=cls)

        cur = getattr(cls.lz, ext)

        ext_ancestors = filter_lz_cls(cls.mro(), ext)

        logger.debug("validators:")
        for name, val in sorted(cur.validators.items()):
            filtered_ancestors_mro = filter_val(ext_ancestors, ext, name)

            print_validator(cls, name, val, filtered_ancestors_mro, cargo=cargo)

        logger.debug("\nlegend:")
        for k, color in cargo.palette.items():
            if isinstance(k, str) and k.startswith("style-"):
                continue
            logger.debug(f"  [{color}]{k}[/]")
        logger.debug("\n\n")

        mro_validators = [acls for acls in cls.mro() if hasattr(acls, "cls_validators")]

        logger.debug("\n\nancestors with validator definitions:")
        for acls in mro_validators:
            logger.debug(f"  {acls.__name__}")

        if rpdb():  # pragma: no cover
            breakpoint()
            pass

    # pragma: no cover
    except (Exception,) as e:  # noqa F841
        if cpdb():
            breakpoint()
        raise




def cpdb(*args, **kwargs):
    "disabled"

rpdb = breakpoints = cpdb

if __name__ == "__main__":
    cpdb = set_cpdb()
    rpdb = set_rpdb()
    breakpoints = set_breakpoints3() or breakpoints
    pass


@click.command()
@click.argument("testscript")
@click.option("--classname")
@click.option("--extension")
@click.option("--verbose/--quiet", "-v/-q", default=False)
def run(**kwargs):
    """click stub
    - do not modify overmuch or at all
    - past click validation the real work is done in Main
    """
    try:
        mgr = Main(**kwargs)
        res = mgr.process()
        return res

    # pragma: no cover
    except (Exception,) as e:  # noqa F841
        if cpdb():
            breakpoint()
        raise


class Main:
    """main manager docstring"""

    def __repr__(self):  #
        """repr"""
        return "%s" % (self.__class__.__name__)

    def __init__(self, **kwargs):  #
        """init - note that the incoming `kwargs` are determined by `run`s arguments
        Main's designed to be called programmatically, but `kwargs` then need to match the expectations
        of `run`s signature.
        """
        self.__dict__.update(**kwargs)

    def process(self):
        "process"
        try:
            module = import_module(self.testscript)

            clsoi = {}
            for name, cls in vars(module).items():
                logger.debug(f"{name} => {type(cls)=}")
                if type(cls) is _LazyMeta:
                    clsoi[cls.__name__] = cls

            if self.classname:
                clsoi2 = {name: cls for name, cls in clsoi.items() if name == self.classname}

            else:
                clsoi2 = clsoi

            for name, cls in sorted(clsoi2.items()):
                logger.debug(f"\n\nanalyze {name}:")

                extensions = cls._lz.extensions
                if self.extension:
                    extensions = [v for v in extensions if self.extension == v]

                for ext in extensions:
                    trace_ancestry(cls, ext=ext)

        # pragma: no cover
        except (Exception,) as e:  # noqa F841
            if cpdb():
                breakpoint()
            raise


if __name__ == "__main__":
    run()
