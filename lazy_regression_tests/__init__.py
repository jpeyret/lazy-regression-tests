# -"""Top-level package for lazy regression tests."""

# -__author__ = """JL Peyret"""
# -__email__ = "jpeyret@gmail.com"
# -__version__ = "__version__ = '__version__ = '0.2.3''"


from .core import LazyMixin, ValidationManager

from .filters import FilterManager

from .validators import (
    NamedTesteeAttributeValidator,
    FullyQualifiedNamesValidator,
    MixinExpInGot,
    ValidationDirective,
    DictValidator,
    DirectValidator,
    AutoExp,
)
