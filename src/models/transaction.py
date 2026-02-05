from sqlalchemy import (
    Column, Integer, Text, Numeric, String, DateTime, Boolean, ForeignKey, 
    UniqueConstraint, Enum as SAEnum, JSON, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
from enum import Enum


# ========== ENUMS ==========
class TransactionStatus(str, Enum):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcurementStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class PendingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class TransactionType(str, Enum):
    CASHIN = "cashin"
    CASHOUT = "cashout"
    AIRTIME = "airtime"


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    CHECKER = "CHECKER"
    USER = "USER"
    MAKER = "MAKER"


# ========== CORE MODELS ==========
class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    iso_code = Column(String(3), nullable=False, unique=True)
    phone_code = Column(String(10), nullable=True)
    currency = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    procurements = relationship("Procurement", back_populates="country")
    fee_configs_destination = relationship("FeeConfig", foreign_keys="[FeeConfig.destination_country_id]", back_populates="destination_country")
    balances = relationship("CompanyCountryBalance", back_populates="country")
    
    # NEW: Relationships to specific transaction types
    deposit_transactions = relationship("DepositTransaction", back_populates="country")
    withdrawal_transactions = relationship("WithdrawalTransaction", back_populates="country")
    airtime_purchases = relationship("AirtimePurchase", back_populates="country")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    email = Column(String(150), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    users = relationship("User", back_populates="company")
    balances = relationship("CompanyCountryBalance", back_populates="company")
    procurements = relationship("Procurement", back_populates="company")
    api_keys = relationship("APIKey", back_populates="company")
    
    # NEW: Relationships to specific transaction types
    deposit_transactions = relationship("DepositTransaction", back_populates="company")
    withdrawal_transactions = relationship("WithdrawalTransaction", back_populates="company")
    airtime_purchases = relationship("AirtimePurchase", back_populates="company")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(
        SAEnum(RoleEnum, name="role_enum"),
        nullable=False,
        default=RoleEnum.USER
    )
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String, nullable=True)
    last_login_user_agent = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="users")
    otp_codes = relationship("OTPCode", back_populates="user")
    blacklisted_tokens = relationship("JWTBlacklist", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")


# ========== AUTH MODELS ==========
class JWTBlacklist(Base):
    __tablename__ = "jwt_blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String(50))
    
    user = relationship("User", back_populates="blacklisted_tokens")
    
    __table_args__ = (
        Index('ix_jwt_blacklist_user_id', 'user_id'),
        Index('ix_jwt_blacklist_expires', 'expires_at'),
    )


class OTPCode(Base):
    __tablename__ = "otp_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(6), nullable=False)
    purpose = Column(String(20), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="otp_codes")
    
    __table_args__ = (
        Index('ix_otp_codes_user_purpose', 'user_id', 'purpose'),
        Index('ix_otp_codes_expires', 'expires_at'),
    )


class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100), nullable=False)
    key = Column(String(64), unique=True, index=True, nullable=False)
    secret = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company", back_populates="api_keys")
    
    __table_args__ = (
        Index('ix_api_keys_company', 'company_id'),
        Index('ix_api_keys_active', 'is_active'),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(64), unique=True, index=True, nullable=False)
    device_info = Column(JSON)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="refresh_tokens")
    
    __table_args__ = (
        Index('ix_refresh_tokens_user_active', 'user_id', 'is_active'),
    )


# ========== FINANCE MODELS ==========
class CompanyCountryBalance(Base):
    __tablename__ = "company_country_balances"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    partner_code = Column(String(20), nullable=False)
    
    # Dual balance system
    available_balance = Column(Numeric(14, 2), default=0)
    held_balance = Column(Numeric(14, 2), default=0)

    company = relationship("Company", back_populates="balances")
    country = relationship("Country", back_populates="balances")

    __table_args__ = (
        UniqueConstraint("company_id", "country_id", name="uq_company_country"),
    )

    @property
    def effective_balance(self):
        return self.available_balance - self.held_balance


# class FeeConfig(Base):
#     __tablename__ = "fee_configs"

#     id = Column(Integer, primary_key=True, index=True)

#     transaction_type = Column(
#         SAEnum(TransactionType, name="transaction_type_enum"),
#         nullable=False
#     )

