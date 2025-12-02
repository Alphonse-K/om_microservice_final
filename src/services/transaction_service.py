from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from src.core.security import SecurityUtils


# MODELS
from src.models.transaction import (
    DepositTransaction,
    WithdrawalTransaction,
    AirtimePurchase,
    PendingTransaction,
    Country,
    CompanyCountryBalance,
    Company,
    User,
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
    UserCreate,
    UserUpdate,
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

def create_company(db: Session, data: CompanyCreate):
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

def list_companies(db: Session):
    return db.query(Company).all()

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

def create_balance(db: Session, data: CompanyBalanceCreate):
    balance = CompanyCountryBalance(**data.model_dump())
    db.add(balance)
    db.commit()
    db.refresh(balance)
    return balance

def list_balances(db: Session):
    return db.query(CompanyCountryBalance).all()

def get_balance(db: Session, balance_id: int):
    return db.query(CompanyCountryBalance).filter(CompanyCountryBalance.id == balance_id).first()

def update_balance(db: Session, balance_id: int, data: CompanyBalanceUpdate):
    balance = get_balance(db, balance_id)
    if not balance:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(balance, key, value)

    db.commit()
    db.refresh(balance)
    return balance

def create_user(db: Session, data: UserCreate):
    user = User(
        name=data.name,
        email=data.email,
        role=data.role,
        company_id=data.company_id,
        password_hash=SecurityUtils.hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def list_users(db: Session):
    return db.query(User).all()

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def update_user(db: Session, user_id: int, data: UserUpdate):
    user = get_user(db, user_id)
    if not user:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user

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

def create_procurement(db: Session, data: ProcurementCreate, file_path: str | None = None):
    procurement = Procurement(
        **data.model_dump(),
        slip_file_path=file_path
    )
    db.add(procurement)
    db.commit()
    db.refresh(procurement)
    return procurement

def list_procurements(db: Session):
    return db.query(Procurement).all()

def get_procurement(db: Session, procurement_id: int):
    return db.query(Procurement).filter(Procurement.id == procurement_id).first()

def update_procurement(db: Session, procurement_id: int, data: ProcurementUpdate):
    proc = get_procurement(db, procurement_id)
    if not proc:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(proc, key, value)

    db.commit()
    db.refresh(proc)
    return proc

