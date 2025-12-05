# src/autoheader/__init__.py

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("autoheader")
except PackageNotFoundError:
    __version__ = "0.0.0"

from .api import AutoHeader, HeaderResult

__all__ = ["AutoHeader", "HeaderResult"]
