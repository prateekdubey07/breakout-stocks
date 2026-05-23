# Compatibility shim -- re-exports pandas_ta_classic under the pandas_ta name.
# pandas-ta has no PyPI release compatible with Python 3.11; pandas-ta-classic
# (0.3.14b1) is the maintained fork and exposes the same public API.
from pandas_ta_classic import *  # noqa: F401, F403
from pandas_ta_classic import core  # noqa: F401

try:
    from pandas_ta_classic import __version__  # noqa: F401
except ImportError:
    __version__ = "0.3.14b1-shim"
