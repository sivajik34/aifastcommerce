from sqlalchemy import Column, Integer, String, DateTime,Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from db.session import Base

class ChatMessageHistory(Base):
    __tablename__ = "chat_message_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), index=True,nullable=False)
    message = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
