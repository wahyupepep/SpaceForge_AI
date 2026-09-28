from pathlib import Path

import pytest

from app.integrations.local_file_storage import (
    InvalidStorageKeyError,
    LocalFileStorageService,
)


@pytest.mark.asyncio
async def test_local_storage_round_trip(tmp_path: Path) -> None:
    storage = LocalFileStorageService(tmp_path)

    stored = await storage.put("prototype/index.html", b"<h1>Spec</h1>", "text/html")

    assert stored.key == "prototype/index.html"
    assert stored.size_bytes == 13
    assert await storage.read(stored.key) == b"<h1>Spec</h1>"


@pytest.mark.asyncio
async def test_local_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalFileStorageService(tmp_path)

    with pytest.raises(InvalidStorageKeyError):
        await storage.put("../secret", b"unsafe", "text/plain")