#     destination_country_id = Column(
#         Integer,
#         ForeignKey("countries.id"),
#         nullable=False
#     )

#     # Fee calculation
#     fee_type = Column(String(20), nullable=False)  # flat, percent, mixed
#     flat_fee = Column(Numeric(10, 6), default=0)
#     percent_fee = Column(Numeric(10, 6), default=0)
#     min_fee = Column(Numeric(10, 6), default=0)
#     max_fee = Column(Numeric(10, 6), nullable=True)

#     # Workflow fields
#     status = Column(String(20), default="PENDING")
#     created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
#     approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
#     approved_at = Column(DateTime(timezone=True), nullable=True)

#     is_active = Column(Boolean, default=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())

#     destination_country = relationship(
#         "Country",
#         foreign_keys=[destination_country_id],
#         back_populates="fee_configs_destination"
#     )

#     __table_args__ = (
#         UniqueConstraint(
#             "transaction_type",
#             "destination_country_id",
#             "is_active",
#             name="uix_fee_active_rule"
#         ),
#     )

class FeeConfig(Base):
    __tablename__ = "fee_configs"

    id = Column(Integer, primary_key=True, index=True)

    transaction_type = Column(
        SAEnum(TransactionType, name="transaction_type_enum"),
        nullable=False
    )

    destination_country_id = Column(
        Integer,
        ForeignKey("countries.id"),
        nullable=False
    )

    # ==========================
    # Fee calculation
    # ==========================
    fee_type = Column(String(20), nullable=False)  # flat, percent, mixed
    flat_fee = Column(Numeric(10, 6), default=0)
    percent_fee = Column(Numeric(10, 6), default=0)
    min_fee = Column(Numeric(10, 6), default=0)
    max_fee = Column(Numeric(10, 6), nullable=True)

    # ==========================
    # Versioning
    # ==========================
    version = Column(Integer, nullable=False, default=1)

    previous_config_id = Column(
        Integer,
        ForeignKey("fee_configs.id"),
        nullable=True
    )

    previous_config = relationship(
        "FeeConfig",
        remote_side=[id],
        uselist=False
    )

    # ==========================
    # Workflow
    # ==========================
    status = Column(String(20), default="PENDING")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    destination_country = relationship(
        "Country",
        foreign_keys=[destination_country_id],
        back_populates="fee_configs_destination"
    )

    __table_args__ = (
        UniqueConstraint(
            "transaction_type",
            "destination_country_id",
            "is_active",
            name="uix_fee_active_rule"
        ),
    )

class Procurement(Base):
    __tablename__ = "procurements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    
    # Add balance_id field
    balance_id = Column(Integer, ForeignKey("company_country_balances.id"), nullable=True)
    
    bank_name = Column(String(255), nullable=False)
    slip_number = Column(String(255), nullable=False, unique=True)
    slip_file_path = Column(String(500), nullable=True)

    initiation_date = Column(DateTime(timezone=True), server_default=func.now())
    validation_date = Column(DateTime(timezone=True), nullable=True)
    
    # Add who initiated and validated
    initiated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    amount = Column(Numeric(18, 2), nullable=False)
    status = Column(SAEnum(ProcurementStatus), default=ProcurementStatus.PENDING)
    notes = Column(String(1000), nullable=True)

    # Relationships
    company = relationship("Company", back_populates="procurements")
    country = relationship("Country", back_populates="procurements")
    balance = relationship("CompanyCountryBalance")
    initiator_user = relationship("User", foreign_keys=[initiated_by])
    validator_user = relationship("User", foreign_keys=[validated_by])
    
    __table_args__ = (
        Index('ix_procurement_company_country', 'company_id', 'country_id'),
        Index('ix_procurement_status', 'status'),
    )

