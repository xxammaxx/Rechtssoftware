"""Test guard that denies common Python network entry points."""

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from unittest.mock import patch


class NetworkAccessDenied(RuntimeError):  # noqa: N818 - preserved source API
    """Raised when code attempts network access inside the deny context."""


def _deny_network_call(*args: object, **kwargs: object) -> None:
    del args, kwargs
    raise NetworkAccessDenied("Outbound network access is forbidden during local analysis")


@contextmanager
def deny_network() -> Iterator[None]:
    """Deny socket and standard-library HTTP access for the enclosed operation."""

    targets = (
        "socket.socket",
        "socket.create_connection",
        "socket.getaddrinfo",
        "urllib.request.urlopen",
        "http.client.HTTPConnection.connect",
        "http.client.HTTPSConnection.connect",
    )

    with ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, new=_deny_network_call))
        yield
