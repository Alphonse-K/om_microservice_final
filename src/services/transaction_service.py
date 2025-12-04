from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from src.core.security import SecurityUtils
from typing import List, Optional


# MODELS
from src.models.transaction import (
    DepositTransaction,
    WithdrawalTransaction,
    AirtimePurchase,
    PendingTransaction,
    Country,
    CompanyCountryBalance,
    Company,
    FeeConfig,
    Procurement,
)

# SCHEMAS
from src.schemas.transaction import (
    DepositCreate,
    WithdrawalCreate,
    AirtimeCreate,
    CountryCreate,
    CountryUpdate,
    CompanyBalanceCreate,
    CompanyBalanceUpdate,
    CompanyCreate,
    CompanyUpdate,
    FeeConfigCreate,
    FeeConfigUpdate,
    ProcurementCreate,
    ProcurementUpdate,
)


# Minimum intervals
BLACKOUT_TIMES = {
    "deposit": timedelta(minutes=10),
    "withdrawal": timedelta(minutes=10),
    "airtime": timedelta(minutes=4),
}

def ussd_is_failure(text: str | None) -> bool:
    if not text:
        return True

    failure_patterns = [
        "echec",
        "erreur",
        "invalid",
        "montant minimum",
        "vous devez attendre",
        "insufficient",
        "temporarily unavailable",
        "balance insuffisante",
        "too many",
        "not allowed",
        "limit",
    ]

    text_l = text.lower()
    return any(p in text_l for p in failure_patterns)


def check_blackout(db: Session, model, msisdn: str, tx_type: str) -> bool:
    interval = BLACKOUT_TIMES.get(tx_type)
    if not interval:
        return False

    msisdn = msisdn.strip()

    last_tx = (
        db.query(model)
        .filter(model.status.in_(["created", "initiated", "pending", "processing"]))
        .filter((model.recipient == msisdn) if tx_type != "withdrawal" else (model.sender == msisdn))
        .order_by(model.created_at.desc())
        .first()
    )

    if last_tx:
        if last_tx.created_at.tzinfo is None:
            last_created = last_tx.created_at.replace(tzinfo=timezone.utc)
        else:
            last_created = last_tx.created_at

        now = datetime.now(timezone.utc)
        if (now - last_created) < interval:
            return True

    return False


# ====================================================
# DEPOSIT (QUEUE MODE)
# ====================================================
async def create_deposit(db: Session, deposit: DepositCreate):
    if check_blackout(db, DepositTransaction, deposit.recipient, "deposit"):
        raise Exception("Deposit blackout: please wait 10 minutes.")

    pending = PendingTransaction(
        transaction_type="deposit",
        msisdn=deposit.recipient,
        amount=deposit.amount,
        partner_id=deposit.partner_id,
        status="pending",
    )
    db.add(pending)
    db.commit()

    return {"message": "Deposit queued for execution.", "queue_id": pending.id}


# ====================================================
# WITHDRAWAL (QUEUE MODE)
# ====================================================
async def intitiate_withdrawal_transaction(db: Session, withdrawal: WithdrawalCreate):
    if check_blackout(db, WithdrawalTransaction, withdrawal.sender, "withdrawal"):
        raise Exception("Withdrawal blackout: please wait 10 minutes.")

    pending = PendingTransaction(
        transaction_type="withdrawal",
        msisdn=withdrawal.sender,
        amount=withdrawal.amount,
        partner_id=withdrawal.partner_id,
        status="pending",
    )
    db.add(pending)
    db.commit()

    return {"message": "Withdrawal queued for execution.", "queue_id": pending.id}


