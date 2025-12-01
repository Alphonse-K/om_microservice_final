from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class EmailMessageBase(BaseModel):
    gmail_account: str = Field(..., description="Gmail account used for creating email")
    message_id: str = Field(..., description="Unique Gmail message ID")
    subject: Optional[str] = Field(None, description="Email subject")
    sender: Optional[str] = Field(None, description="Email sender address")
    body: str = Field(..., description="Email Content body")
    parsed_transaction_id: Optional[str] = Field(None, description="Parsed transaction ID")
    matched: Optional[bool] = Field(False, description="Indicates if the email was matched to a transaction")


class EmailMessageCreate(EmailMessageBase):
    """Schema used for creating a new email message"""
    pass


class EmailMessageUpdate(BaseModel):
    """Schema for updating existing email data"""
    parsed_transaction_id: Optional[str] = None
    matched: Optional[bool] = None


class EmailMessageInDBBase(EmailMessageBase):
    id: int
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailMessageResponse(EmailMessageInDBBase):
    """Schema returned in API responses"""
    pass


class EmailMessageListResponse(BaseModel):
    emails: list[EmailMessageResponse]
    total: int