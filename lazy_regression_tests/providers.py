"""store Extention Providers """
from typing import Any, Union
from io import StringIO
import pprint
import json
import re
from _pickle import PicklingError

#################################################################
# Dependencies
#################################################################
from yaml import dump as ydump
import requests


from lazy_regression_tests.common import (
    ConfigurationException,
    LazyTemp,
    PAbstractExtProvider,
    di_ext_provider,
    DEFAULT_PROVIDER,
    DictFilter,
    DictFilterWrapper,
    BFilter,
    Checker,
    ValidationError,
    undefined,
)

from lazy_regression_tests._baseutils import dropbad_dump


def cpdb(*args, **kwargs):
    "disabled conditional breakpoints - does nothing until activated by set_cpdb/rpdb/breakpoint3"


rpdb = breakpoints = cpdb



class DictExtProvider(PAbstractExtProvider):
    """support dict data and dumps via pretty-print"""

    extension = "dict"

    TYPE_RAW = (dict, list)

    def prep_rawdata(self, checker: Checker, data: Any) -> Any:
        """convert data if needed"""
        try:

            for name in ["dict", "to_dict", "as_dict", "json"]:
                f = getattr(data, name, None)
                if callable(f):
                    res = f()
                    if isinstance(res, str) and name == "json":
                        res = json.loads(res)
                    if not isinstance(res, dict):
                        raise ConfigurationException(
                            # 🎫004.lazy.054.underscore_lz
                            f" data type {type(res)}, returned by data.{name}() not supported by {self}.  known extensions for testcase: {','.join(checker._lz.extensions)}"
                        )

                    return res
            raise ConfigurationException(
                # 🎫004.lazy.054.underscore_lz
                f" data type {type(data)} not supported by {self}.  known extensions for testcase: {','.join(checker._lz.extensions)}"
            )

        except (json.decoder.JSONDecodeError):
            raise
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @classmethod
    def datain_to_str(
        cls, data: dict, checker: Checker, temp: LazyTemp = None
    ) -> str:
        """pretty print dict to string"""
        try:

            tu_supp = (dict,)

            if not isinstance(data, tu_supp):
                f = getattr(data, "dict", None)
                if callable(f):
                    data = f()
                else:
                    raise ConfigurationException(
                        # 🎫004.lazy.054.underscore_lz
                        f" data type {type(data)} not supported by {cls.__name__} which supports {tu_supp}.  known extensions for testcase: {','.join(checker._lz.extensions)}"
                    )

            out = StringIO()
            pprint.pprint(data, out, width=1)
            return out.getvalue().strip()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def build_filter(self, v_in: Any) -> Union[DictFilter, BFilter]:
        "build filter"
        try:

            if isinstance(v_in, BFilter):
                return v_in

            elif isinstance(v_in, dict):

                f = v_in.get("f")
                if f is None:
                    f = DictFilterWrapper({v_in["name"]: None})
                    v_in["f"] = f
                filter2 = DictFilter(**v_in)
            elif isinstance(v_in, str):
                filter2 = DictFilter(f=v_in)
            else:
                raise NotImplementedError(f"unsupported {v_in}")

            return filter2

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


