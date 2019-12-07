import json


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