# ========== DEPOSIT TRANSACTION ==========
class DepositTransaction(Base):
    __tablename__ = "deposit_transactions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction details
    amount = Column(Numeric(14, 2), nullable=False)
    recipient = Column(String(20), nullable=False)
    status = Column(String(20), default='initiated')
    
    # Foreign keys
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    balance_id = Column(Integer, ForeignKey("company_country_balances.id"), nullable=True)
    pending_transaction_id = Column(Integer, ForeignKey("pending_transactions.id"), nullable=True)
    
    # Partner info
    partner_id = Column(String(100), nullable=False)
    service_partner_id = Column(String(100), nullable=True)
    
    # Gateway fields
    gateway_response = Column(Text, nullable=True)
    gateway_transaction_id = Column(String(100), nullable=True)
    sim_used = Column(String(20), nullable=True)
    
    # Fees and amounts
    fee_amount = Column(Numeric(10, 2), default=0)
    net_amount = Column(Numeric(10, 2), nullable=False)
    
    # Balance tracking
    before_balance = Column(Numeric(14, 2), nullable=True)
    after_balance = Column(Numeric(14, 2), nullable=True)
        
    # Technical fields
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    validated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="deposit_transactions")
    country = relationship("Country", back_populates="deposit_transactions")
    balance = relationship("CompanyCountryBalance")
    pending_transaction = relationship("PendingTransaction")


# ========== WITHDRAWAL TRANSACTION ==========
class WithdrawalTransaction(Base):
    __tablename__ = "withdrawal_transactions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction details
    amount = Column(Numeric(14, 2), nullable=False)
    sender = Column(String(20), nullable=False)
    status = Column(String(20), default='initiated')
    
    # Foreign keys
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    balance_id = Column(Integer, ForeignKey("company_country_balances.id"), nullable=True)
    pending_transaction_id = Column(Integer, ForeignKey("pending_transactions.id"), nullable=True)
    
    # Partner info
    partner_id = Column(String(100), nullable=False)
    service_partner_id = Column(String(100), nullable=True)
    
    # Gateway fields
    gateway_response = Column(Text, nullable=True)
    gateway_transaction_id = Column(String(100), nullable=True)
    sim_used = Column(String(20), nullable=True)
    
    # Fees and amounts
    fee_amount = Column(Numeric(10, 2), default=0)
    net_amount = Column(Numeric(10, 2), nullable=False)
    
    # Balance tracking
    before_balance = Column(Numeric(14, 2), nullable=True)
    after_balance = Column(Numeric(14, 2), nullable=True)
        
    # Technical fields
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    validated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="withdrawal_transactions")
    country = relationship("Country", back_populates="withdrawal_transactions")
    balance = relationship("CompanyCountryBalance")
    pending_transaction = relationship("PendingTransaction")


# ========== AIRTIME PURCHASE ==========
class AirtimePurchase(Base):
    __tablename__ = "airtime_purchases"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction details
    amount = Column(Numeric(14, 2), nullable=False)
    recipient = Column(String(20), nullable=False)
    status = Column(String(20), default='initiated')
    
    # Foreign keys
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    balance_id = Column(Integer, ForeignKey("company_country_balances.id"), nullable=True)
    pending_transaction_id = Column(Integer, ForeignKey("pending_transactions.id"), nullable=True)
    
    # Partner info
    partner_id = Column(String(100), nullable=False)
    service_partner_id = Column(String(100), nullable=True)
    
    # Gateway fields
    gateway_response = Column(Text, nullable=True)
    gateway_transaction_id = Column(String(100), nullable=True)
    sim_used = Column(String(20), nullable=True)
    
    # Fees and amounts
    fee_amount = Column(Numeric(10, 2), default=0)
    net_amount = Column(Numeric(10, 2), nullable=False)
    
    # Balance tracking
    before_balance = Column(Numeric(14, 2), nullable=True)
    after_balance = Column(Numeric(14, 2), nullable=True)
        
    # Technical fields
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    validated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="airtime_purchases")
    country = relationship("Country", back_populates="airtime_purchases")
    balance = relationship("CompanyCountryBalance")
    pending_transaction = relationship("PendingTransaction")


# ========== PENDING TRANSACTION ==========
class PendingTransaction(Base):
    __tablename__ = "pending_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(
        SAEnum(TransactionType, name="transaction_type_enum"),
        nullable=False
    )
    msisdn = Column(String(20), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    partner_id = Column(String(100), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_iso = Column(String(3), nullable=True)
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    company = relationship("Company")
    
    # Relationships to specific transaction types
    deposit_transactions = relationship("DepositTransaction", back_populates="pending_transaction")
    withdrawal_transactions = relationship("WithdrawalTransaction", back_populates="pending_transaction")
    airtime_purchases = relationship("AirtimePurchase", back_populates="pending_transaction")