""" this file provides common functionality and constants to the others 
    
    DO NOT import anything lazy in it other than utils/baseutils otherwise
    there is a strong chance for circular import issues.

"""

OPT_DIRECTIVE_SKIP = "skip"
OPT_DIRECTIVE_BASELINE = "baseline"
OPT_DIRECTIVE_NODIFF = "nodiff"

from lazy_regression_tests.utils import InvalidConfigurationException
