import enum
from typing import Any
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy import DateTime, Enum, func

from .base import Base


class AnalysisStatus(str, enum.Enum):
    completed = "completed"
    pending = "pending"
    processing = "processing"
    error = "error"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repo_full_name: Mapped[str]
    pr_number: Mapped[int]
    gh_delivery_id: Mapped[str] = mapped_column(unique=True)
    feedback: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.pending
    )
    error: Mapped[str | None] = mapped_column(nullable=True, default=None)
    attempts: Mapped[int] = mapped_column(server_default="0")
    comment_posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
