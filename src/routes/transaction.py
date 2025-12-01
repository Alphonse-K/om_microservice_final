import os
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from src.schemas.transaction import (
    DepositCreate, WithdrawalCreate, AirtimeCreate,
    DepositResponse, WithdrawalResponse, AirtimeResponse,
    UserCreate, UserUpdate, UserResponse, CountryCreate, CountryUpdate, CountryResponse,
    CompanyBalanceCreate, CompanyBalanceUpdate, CompanyBalanceResponse,
    FeeConfigCreate, FeeConfigUpdate, FeeConfigResponse,
    ProcurementCreate, ProcurementUpdate, ProcurementResponse
)
from src.core.database import get_db
from src.services.transaction_service import (
    create_deposit, create_airtime_purchase, intitiate_withdrawal_transaction,
    create_user, list_users, get_user, update_user, create_country, list_countries, 
    get_country, update_country,
    create_balance, list_balances, get_balance, update_balance,
    create_fee_config, list_fee_configs, get_fee_config, update_fee_config,
    create_procurement, list_procurements, get_procurement, update_procurement
)    

transaction_router = APIRouter(prefix="/api/v1/transactions/request", tags=["Transactions"])
country_router = APIRouter(prefix="/api/v1/countries", tags=["Countries"])
user_router = APIRouter(prefix="/api/v1/users", tags=["Users"])
balance_router = APIRouter(prefix="/api/v1/company-balances", tags=["Company Balances"])
fee_router = APIRouter(prefix="/api/v1/fee-config", tags=["Fee Configuration"])
procurement_router = APIRouter(prefix="/api/v1/procurements", tags=["Procurements"])

UPLOAD_DIR = "uploads/procurements"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------- DEPOSIT ----------------------
@transaction_router.post("/send/orange-money/", response_model=DepositResponse)
async def send_deposit(deposit: DepositCreate, db: Session = Depends(get_db)):
    try:
        result = await create_deposit(db, deposit)
        return result
    except Exception as e:
        raise HTTPException(status_code=429, detail=str(e))

# ---------------------- AIRTIME ----------------------
@transaction_router.post("/purchase/airtime/", response_model=AirtimeResponse)
async def purchase_airtime(airtime: AirtimeCreate, db: Session = Depends(get_db)):
    try:
        result = await create_airtime_purchase(db, airtime)
        return result
    except Exception as e:
        raise HTTPException(status_code=429, detail=str(e))

# ---------------------- WITHDRAWAL ----------------------
@transaction_router.post("/initiate/withdrawal/", response_model=WithdrawalResponse)
async def initiate_withdrawal(withdrawal: WithdrawalCreate, db: Session = Depends(get_db)):
    try:
        result = await intitiate_withdrawal_transaction(db, withdrawal)
        return result
    except Exception as e:
        raise HTTPException(status_code=429, detail=str(e))

@country_router.post("/", response_model=CountryResponse)
def create(data: CountryCreate, db: Session = Depends(get_db)):
    return create_country(db, data)

@country_router.get("/", response_model=list[CountryResponse])
def retrieve_all(db: Session = Depends(get_db)):
    return list_countries(db)

@country_router.get("/{country_id}", response_model=CountryResponse)
def retrieve_one(country_id: int, db: Session = Depends(get_db)):
    country = get_country(db, country_id)
    if not country:
        raise HTTPException(404, "Country not found")
    return country

@country_router.put("/{country_id}", response_model=CountryResponse)
def update(country_id: int, data: CountryUpdate, db: Session = Depends(get_db)):
    updated = update_country(db, country_id, data)
    if not updated:
        raise HTTPException(404, "Country not found")
    return updated


@user_router.post("/", response_model=UserResponse)
def create(data: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, data)

@user_router.get("/", response_model=list[UserResponse])
def retrieve(db: Session = Depends(get_db)):
    return list_users(db)

@user_router.get("/{user_id}", response_model=UserResponse)
def retrieve_one(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user

@user_router.put("/{user_id}", response_model=UserResponse)
def update(user_id: int, data: UserUpdate, db: Session = Depends(get_db)):
    updated = update_user(db, user_id, data)
    if not updated:
        raise HTTPException(404, "User not found")
    return updated

@balance_router.post("/", response_model=CompanyBalanceResponse)
def create(data: CompanyBalanceCreate, db: Session = Depends(get_db)):
    return create_balance(db, data)

@balance_router.get("/", response_model=list[CompanyBalanceResponse])
def retrieve(db: Session = Depends(get_db)):
    return list_balances(db)

@balance_router.get("/{balance_id}", response_model=CompanyBalanceResponse)
def retrieve_one(balance_id: int, db: Session = Depends(get_db)):
    bal = get_balance(db, balance_id)
    if not bal:
        raise HTTPException(404, "Balance not found")
    return bal

@balance_router.put("/{balance_id}", response_model=CompanyBalanceResponse)
def update(balance_id: int, data: CompanyBalanceUpdate, db: Session = Depends(get_db)):
    updated = update_balance(db, balance_id, data)
    if not updated:
        raise HTTPException(404, "Balance not found")
    return updated

@fee_router.post("/", response_model=FeeConfigResponse)
def create(data: FeeConfigCreate, db: Session = Depends(get_db)):
    return create_fee_config(db, data)

@fee_router.get("/", response_model=list[FeeConfigResponse])
def list_all(db: Session = Depends(get_db)):
    return list_fee_configs(db)

@fee_router.get("/{config_id}", response_model=FeeConfigResponse)
def retrieve_one(config_id: int, db: Session = Depends(get_db)):
    config = get_fee_config(db, config_id)
    if not config:
        raise HTTPException(404, "Fee config not found")
    return config

@fee_router.put("/{config_id}", response_model=FeeConfigResponse)
def update(config_id: int, data: FeeConfigUpdate, db: Session = Depends(get_db)):
    updated = update_fee_config(db, config_id, data)
    if not updated:
        raise HTTPException(404, "Fee config not found")
    return updated


@procurement_router.post("/", response_model=ProcurementResponse)
async def create(data: ProcurementCreate, db: Session = Depends(get_db), slip: UploadFile = File(None)):
    file_path = None
    if slip:
        file_path = f"{UPLOAD_DIR}/{slip.filename}"
        with open(file_path, "wb") as f:
            f.write(await slip.read())

    return create_procurement(db, data, file_path)

@procurement_router.get("/", response_model=list[ProcurementResponse])
def list_all(db: Session = Depends(get_db)):
    return list_procurements(db)

@procurement_router.get("/{procurement_id}", response_model=ProcurementResponse)
def retrieve_one(procurement_id: int, db: Session = Depends(get_db)):
    proc = get_procurement(db, procurement_id)
    if not proc:
        raise HTTPException(404, "Procurement not found")
    return proc

@procurement_router.put("/{procurement_id}", response_model=ProcurementResponse)
def update(procurement_id: int, data: ProcurementUpdate, db: Session = Depends(get_db)):
    updated = update_procurement(db, procurement_id, data)
    if not updated:
        raise HTTPException(404, "Procurement not found")
    return updated
