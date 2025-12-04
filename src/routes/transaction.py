# src/routes/transactions.py (update your existing file)
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from src.models.transaction import User, ProcurementStatus
from src.services.finance_service import FinanceService

from src.core.database import get_db
from src.core.auth_dependencies import get_current_user, require_role
from src.services.transaction_service import *
from src.services.auth_service import AuthService
from src.schemas.transaction import *
 
logger = logging.getLogger("router logging")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


transaction_router = APIRouter(prefix="/api/v1/transactions/request", tags=["Transactions"])
country_router = APIRouter(prefix="/api/v1/countries", tags=["Countries"])
user_router = APIRouter(prefix="/api/v1/users", tags=["Users"])
finance_router = APIRouter(prefix="/api/v1/finance", tags=["Finance"])
fee_router = APIRouter(prefix="/api/v1/fee-config", tags=["Fee Configuration"])
procurement_router = APIRouter(prefix="/api/v1/procurements", tags=["Procurements"])
company_router = APIRouter(prefix="/api/v1/companies", tags=["Companies"])


UPLOAD_DIR = "uploads/procurements"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==================== COMPANY ENDPOINTS ====================

@company_router.get("/", response_model=List[CompanyResponse])
def get_companies(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    active_only: bool = Query(True, description="Return only active companies"),
    current_user: User = Depends(require_role(["ADMIN", "MAKER", "CHECKER"])),
    db: Session = Depends(get_db)
):
    """
    Get all companies.
    
    - **admin** and **viewer** roles can access
    - Supports pagination
    - Can filter by active status
    """
    companies = list_companies(db, skip=skip, limit=limit, active_only=active_only)
    return companies

@company_router.get("/count", response_model=dict)
def get_companies_count(
    active_only: bool = Query(True, description="Count only active companies"),
    current_user: User = Depends(require_role(["ADMIN", "MAKER", "CHECKER"])),
    db: Session = Depends(get_db)
):
    """
    Get total number of companies.
    """
    count = get_companies_count(db, active_only=active_only)
    return {"total": count}

@company_router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific company by ID.
    
    - All authenticated users can access
    """
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found"
        )
    return company

@company_router.post("/", response_model=CompanyResponse, status_code=201)
def create_company(
    company_data: CompanyCreate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Create a new company.
    
    - Only **admin** role can create companies
    - Email and name must be unique
    """
    try:
        company = create_company(db, company_data)
        return company
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating company: {str(e)}"
        )

@company_router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    update_data: CompanyUpdate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Update an existing company.
    
    - Only **admin** role can update companies
    - Partial updates are supported
    """
    try:
        company = update_company(db, company_id, update_data)
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company with ID {company_id} not found"
            )
        return company
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@company_router.delete("/{company_id}", status_code=200)
def delete_company(
    company_id: int,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Soft delete (deactivate) a company.
    
    - Only **admin** role can delete companies
    - This is a soft delete (sets is_active = False)
    """
    success = delete_company(db, company_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Company with ID {company_id} not found"
        )
    return {"message": f"Company {company_id} deactivated successfully"}

@company_router.post("/{company_id}/activate", response_model=CompanyResponse)
def activate_company(
    company_id: int,
    current_user: User = Depends(require_role(["ADMIN", "MAKER", "CHECKER"])),
    db: Session = Depends(get_db)
):
    """
    Activate a deactivated company.
    
    - Only **admin** role can activate companies
    """
    success = activate_company(db, company_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Company with ID {company_id} not found"
        )
    
    company = get_company(db, company_id)
    return company

