from pathlib import Path

import anyio

from app.services.file_storage import StoredFile


class InvalidStorageKeyError(ValueError):
    pass


class LocalFileStorageService:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _resolve(self, key: str) -> Path:
        candidate = (self._root / key).resolve()
        if candidate == self._root or self._root not in candidate.parents:
            raise InvalidStorageKeyError("Storage key must remain inside the configured root.")
        return candidate

    async def put(self, key: str, content: bytes, content_type: str) -> StoredFile:
        destination = self._resolve(key)
        await anyio.to_thread.run_sync(destination.parent.mkdir, 0o755, True, True)
        await anyio.to_thread.run_sync(destination.write_bytes, content)
        return StoredFile(key=key, size_bytes=len(content), content_type=content_type)

    async def read(self, key: str) -> bytes:
        return await anyio.to_thread.run_sync(self._resolve(key).read_bytes)

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            await anyio.to_thread.run_sync(path.unlink)
