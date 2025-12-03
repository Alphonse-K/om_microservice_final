from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator
from typing import Literal, List, Any, Dict

from src.core.constants import TransactionStatus, WithdrawalStatus


# -------------------------- BASE SCHEMAS -----------------------------------

# ------------------- Deposit -------------------
class DepositBase(BaseModel):
    recipient: str = Field(..., min_length=9, max_length=15)
    amount: Decimal = Field(..., ge=2000, le=15_000_000)
    transaction_type: Literal["deposit"] = Field(..., description="Must be 'deposit'")
    partner_id: str = Field(..., max_length=100)

# ------------------- Withdrawal -------------------
class WithdrawalBase(BaseModel):
    sender: str = Field(..., min_length=9, max_length=15)
    amount: Decimal = Field(..., ge=2000, le=15_000_000)
    transaction_type: Literal["withdrawal"] = Field(..., description="Must be 'withdrawal'")
    partner_id: str = Field(..., max_length=100)

# ------------------- Airtime -------------------
class AirtimeBase(BaseModel):
    recipient: str = Field(..., min_length=9, max_length=15)
    amount: Decimal = Field(..., ge=1000, le=250_000)
    transaction_type: Literal["credit_purchase"] = Field(..., description="Must be 'credit_purchase'")
    partner_id: str = Field(..., max_length=100)


# -------------------------- CREATE SCHEMAS ---------------------------------

class DepositCreate(DepositBase):
    pass


class WithdrawalCreate(WithdrawalBase):
    pass 


class AirtimeCreate(AirtimeBase):
    pass 


# -------------------------- RESPONSE SCHEMAS -------------------------------

class DepositResponse(DepositBase):
    id: int
    status: TransactionStatus
    created_at: datetime
    validated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WithdrawalResponse(WithdrawalBase):
    id: int
    status: WithdrawalStatus
    created_at: datetime
    validated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AirtimeResponse(AirtimeBase):
    id: int
    status: TransactionStatus
    created_at: datetime
    validated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------- GENERIC OPERATION RESPONSE -------------------------

class OperationResponse(BaseModel):
    status: str
    message: str
    deposit_id: Optional[int] = None
    withdrawal_id: Optional[int] = None
    airtime_id: Optional[int] = None
    sim_used: Optional[str] = None
    gateway_response: Optional[str] = None


class CountryBase(BaseModel):
    name: str
    iso_code: str = Field(..., max_length=3)
    phone_code: Optional[str] = None
    currency: Optional[str] = None
    is_active: bool = True

class CountryCreate(CountryBase):
    pass

class CountryUpdate(BaseModel):
    name: Optional[str] = None
    phone_code: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None

class CountryResponse(CountryBase):
    id: int
    model_config = {"from_attributes": True}


class CompanyBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

class CompanyResponse(CompanyBase):
    id: int
    model_config = {"from_attributes": True}

class CompanyStatsResponse(BaseModel):
    company_id: int
    company_name: str
    total_users: int
    active_users: int
    total_balance: float
    total_transactions: int
    transaction_breakdown: Dict[str, int]
    recent_transactions: List[Dict[str, Any]] = []


class CompanyBalanceBase(BaseModel):
    """Base schema for company country balance"""
    company_id: int = Field(..., ge=1, description="Company ID")
    country_id: int = Field(..., ge=1, description="Country ID")
    partner_code: str = Field(..., min_length=1, max_length=20, description="Partner code for this country")

class CompanyBalanceCreate(CompanyBalanceBase):
    """Schema for creating a new company country balance"""
    available_balance: Decimal = Field(default=0, ge=0, description="Initial available balance")
    held_balance: Decimal = Field(default=0, ge=0, description="Initial held balance")

class CompanyBalanceUpdate(BaseModel):
    """Schema for updating company country balance"""
    partner_code: Optional[str] = Field(None, min_length=1, max_length=20, description="Partner code")
    available_balance: Optional[Decimal] = Field(None, ge=0, description="Available balance")
    held_balance: Optional[Decimal] = Field(None, ge=0, description="Held balance")
    
    model_config = ConfigDict(extra="forbid")  # Prevent extra fields

class CompanyBalanceResponse(CompanyBalanceBase):
    """Schema for company country balance response"""
    id: int
    available_balance: Decimal
    held_balance: Decimal
    effective_balance: Decimal  # Computed property
    total_balance: Decimal      # Computed property
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "company_id": 1,
                "country_id": 84,  # Iran country code
                "partner_code": "IRN001",
                "available_balance": "10000.00",
                "held_balance": "2500.00",
                "effective_balance": "7500.00",
                "total_balance": "12500.00"
            }
        }
    )
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str
    is_active: bool = True

class UserCreate(UserBase):
    company_id: int
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    email: Optional[EmailStr] 
    company_id: int

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    company_id: int
    is_active: bool
    last_login: Optional[datetime]
    
    model_config = {"from_attributes": True}


