import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AuditAction(str, Enum):
    created = "created"
    updated = "updated"
    deleted = "deleted"


class RecordAuditLog(Base):
    __tablename__ = "record_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), ForeignKey("financial_records.id"), nullable=False)
    action = Column(SqlEnum(AuditAction), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    before_snapshot = Column(JSON, nullable=True)
    after_snapshot = Column(JSON, nullable=True)
    changed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
