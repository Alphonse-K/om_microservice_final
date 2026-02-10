from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.models.transaction import User, Bank
from src.schemas.transaction import BankCreateUpdate, BankResponse
from src.services.bank_service import (
    create_bank,
    update_bank,
    delete_bank,
)
from src.core.auth_dependencies import require_role

bank_router = APIRouter(prefix="/api/v1/banks", tags=["Banks"])


@bank_router.post(
    "",
    response_model=BankResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bank_route(
    payload: BankCreateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "MAKER"]))
):
    return create_bank(
        db=db,
        name=payload.name,
        account_number=payload.account_number,
        created_by=current_user.name
    )

@bank_router.get(
    "",
    response_model=list[BankResponse],
)
def list_banks(
    db: Session = Depends(get_db),
):
    return db.query(Bank).order_by(Bank.name).all()

@bank_router.put(
    "/{bank_id}",
    response_model=BankResponse,
)
def update_bank_route(
    bank_id: int,
    payload: BankCreateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "MAKER", "CHECKER"]))
):
    return update_bank(
        db=db,
        bank_id=bank_id,
        data=payload,
    )

@bank_router.delete(
    "/{bank_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_bank_route(
    bank_id: int,
    current_user: User = Depends(require_role(["ADMIN", "MAKER", "CHECKER"])),
    db: Session = Depends(get_db),
):
    delete_bank(db, bank_id)
