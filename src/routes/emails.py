from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.services.email_service import list_emails
from src.schemas.email_message import EmailMessageListResponse, EmailMessageResponse

email_router = APIRouter(prefix="/emails", tags=['Emails'])

@email_router.get("/", response_model=EmailMessageListResponse)
def read_emails(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items, total = list_emails(db, skip=skip, limit=limit)
    return {'emails': items, 'total': total}