@company_router.get("/{company_id}/stats", response_model=CompanyStatsResponse)
def get_company_stats(
    company_id: int,
    current_user: User = Depends(require_role(["ADMIN", "MAKER", "CHECKER", "USER"])),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a company.
    
    - All authenticated users with any role can access their own company stats
    - **admin** can access any company stats
    """
    # Check if user has permission to view this company's stats
    if current_user.role != "admin" and current_user.company_id != company_id:
        raise HTTPException(
            status_code=403,
            detail="You can only view statistics for your own company"
        )
    
    stats = get_company_stats(db, company_id)
    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"Company with ID {company_id} not found"
        )
    
    return stats

@company_router.get("/search/", response_model=List[CompanyResponse])
def search_companies(
    q: str = Query(..., min_length=2, max_length=100, description="Search term"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role(["ADMIN", "MAKER", "CHECKER", "USER"])),
    db: Session = Depends(get_db)
):
    """
    Search companies by name, email, or phone.
    
    - **admin** and **viewer** roles can search
    - Minimum 2 characters required for search term
    """
    companies = search_companies(db, q, skip=skip, limit=limit)
    return companies

@company_router.get("/email/{email}", response_model=CompanyResponse)
def get_company_by_email(
    email: str,
    current_user: User = Depends(require_role(["ADMIN", "MAKER", "CHECKER", "USER"])),
    db: Session = Depends(get_db)
):
    """
    Get company by email.
    
    - **admin** and **viewer** roles can access
    """
    company = get_company_by_email(db, email)
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company with email {email} not found"
        )
    return company

# ==================== EXISTING ENDPOINTS (Keep as is) ====================

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
    

# ---------- GET deposits ----------
@transaction_router.get("/deposits", response_model=List[DepositResponse])
def get_deposits(
    recipient: Optional[str] = Query(None),
    partner_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return get_deposit_transactions(db, recipient, partner_id, status)

# ---------- GET withdrawals ----------
@transaction_router.get("/withdrawals", response_model=List[WithdrawalResponse])
def get_withdrawals(
    sender: Optional[str] = Query(None),
    partner_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return get_withdrawal_transactions(db, sender, partner_id, status)

# ---------- GET airtime purchases ----------
@transaction_router.get("/airtime", response_model=List[AirtimeResponse])
def get_airtime(
    recipient: Optional[str] = Query(None),
    partner_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return get_airtime_purchase_transactions(db, recipient, partner_id, status)

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
    return AuthService.create_user(db, data)

@user_router.get("/", response_model=list[UserResponse])
def retrieve(db: Session = Depends(get_db)):
    return AuthService.list_users(db)

@user_router.get("/{user_id}", response_model=UserResponse)
def retrieve_one(user_id: int, db: Session = Depends(get_db)):
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user

@user_router.put("/{user_id}", response_model=UserUpdate)
def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    update_data = user_update.model_dump(exclude_unset=True)  # only fields sent
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    user = AuthService.update_user(db, user_id, update_data)
    return user

@user_router.post("/change-password", response_model=PasswordChangeResponse)
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    
    Requires:
    - **old_password**: Current password
    - **new_password**: New password (min 8 chars, with number, uppercase, lowercase)
    - **confirm_password**: Confirm new password
    
    Validates:
    - Old password must be correct
    - New password must meet strength requirements
    - New password must match confirmation
    - New password must be different from old password
    """
    try:
        success = AuthService.change_password(
            db=db,
            user_id=current_user.id,
            old_password=password_data.old_password,
            new_password=password_data.new_password,
            confirm_password=password_data.confirm_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
        
        return PasswordChangeResponse(message="Password changed successfully")
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    

@finance_router.get("/balance/summary", response_model=BalanceSummaryResponse)
def get_balance_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive balance summary for current user's company
    """
    summary = FinanceService.get_balance_summary(db, current_user.company_id)
    return summary

@finance_router.get("/balance/{country_id}")
def get_country_balance(
    country_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get balance for a specific country
    """
    balance = FinanceService.get_company_balance(db, current_user.company_id, country_id)
    
    if not balance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No balance found for country ID {country_id}"
        )
    
    # Get country name
    from src.models.transaction import Country
    country = db.query(Country).filter(Country.id == country_id).first()
    
    return {
        "country_id": country_id,
        "country_name": country.name if country else "Unknown",
        "available_balance": float(balance.available_balance),
        "held_balance": float(balance.held_balance),
        "effective_balance": float(balance.effective_balance),
        "partner_code": balance.partner_code
    }

@finance_router.get("/balances")
def list_all_balances(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all balances for current user's company
    """
    balances = FinanceService.get_all_company_balances(db, current_user.company_id)
    return balances

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
async def create_procurement_endpoint(
    data: ProcurementCreate,
    current_user: User = Depends(require_role(["ADMIN", "MAKER"])),
    db: Session = Depends(get_db),
    slip: UploadFile = File(None)
):
    """
    Create a new procurement
    
    - Requires ADMIN or MAKER role
    - Creates procurement in PENDING status
    - Balance is NOT updated until approved
    """
    try:
        # Ensure procurement is for user's company
        # Only admins can create for other companies
        if current_user.role != "ADMIN" and current_user.company_id != data.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create procurements for your own company"
            )
        
        file_path = None
        if slip:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{slip.filename}"
            file_path = f"{UPLOAD_DIR}/{filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save file
            with open(file_path, "wb") as f:
                content = await slip.read()
                f.write(content)
        
        # Import the service
        from src.services.procurement_service import ProcurementService
        
        procurement = ProcurementService.create_procurement(
            db=db,
            procurement_data=data,
            initiated_by_user_id=current_user.id,
            file_path=file_path
        )
        return procurement
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating procurement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create procurement: {str(e)}"
        )

@procurement_router.post("/{procurement_id}/approve", response_model=ProcurementResponse)
def approve_procurement_endpoint(
    procurement_id: int,
    action_data: ProcurementAction,
    current_user: User = Depends(require_role(["ADMIN", "CHECKER"])),
    db: Session = Depends(get_db)
):
    """
    Approve a procurement
    
    - Requires ADMIN or CHECKER role
    - Updates the country's available balance
    - Changes status from PENDING to SUCCESS
    """
    from src.services.procurement_service import ProcurementService
    
    success, message, procurement = ProcurementService.approve_procurement(
        db=db,
        procurement_id=procurement_id,
        validated_by_user_id=current_user.id,
        notes=action_data.notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Get updated balance info
    if procurement.balance:
        procurement.available_balance = procurement.balance.available_balance
    
    return procurement

@procurement_router.post("/{procurement_id}/reject", response_model=ProcurementResponse)
def reject_procurement_endpoint(
    procurement_id: int,
    action_data: ProcurementAction,
    current_user: User = Depends(require_role(["ADMIN", "CHECKER"])),
    db: Session = Depends(get_db)
):
    """
    Reject a procurement
    
    - Requires ADMIN or CHECKER role
    - Changes status from PENDING to FAILED
    - Does NOT update balance
    """
    from src.services.procurement_service import ProcurementService
    
    success, message, procurement = ProcurementService.reject_procurement(
        db=db,
        procurement_id=procurement_id,
        validated_by_user_id=current_user.id,
        notes=action_data.notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return procurement

@procurement_router.get("/summary")
def get_procurement_summary_endpoint(
    company_id: Optional[int] = None,
    current_user: User = Depends(require_role(["ADMIN", "CHECKER", "MAKER", "USER"])),
    db: Session = Depends(get_db)
):
    """
    Get procurement summary
    
    - Users can see their own company's summary
    - Admins can see all or filter by company_id
    """
    from src.services.procurement_service import ProcurementService
    
    # If not admin, restrict to user's company
    if current_user.role != "ADMIN":
        company_id = current_user.company_id
    
    summary = ProcurementService.get_procurement_summary(db, company_id)
    return summary

@procurement_router.get("/")
def list_procurements_endpoint(
    company_id: Optional[int] = None,
    country_id: Optional[int] = None,
    status: Optional[ProcurementStatus] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_role(["ADMIN", "CHECKER", "MAKER", "USER"])),
    db: Session = Depends(get_db)
):
    """
    List procurements with filtering and pagination
    
    - Non-admins can only see their own company's procurements
    """
    from src.services.procurement_service import ProcurementService
    
    # If not admin, restrict to user's company
    if current_user.role != "ADMIN":
        company_id = current_user.company_id
    
    procurements, total = ProcurementService.get_procurements(
        db=db,
        company_id=company_id,
        country_id=country_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    # Add balance info for approved procurements
    for proc in procurements:
        if proc.balance:
            proc.available_balance = proc.balance.available_balance
    
    return {
        "procurements": procurements,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(procurements)) < total
        }
    }