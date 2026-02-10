from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.models.transaction import Bank
from src.schemas.transaction import BankCreateUpdate

def create_bank(
    db: Session,
    name: str,
    account_number: str | None = None,
    created_by: str = "system",
):
    existing = db.query(Bank).filter(Bank.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bank name already exists",
        )

    bank = Bank(
        name=name,
        account_number=account_number,
        created_by=created_by,
    )

    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


def update_bank(
    db: Session,
    bank_id: int,
    data: BankCreateUpdate,
):
    bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if not bank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank not found",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(bank, field, value)

    db.commit()
    db.refresh(bank)
    return bank


def delete_bank(db: Session, bank_id: int) -> None:
    bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if not bank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank not found",
        )

    db.delete(bank)
    db.commit()