from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import or_, func
from typing import Optional, List


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

def create_a_company(db: Session, data: CompanyCreate):
    """Create a new company"""
    # Check if email already exists
    existing = db.query(Company).filter(Company.email == data.email).first()
    if existing:
        raise ValueError(f"Company with email {data.email} already exists")
    
    # Check if name already exists
    existing_name = db.query(Company).filter(Company.name == data.name).first()
    if existing_name:
        raise ValueError(f"Company with name {data.name} already exists")
    
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
    """List companies with pagination"""
    query = db.query(Company)

    if active_only:
        query = query.filter(Company.is_active == True)

    return query.order_by(Company.created_at.desc()).offset(skip).limit(limit).all()

def get_company_by_id(db: Session, company_id: int):
    """Get company by ID"""
    return db.query(Company).filter(Company.id == company_id).first()

def update_a_company(db: Session, company_id: int, data: CompanyUpdate):
    """Update a company"""
    company = get_company_by_id(db, company_id)
    if not company:
        return None

    # Check if new email already exists (if email is being updated)
    if data.email and data.email != company.email:
        existing = db.query(Company).filter(Company.email == data.email).first()
        if existing:
            raise ValueError(f"Company with email {data.email} already exists")
    
    # Check if new name already exists (if name is being updated)
    if data.name and data.name != company.name:
        existing = db.query(Company).filter(Company.name == data.name).first()
        if existing:
            raise ValueError(f"Company with name {data.name} already exists")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(company, key, value)

    db.commit()
    db.refresh(company)
    return company

def delete_a_company(db: Session, company_id: int):
    """Soft delete (deactivate) a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return False
    
    company.is_active = False
    db.commit()
    return True

def activate_a_company(db: Session, company_id: int):
    """Activate a deactivated company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return False
    
    company.is_active = True
    db.commit()
    return True

def get_companies_count(db: Session, active_only: bool = False):
    """Get total number of companies"""
    query = db.query(func.count(Company.id))
    
    if active_only:
        query = query.filter(Company.is_active == True)
    
    return query.scalar()

def get_company_stats(db: Session, company_id: int):
    """Get statistics for a company"""
    from src.models.transaction import User, Procurement, DepositTransaction, WithdrawalTransaction, AirtimePurchase
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return None
    
    # Get user count
    user_count = db.query(func.count(User.id)).filter(
        User.company_id == company_id,
        User.is_active == True
    ).scalar()
    
    # Get active user count
    active_user_count = db.query(func.count(User.id)).filter(
        User.company_id == company_id,
        User.is_active == True
    ).scalar()
    
    # Get procurement stats
    procurement_stats = db.query(
        func.count(Procurement.id).label('total'),
        func.sum(Procurement.amount).label('total_amount')
    ).filter(Procurement.company_id == company_id).first()
    
    # Get transaction counts
    deposit_count = db.query(func.count(DepositTransaction.id)).filter(
        DepositTransaction.company_id == company_id
    ).scalar()
    
    withdrawal_count = db.query(func.count(WithdrawalTransaction.id)).filter(
        WithdrawalTransaction.company_id == company_id
    ).scalar()
    
    airtime_count = db.query(func.count(AirtimePurchase.id)).filter(
        AirtimePurchase.company_id == company_id
    ).scalar()
    
    # Get total balance from all countries
    balance_stats = db.query(
        func.sum(CompanyCountryBalance.available_balance).label('total_available'),
        func.sum(CompanyCountryBalance.held_balance).label('total_held')
    ).filter(CompanyCountryBalance.company_id == company_id).first()
    
    # Get recent transactions (last 10)
    recent_deposits = db.query(DepositTransaction).filter(
        DepositTransaction.company_id == company_id
    ).order_by(DepositTransaction.created_at.desc()).limit(5).all()
    
    recent_withdrawals = db.query(WithdrawalTransaction).filter(
        WithdrawalTransaction.company_id == company_id
    ).order_by(WithdrawalTransaction.created_at.desc()).limit(5).all()
    
    recent_transactions = []
    
    # Format recent transactions
    for tx in recent_deposits:
        recent_transactions.append({
            "id": tx.id,
            "type": "deposit",
            "amount": float(tx.amount),
            "msisdn": tx.recipient,
            "status": tx.status,
            "created_at": tx.created_at
        })
    
    for tx in recent_withdrawals:
        recent_transactions.append({
            "id": tx.id,
            "type": "withdrawal",
            "amount": float(tx.amount),
            "msisdn": tx.sender,
            "status": tx.status,
            "created_at": tx.created_at
        })
    
    # Sort by created_at descending
    recent_transactions.sort(key=lambda x: x["created_at"], reverse=True)
    recent_transactions = recent_transactions[:10]  # Keep only top 10
    
    return {
        "company_id": company_id,
        "company_name": company.name,
        "total_users": user_count,
        "active_users": active_user_count,
        "total_balance": float(balance_stats.total_available or 0) + float(balance_stats.total_held or 0),
        "total_transactions": deposit_count + withdrawal_count + airtime_count,
        "transaction_breakdown": {
            "deposits": deposit_count,
            "withdrawals": withdrawal_count,
            "airtime_purchases": airtime_count
        },
        "recent_transactions": recent_transactions,
        # Additional stats
        "available_balance": float(balance_stats.total_available or 0),
        "held_balance": float(balance_stats.total_held or 0),
        "procurement_count": procurement_stats.total if procurement_stats.total else 0,
        "procurement_total": float(procurement_stats.total_amount) if procurement_stats.total_amount else 0.0
    }

def search_companies(db: Session, query_str: str, skip: int = 0, limit: int = 50):
    """Search companies by name, email, or phone"""
    search_pattern = f"%{query_str}%"
    return db.query(Company).filter(
        or_(
            Company.name.ilike(search_pattern),
            Company.email.ilike(search_pattern),
            Company.phone.ilike(search_pattern)
        )
    ).filter(Company.is_active == True).order_by(Company.name).offset(skip).limit(limit).all()

def get_company_by_email(db: Session, email: str):
    """Get company by email"""
    return db.query(Company).filter(Company.email == email).first()

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