# ====================================================
# AIRTIME (QUEUE MODE)
# ====================================================
async def create_airtime_purchase(db: Session, airtime: AirtimeCreate):
    if check_blackout(db, AirtimePurchase, airtime.recipient, "airtime"):
        raise Exception("Airtime blackout: wait 4 minutes.")

    pending = PendingTransaction(
        transaction_type="airtime",
        msisdn=airtime.recipient,
        amount=airtime.amount,
        partner_id=airtime.partner_id,
        status="pending",
    )
    db.add(pending)
    db.commit()

    return {"message": "Airtime queued for execution.", "queue_id": pending.id}

# ++++++++++++++++++ GET REQUEST FOR DEPOSIT, AIRTIME, WITHDRAWAL +++++++++++++++++++++++++++++++++++++++++++

def get_deposit_transactions(
    db: Session,
    recipient: Optional[str] = None,
    partner_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[DepositTransaction]:
    query = db.query(DepositTransaction)
    if recipient:
        query = query.filter(DepositTransaction.recipient == recipient)
    if partner_id:
        query = query.filter(DepositTransaction.partner_id == partner_id)
    if status:
        query = query.filter(DepositTransaction.status == status)
    return query.order_by(DepositTransaction.id.desc()).limit(limit).offset(offset).all()

def get_withdrawal_transactions(
    db: Session,
    sender: Optional[str] = None,
    partner_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[WithdrawalTransaction]:
    query = db.query(WithdrawalTransaction)
    if sender:
        query = query.filter(WithdrawalTransaction.sender == sender)
    if partner_id:
        query = query.filter(WithdrawalTransaction.partner_id == partner_id)
    if status:
        query = query.filter(WithdrawalTransaction.status == status)
    return query.order_by(WithdrawalTransaction.id.desc()).limit(limit).offset(offset).all()

def get_airtime_purchase_transactions(
    db: Session,
    recipient: Optional[str] = None,
    partner_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[AirtimePurchase]:
    query = db.query(AirtimePurchase)
    if recipient:
        query = query.filter(AirtimePurchase.recipient == recipient)
    if partner_id:
        query = query.filter(AirtimePurchase.partner_id == partner_id)
    if status:
        query = query.filter(AirtimePurchase.status == status)
    return query.order_by(AirtimePurchase.id.desc()).limit(limit).offset(offset).all()


# ++++++++++++++++++ COUNTRY SERVICE LAYER +++++++++++++++++++++++++++++++++++++++++++

def create_country(db: Session, data: CountryCreate):
    country = Country(**data.model_dump())
    db.add(country)
    db.commit()
    db.refresh(country)
    return country

def list_countries(db: Session):
    return db.query(Country).all()

def get_country(db: Session, country_id: int):
    return db.query(Country).filter(Country.id == country_id).first()

def update_country(db: Session, country_id: int, data: CountryUpdate):
    country = get_country(db, country_id)
    if not country:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(country, key, value)
    db.commit()
    db.refresh(country)
    return country


# ++++++++++++++++++ COMPANY SERVICE LAYER +++++++++++++++++++++++++++++++++++++++++++

def create_company(db: Session, data: CompanyCreate):
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

def list_companies(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False
):
    query = db.query(Company)

    if active_only:
        query = query.filter(Company.is_active == True)

    return query.offset(skip).limit(limit).all()

def get_company(db: Session, company_id: int):
    return db.query(Company).filter(Company.id == company_id).first()

def update_company(db: Session, company_id: int, data: CompanyUpdate):
    company = get_company(db, company_id)
    if not company:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(company, key, value)

    db.commit()
    db.refresh(company)
    return company

# ++++++++++++++++++ FEE SERVICE LAYER +++++++++++++++++++++++++++++++++++++++++++

def create_fee_config(db: Session, data: FeeConfigCreate):
    config = FeeConfig(**data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

def list_fee_configs(db: Session):
    return db.query(FeeConfig).all()

def get_fee_config(db: Session, config_id: int):
    return db.query(FeeConfig).filter(FeeConfig.id == config_id).first()

def update_fee_config(db: Session, config_id: int, data: FeeConfigUpdate):
    config = get_fee_config(db, config_id)
    if not config:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config

