# -"""Top-level package for lazy regression tests."""

__author__ = """JL Peyret"""
__email__ = "jpeyret@gmail.com"
__version__ = "0.5.2"


from .core import LazyMixin, ValidationManager

from .filters import FilterManager, FilterDirective, RegexRemoveSaver

from .validators import (
    NamedTesteeAttributeValidator,
    FullyQualifiedNamesValidator,
    MixinExpInGot,
    ValidationDirective,
    DictValidator,
    DirectValidator,
    AutoExp,
)
