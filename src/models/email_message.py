from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime, timezone
from src.core.database import Base


class EmailMessage(Base):
    __tablename__ = 'email_messages'

    id = Column(Integer, primary_key=True, index=True)
    gmail_account = Column(String, index=True) # airtime or withdrawal
    message_id = Column(String, unique=True, index=True)
    subject = Column(String)
    sender = Column(String)
    body = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.now(timezone.utc))
    parsed_transaction_id = Column(String, index=True, nullable=True)
    matched = Column(Boolean, default=False)


