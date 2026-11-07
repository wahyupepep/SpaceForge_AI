import os
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import normalize_database_url
from app.integrations.database_file_storage import DatabaseFileStorageService
from app.integrations.local_file_storage import InvalidStorageKeyError


@pytest_asyncio.fixture
async def storage_context():  # type: ignore[no-untyped-def]
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL must point to a disposable, migrated PostgreSQL database.")
    engine = create_async_engine(normalize_database_url(url), poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    key = f"tests/{uuid4()}/evidence.txt"
    storage = DatabaseFileStorageService(sessions)
    try:
        yield storage, sessions, key
    finally:
        await storage.delete(key)
        await engine.dispose()


@pytest.mark.asyncio
async def test_file_survives_storage_instance_changes_and_can_be_overwritten(storage_context):  # type: ignore[no-untyped-def]
    storage, sessions, key = storage_context
    stored = await storage.put(key, b"original", "text/plain")
    assert stored.size_bytes == 8
    another_instance = DatabaseFileStorageService(sessions)
    assert await another_instance.read(key) == b"original"

    await another_instance.put(key, b"revised", "text/plain")
    assert await storage.read(key) == b"revised"
    await another_instance.delete(key)
    await another_instance.delete(key)
    with pytest.raises(FileNotFoundError):
        await storage.read(key)


@pytest.mark.asyncio
async def test_empty_files_are_distinct_from_missing_files(storage_context):  # type: ignore[no-untyped-def]
    storage, _sessions, key = storage_context
    await storage.put(key, b"", "text/plain")
    assert await storage.read(key) == b""


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["../secret", "/absolute", "", "."])
async def test_database_storage_rejects_invalid_keys(key: str) -> None:
    storage = DatabaseFileStorageService(None)  # type: ignore[arg-type]
    with pytest.raises(InvalidStorageKeyError):
        await storage.put(key, b"unsafe", "text/plain")
