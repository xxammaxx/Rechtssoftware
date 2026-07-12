"""File storage port (interface) for document persistence."""

from abc import ABC, abstractmethod


class FileStorage(ABC):
    """Abstract file storage for document binary data.

    Stores files on the local filesystem. Each implementation decides
    the storage strategy (flat directory, sharded, etc.).
    """

    @abstractmethod
    def store(self, storage_path: str, content: bytes) -> None:
        """Persist file content at the given storage path."""
        ...

    @abstractmethod
    def retrieve(self, storage_path: str) -> bytes:
        """Retrieve file content by storage path.

        Raises FileNotFoundError if the file doesn't exist.
        """
        ...

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """Check if a file exists at the given storage path."""
        ...