class FeeConfigBase(BaseModel):
    source_country_id: int = Field(..., example=1)
    destination_country_id: int = Field(..., example=2)
    fee_type: str = Field(..., example="percent")
    flat_fee: Decimal = Field(default=0, example="5.00")
    percent_fee: Decimal = Field(default=0, example="1.50")
    min_fee: Decimal = Field(default=0, example="0.50")
    max_fee: Optional[Decimal] = Field(default=None, example="10.00")
    is_active: bool = Field(default=True, example=True)
    
    @field_validator('percent_fee')
    @classmethod
    def validate_percent_fee(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 100:
            raise ValueError('Percent fee must be between 0 and 100')
        return v
    
    @field_validator('max_fee', mode='before')
    @classmethod
    def validate_max_fee(cls, v: Any) -> Optional[Decimal]:
        if v is not None and isinstance(v, str) and len(v) > 50:
            # Fix corrupted max_fee values
            return None
        return v


class FeeConfigCreate(FeeConfigBase):
    pass

class FeeConfigUpdate(BaseModel):
    flat_fee: Optional[Decimal] = None
    percent_fee: Optional[Decimal] = None
    min_fee: Optional[Decimal] = None
    max_fee: Optional[Decimal] = None
    is_active: Optional[bool] = None


class FeeConfigResponse(FeeConfigBase):
    id: int = Field(..., example=1)
    
    model_config = {
        "from_attributes": True,
        "json_encoders": {
            Decimal: str
        }
    }


class ProcurementBase(BaseModel):
    company_id: int = Field(..., example=1)
    country_id: int = Field(..., example=1)
    bank_name: str = Field(..., example="Ecobank Senegal")
    slip_number: str = Field(..., example="GN20241130001")
    amount: Decimal = Field(..., example="1000.00")
    slip_file_path: Optional[str] = Field(None, example="/uploads/slips/slip123.pdf")
    
    @field_validator('amount')
    @classmethod
    def validate_amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
    
    @field_validator('amount', mode='before')
    @classmethod
    def fix_corrupted_amount(cls, v: Any) -> Decimal:
        if isinstance(v, str) and len(v) > 50:
            # Fix corrupted amount values in Swagger
            return Decimal("1000.00")
        return v


class ProcurementCreate(ProcurementBase):
    pass


class ProcurementUpdate(BaseModel):
    validation_date: Optional[datetime] = None
    status: Optional[str] = None


class ProcurementResponse(ProcurementBase):
    id: int = Field(..., example=1)
    initiation_date: datetime = Field(..., example="2024-11-30T16:02:36.005Z")
    validation_date: Optional[datetime] = Field(None, example="2024-11-30T16:02:36.005Z")
    slip_file_path: Optional[str]
    status: str = Field(..., example="pending")
    
    model_config = {
        "from_attributes": True,
        "json_encoders": {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
    }

class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="user@company.com")
    password: str = Field(..., example="your_password")
    
    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class OTPVerify(BaseModel):
    email: EmailStr = Field(..., example="user@company.com")
    otp_code: str = Field(..., example="123456")
    
    @field_validator('otp_code')
    @classmethod
    def validate_otp_format(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP must be 6 digits')
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutResponse(BaseModel):
    message: str

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, example="Production Key")
    expires_at: Optional[datetime] = None
    permissions: List[str] = Field(
        default=["transactions:read"],
        example=["transactions:read", "transactions:write"]
    )
    
    @field_validator('permissions')
    def validate_permissions(cls, v):
        valid_permissions = {"transactions:read", "transactions:write", "users:read", "reports:read"}
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(f"Invalid permission: {perm}")
        return v

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: str  # Only shown once during creation
    secret: str  # Only shown once during creation
    is_active: bool
    permissions: List[str]
    expires_at: Optional[datetime]
    created_at: datetime

class APIKeyListResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    last_used: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]


class PasswordChange(BaseModel):
    """Schema for password change request"""
    old_password: str = Field(
        ..., 
        min_length=1, 
        description="Current password"
    )
    new_password: str = Field(
        ..., 
        min_length=8, 
        description="New password (min 8 characters)"
    )
    confirm_password: str = Field(
        ..., 
        min_length=8, 
        description="Confirm new password"
    )
    
    @field_validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password cannot exceed 128 characters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one number")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v
    
    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        """Ensure new_password and confirm_password match"""
        # Use info.data.get() to safely access the value
        new_password = info.data.get('new_password')
        if new_password is not None and v != new_password:
            raise ValueError('Passwords do not match')
        return v
    

class PasswordChangeResponse(BaseModel):
    """Schema for password change response"""
    message: str = Field(..., description="Success message")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Password changed successfully"
            }
        }
    }


class OTPResponse(BaseModel):
    """Response model for OTP login"""
    message: str = Field(..., description="Success message")
    expires_in: int = Field(..., description="OTP expiry time in seconds")
    debug_info: Optional[Dict[str, Any]] = Field(
        None, 
        description="Debug information (development only)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "OTP sent to your registered email",
                "expires_in": 300,
                "debug_info": {
                    "email": "user@example.com",
                    "otp_code": "123456",
                    "user_id": 1,
                    "client_ip": "192.168.1.1"
                }
            }
        }
    }


