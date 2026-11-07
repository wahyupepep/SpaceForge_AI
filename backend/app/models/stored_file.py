from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StoredFileRecord(TimestampMixin, Base):
    __tablename__ = "stored_files"

    key: Mapped[str] = mapped_column(String(500), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False)
