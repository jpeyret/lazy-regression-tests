""" provide validation building blocks """

from typing import List, Any, Optional, Dict
from collections import defaultdict
import unittest

#################################################################
# Dependencies
#################################################################
from more_itertools import partition

from lazy_regression_tests.utils import ppp

from lazy_regression_tests.basics import (
    ExtAlias,
    get_alias_from_ancestors,
    ValidationError,
    ConfigurationException,
    DisableAll,
)


undefined = NotImplemented
verbose = False

from lazy_regression_tests.providers import di_ext_provider, DEFAULT_PROVIDER
from lazy_regression_tests.common import (
    Validator,
    ValidatorMgr,
    flatten_to_validators_dicts,
    AutoExp,
    check_equal,
    check_exp_in_data,
    check_in,
    check_not_in,
    Selectors,
)


# disable stuff that makes this module's audit noisy
# pylint: disable=no-self-argument,super-init-not-called,no-member,bad-mcs-method-argument
# pylint: disable=bad-mcs-classmethod-argument,no-name-in-module,line-too-long
from pydantic import BaseModel, Field, validator as pyd_validator


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb


def build_validators_for_class(
    cls, ancestors_in, di_alias: Dict[str, str]
) -> Dict[str, ValidatorMgr]:
    """ build ValidatorMgrs for a class by adding them up by extension from all its supers and itself
        and assigning them
    """

    try:

        res: Dict[str, ValidatorMgr] = {}

        di_tmp: Dict[str, List[Validator]] = defaultdict(list)
        ancestors = [
            ancestor for ancestor in ancestors_in if hasattr(ancestor, "cls_validators")
        ]

        di_vcls = {}

        for ix, acls in enumerate(ancestors):

            if verbose:
                print(f"{ix:02} ancestor={acls.__name__}")
            for ext, values in acls.cls_validators.items():

                mgr_cls = alias = None

                if isinstance(values, (list, tuple)):
                    values, aliases = [
                        list(v) for v in partition(ExtAlias.is_instance, values)
                    ]
                    alias = aliases[-1].alias if aliases else None

                # preserve specialized ValidatorMgr subclasses
                if isinstance(values, ValidatorMgr):
                    di_vcls[ext] = values.__class__
                    alias = values.alias

                if alias:
                    known_alias = di_alias.get(ext)
                    if known_alias:
                        if not known_alias == alias:
                            raise ConfigurationException(
                                f"build_validators_for_class({cls=}).{known_alias=} <> {alias=}"
                            )
                    else:
                        di_alias[ext] = alias

                li = di_tmp[ext]

                # inactivate all validators so far
                if values is DisableAll:
                    da_uniqs = set()
                    for da_v in li:
                        if isinstance(da_v, dict):
                            da_name = da_v.get("name")
                        else:
                            da_name = getattr(da_v, "name", None)
                        if da_name:
                            da_uniqs.add(da_name)

                    for da_name in sorted(da_uniqs):
                        li.append(dict(name=da_name, active=False))
                    continue

                li_values = []
                flatten_to_validators_dicts(li_values, values)

                if verbose:
                    print(f"   {ext:6.6} {values=}")

                for v in li_values:
                    # keep track of specialized ValidatorMgr subclasses
                    li.append(v)

        for ext, validators in di_tmp.items():
            alias = None
            if verbose:
                print(f"{ext=} : {validators}")

            di: Dict[str, Validator] = {}

            for v_in in validators:

                if isinstance(v_in, Validator):
                    v = v_in
                elif v_in is DisableAll:
                    v = v_in
                elif isinstance(v_in, dict):
                    name = v_in["name"]
                    prev = di.get(name)

                    if prev:

                        di_override = prev.dict()
                        di_override.update(**v_in)

                        new_v = Validator(**di_override)
                        di[new_v.name] = new_v
                        continue
                    else:
                        v = Validator(**v_in)

                else:
                    raise NotImplementedError(f"unsupported {v_in}")

                # here's the tricky part.  we assign the validator to its hash in a dictionary
                # so later validators in the list - like inactive ones - replace the earlier ones)

                if verbose:
                    print(v)
                if v is DisableAll:
                    di.clear()
                else:
                    di.__setitem__(v.name, v)

            # and now we reassign the list, which is now unique by filter, in their original position
            # of declaration
            vcls = di_vcls.get(ext) or ValidatorMgr
            assert issubclass(vcls, ValidatorMgr)

            alias = di_alias.get(ext)
            if not alias:
                alias = get_alias_from_ancestors(cls, ancestors_in, ext)
                if alias:
                    pass
                    di_alias[ext] = alias
            validators = list(di.values())

            di_init = dict(ext=ext, alias=alias, validators=validators)

            vmgr = res[ext] = vcls(**di_init)
            assert vmgr.provider

        return res

    # pragma: no cover pylint: disable=unused-variable
    except (Exception,) as e:
        if cpdb():
            breakpoint()
        raise
