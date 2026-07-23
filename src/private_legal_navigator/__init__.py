"""PrivateLegalNavigator — Lokale Unterstützung bei rechtlichen Angelegenheiten."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version

try:
    __version__ = _package_version("private-legal-navigator")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
