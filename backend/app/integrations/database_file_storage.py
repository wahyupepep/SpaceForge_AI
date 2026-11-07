from pathlib import PurePosixPath

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.integrations.local_file_storage import InvalidStorageKeyError
from app.models.stored_file import StoredFileRecord
from app.services.file_storage import StoredFile


class DatabaseFileStorageService:
    """Durable storage for the MVP's small files, shared across function instances."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _validate_key(key: str) -> None:
        path = PurePosixPath(key)
        if not key or len(key) > 500 or path.is_absolute() or ".." in path.parts or key == ".":
            raise InvalidStorageKeyError("Storage key must be a relative file path.")

    async def put(self, key: str, content: bytes, content_type: str) -> StoredFile:
        self._validate_key(key)
        statement = insert(StoredFileRecord).values(
            key=key, content=content, content_type=content_type
        )
        statement = statement.on_conflict_do_update(
            index_elements=[StoredFileRecord.key],
            set_={
                "content": statement.excluded.content,
                "content_type": statement.excluded.content_type,
                "updated_at": func.now(),
            },
        )
        async with self._session_factory.begin() as session:
            await session.execute(statement)
        return StoredFile(key=key, size_bytes=len(content), content_type=content_type)

    async def read(self, key: str) -> bytes:
        self._validate_key(key)
        async with self._session_factory() as session:
            content = await session.scalar(
                select(StoredFileRecord.content).where(StoredFileRecord.key == key)
            )
        if content is None:
            raise FileNotFoundError(key)
        return content

    async def delete(self, key: str) -> None:
        self._validate_key(key)
        async with self._session_factory.begin() as session:
            await session.execute(delete(StoredFileRecord).where(StoredFileRecord.key == key))
