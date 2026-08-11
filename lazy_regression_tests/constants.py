"""constants for lazy tests"""

import sys

LOGGER_NAME = "lazy"

verbose = "-v" in sys.argv

undefined = NotImplemented

OPT_DIRECTIVE_SKIP = "skip"
OPT_DIRECTIVE_BASELINE = "baseline"
OPT_DIRECTIVE_NODIFF = "nodiff"
OPT_DIRECTIVE_NOASSERT = "noassert"

TIMEOUT_MAXTIME_TO_ALLOW = 5


HDR = f"\n{'🧨⚙️' * 20}\n"
FTR = f"\n{'🧨⚙️' * 20}\n"

ENVIRONMENT_VARNAME_ROOT = "lzrt_"

LAZY_HEADER_SEPARATOR = "<![CDATA[header"

LAZY_KEEP_TEST_PREFIX = "lazy_keep_test_"
