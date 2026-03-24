from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from sqlalchemy import func

from . import Base

class Analysis(Base):
  __tablename__ = "analyses"

  id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
  repo_full_name: Mapped[str]
  pr_number: Mapped[int]
  gh_delivery_id: Mapped[str] = mapped_column(unique=True)
  feedback: Mapped[dict[str, any]] = mapped_column(JSONB) 
  created_at: Mapped[datetime] = mapped_column(server_default=func.now())
