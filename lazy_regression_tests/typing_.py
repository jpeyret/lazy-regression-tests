from typing import Optional, TYPE_CHECKING, Any, Union, Dict, List, NewType

if TYPE_CHECKING:
    T_FilterParam = NewType(
        "T_FilterParam", Dict[str, Union["FilterManager", "FilterDirective"]]
    )
