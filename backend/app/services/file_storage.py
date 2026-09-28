from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredFile:
    key: str
    size_bytes: int
    content_type: str


class FileStorageService(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> StoredFile: ...

    async def read(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...