class JsonExtProvider(DictExtProvider):
    """support dict data and dumps via json.dumps"""

    extension = "json"

    @classmethod
    def check_is_json(cls, data, checker, temp):
        "check that a 404 didn't return html somehow"
        try:
            content_type = getattr(data, "content_type", None)
            status_code = getattr(data, "status_code", None)
            url_msg = ""
            for attrname in ["full_url", "url"]:
                url = getattr(data, attrname, undefined)
                if url is not undefined:
                    url_msg = f" {url=}"
                    break

            if content_type is not None:
                if "json" not in content_type:
                    raise ValidationError(
                        f"did not get a json response {content_type=} with {status_code=}{url_msg}"
                    )

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    def prep_rawdata(self, checker: Checker, data: Any) -> Any:
        """convert data if needed"""
        try:

            if isinstance(data, list):
                return json.loads(json.dumps(data))
            if data is None:
                return {}
            if isinstance(data, str):
                return json.loads(data)

            for name in ["json"]:
                f = getattr(data, name, None)
                if callable(f):
                    v = f()
                    if isinstance(v, str):
                        v = json.loads(v)
                    return v

            raise ConfigurationException(
                # 🎫004.lazy.054.underscore_lz
                f" data type {type(data)} not supported by {self}.  known extensions for testcase: {','.join(checker._lz.extensions)}"
            )

            # raise NotImplementedError()
        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise

    @classmethod
    def datain_to_str(
        cls, data: dict, checker: Checker, temp: LazyTemp = None
    ) -> str:
        """pretty print dict to string"""
        try:

            tu_supp = (dict, list)

            if isinstance(data, str):
                data = json.loads(data)

            if isinstance(data, tu_supp):
                return json.dumps(data, indent=2, sort_keys=True).strip()
            elif data is None:
                return "{}"
            elif isinstance(data, requests.models.Response):
                return json.dumps(data.json(), indent=2, sort_keys=True).strip()

            elif hasattr(data, "getvalue") and callable(data.getvalue):
                res = data.getvalue()
                if isinstance(res, (str, bytes)):
                    try:
                        res = json.loads(res)
                    except (json.decoder.JSONDecodeError,) as e: # noqa F841
                        cls.check_is_json(data, checker, temp)

                elif isinstance(res, dict):
                    pass
                else:
                    raise NotImplementedError()
                res = json.dumps(res, indent=2, sort_keys=True)
                return res.strip()

            else:
                f = getattr(data, "json", None)
                if callable(f):
                    res = f()
                    if isinstance(res, dict):
                        res = json.dumps(res, indent=2, sort_keys=True)
                    return res.strip()

                raise ConfigurationException(
                    # 🎫004.lazy.054.underscore_lz
                    f" data type {type(data)} not supported by {cls.__name__} which supports {tu_supp}.  known extensions for testcase: {','.join(checker._lz.extensions)}"
                )

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise




def yaml_strip(data: str | Any) -> str | Any:

    if isinstance(data, str):

        patre = re.compile(" \*id\d+$")

        if "&id" in data or "*id" in data:

            lines = data.splitlines()
            lines2 = []
            for line in lines:
                if "&id" in line:
                    repad = (len(line) - len(line.lstrip())) * " "
                    words = line.split()
                    words.pop(1)
                    line2 = repad + " ".join(words)
                    lines2.append(line2)
                elif hit := patre.search(line):
                    line2 = line[: hit.regs[0][0] + 4]
                    lines2.append(line2)
                else:
                    lines2.append(line)

            data = "\n".join(lines2)

        return data.strip()
    return data


class YamlProvider(DictExtProvider):
    """support dict data and dumps via json.dumps"""

    extension = "yaml"

    def strip(self, data: str | Any) -> str | Any:
        return yaml_strip(data)

    def prep_rawdata(self, checker: Checker, data: Any) -> Any:
        """no conversion needed, that's the point of using yaml"""
        return data

    @classmethod
    def datain_to_str(
        cls, data: dict, checker: Checker, temp: LazyTemp = None
    ) -> str:
        """yaml dump"""
        try:
            try:

                # from yaml import dump as ydump
                import yaml

                # breakpoint()

                # https://stackoverflow.com/a/66853182

                class NoAliasDumper(yaml.SafeDumper):
                    def ignore_aliases(self, data):
                        return True

                res = yaml.dump(data, default_flow_style=False)

                res = yaml_strip(res)

                return res

            # pragma: no cover pylint: disable=unused-variable
            except (TypeError, ValueError, PicklingError) as e: # noqa F841
                data2 = dropbad_dump(data, ydump)
                res2 = ydump(data2, default_flow_style=False).strip()
                res2 = yaml_strip(res2)

                return res2
        # pragma: no cover pylint: disable=unused-variable
        except (TypeError,) as e: # noqa F841
            raise

        # pragma: no cover pylint: disable=unused-variable
        except (PicklingError,) as e: # noqa F841
            if 1:
                for k, v in vars(data).items():
                    print(k, end="")
                    try:
                        _ = yaml.dump(v)
                        print("✅")
                    # pragma: no cover pylint: disable=unused-variable
                    except (Exception,) as e2: # noqa F841
                        print("🧨")

            # if cpdb():
            #     breakpoint()
            raise TypeError(e)

        # pragma: no cover pylint: disable=unused-variable
        except (Exception,) as e: # noqa F841
            if cpdb():
                breakpoint()
            raise


di_ext_provider.update(
    txt=DEFAULT_PROVIDER,
    json=JsonExtProvider(),
    dict=DictExtProvider(),
    yaml=YamlProvider(),
)
