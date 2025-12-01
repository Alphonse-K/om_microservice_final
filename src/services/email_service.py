from sqlalchemy.orm import Session
from src.models.email_message import EmailMessage
from src.schemas.email_message import EmailMessageCreate

def create_email(db: Session, paylaod: dict) -> EmailMessageCreate:
    # payload is a dict with fields matching EmailMessage
    email = EmailMessage(**paylaod)
    db.add(email)
    db.commit()
    db.refresh(email)
    return email

def get_email_by_message_id(db: Session, message_id: str):
    return db.query(EmailMessage).filter(EmailMessage.message_id==message_id).first()

def mark_email_matched(db: Session, email_obj: EmailMessage):
    email_obj.matched = True
    db.add(email_obj)
    db.commit()
    db.refresh(email_obj)
    return email_obj

def list_emails(db: Session, skip: int = 0, limit: int = 100):
    q = db.query(EmailMessage).order_by(EmailMessage.received_at.desc()).offset(skip).limit(limit).all()
    total = db.query(EmailMessage).count()
    return q, total

