import json
import pdb


def cpdb(**kwds: "Any") -> bool:  # pragma: no cover
    if cpdb.enabled == "once":
        cpdb.enabled = False  # type : ignore
        return True
    return cpdb.enabled  # type : ignore


cpdb.enabled = False  # type : ignore


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


from lazy_regression_tests.core2 import LazyCheckerOptions2 as LazyCheckerOptions


class DefaultJsonLazyCheckerOptions(LazyCheckerOptions):
    def prep(self, tmp, data):
        try:
            if not isinstance(data, dict):
                data = json.loads(data)
            return data
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise

    def to_text(self, tmp, data):
        try:
            return json.dumps(data, sort_keys=True, indent=4)
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            raise
