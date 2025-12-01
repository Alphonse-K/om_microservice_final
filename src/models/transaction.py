# from sqlalchemy import Column, Integer, Text, Numeric, String, DateTime, Boolean, ForeignKey
# from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
# from src.core.database import Base
# from datetime import datetime, timezone
# from enum import Enum
# from sqlalchemy import Enum as SAEnum



# class DepositTransaction(Base):
#     __tablename__ = 'Deposit'

#     id = Column(Integer, primary_key=True, index=True)
#     recipient = Column(String(20), nullable=False)
#     amount = Column(Numeric(10, 2), nullable=False)
#     status = Column(String(20), default='created', nullable=False)
#     gateway_response = Column(Text, nullable=True)
#     transaction_type= Column(String(20), nullable=False)
#     sim_used = Column(String(20), nullable=True)
#     service_partner_id = Column(String(100), nullable=True)
#     partner_id = Column(String(100), nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     validated_at = Column(DateTime(timezone=True), nullable=True)
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#     error_message = Column(Text, nullable=True)


# class WithdrawalTransaction(Base):
#     __tablename__ = 'withdrawals'

#     id = Column(Integer, primary_key=True, index=True)
#     amount = Column(Numeric(10, 2), nullable=False)
#     sender = Column(String(20), nullable=False)
#     status = Column(String(20), default='initiated', nullable=False)
#     gateway_response = Column(Text, nullable=True)
#     sim_used = Column(String(20), nullable=True)
#     transaction_type = Column(String(20), nullable=False)
#     service_partner_id = Column(String(100), nullable=True)
#     partner_id = Column(String(100), nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     validated_at = Column(DateTime(timezone=True), nullable=True)
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#     error_message = Column(Text, nullable=True)
    

# class AirtimePurchase(Base):
#     __tablename__ = 'airtimes'

#     id = Column(Integer, primary_key=True, index=True)
#     recipient = Column(String(20), nullable=False)
#     amount = Column(Numeric(10, 2), nullable=False)
#     status = Column(String(20), default='created', nullable=False)
#     gateway_response = Column(Text, nullable=True)
#     sim_used = Column(String(20), nullable=True)
#     transaction_type = Column(String(20), nullable=False)
#     service_partner_id = Column(String(100), nullable=True)
#     partner_id = Column(String(100), nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     validated_at = Column(DateTime(timezone=True), nullable=True)
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#     error_message = Column(Text, nullable=True)


# class PendingTransaction(Base):
#     __tablename__ = "pending_transaction"

#     id = Column(Integer, primary_key=True, index=True)
#     transaction_type = Column(String, nullable=False)  # deposit | withdrawal | airtime
#     msisdn = Column(String, nullable=False)
#     amount = Column(Numeric(10, 2), nullable=False)
#     partner_id = Column(String, nullable=False)

#     status = Column(String, default="pending")  # pending | processing | done | failed
#     created_at = Column(DateTime, server_default=datetime.now(timezone.utc))


# class Country(Base):
#     __tablename__ = "country"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), nullable=False, unique=True)
#     iso_code = Column(String(3), nullable=False, unique=True)
#     phone_code = Column(String(10), nullable=True)
#     currency = Column(String(10), nullable=True)
#     is_active = Column(Boolean, default=True)
#     procurements = relationship("Procurement", back_populates="country")


# class Company(Base):
#     __tablename__ = "company"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(150), nullable=False, unique=True)
#     email = Column(String(150), nullable=False, unique=True)
#     phone = Column(String(50), nullable=True)
#     address = Column(String(255), nullable=True)
#     is_active = Column(Boolean, default=True)
#     procurements = relationship("Procurement", back_populates="company")

#     # Relationships
#     users = relationship("User", back_populates="company")
#     balances = relationship("CompanyCountryBalance", back_populates="company")


# class User(Base):
#     __tablename__ = "user"

#     id = Column(Integer, primary_key=True, index=True)
#     company_id = Column(Integer, ForeignKey("company.id"))
#     name = Column(String(150), nullable=False)
#     email = Column(String(150), nullable=False, unique=True)
#     password_hash = Column(String(255), nullable=False)
#     role = Column(String(20), nullable=False)  # admin | maker | checker
#     is_active = Column(Boolean, default=True)

#     company = relationship("Company", back_populates="users")


# class CompanyCountryBalance(Base):
#     __tablename__ = "company_country_balance"

#     id = Column(Integer, primary_key=True, index=True)
#     company_id = Column(Integer, ForeignKey("company.id"))
#     country_id = Column(Integer, ForeignKey("country.id"))

#     # NEW: Country-specific code per company (ex: SN-WAVE-001)
#     company_country_code = Column(String(20), nullable=False)

#     balance = Column(Numeric(14, 2), default=0)

#     company = relationship("Company", back_populates="balances")
#     country = relationship("Country")


# class FeeConfig(Base):
#     __tablename__ = "fee_config"

#     id = Column(Integer, primary_key=True, index=True)

#     source_country_id = Column(Integer, ForeignKey("country.id"), nullable=False)
#     destination_country_id = Column(Integer, ForeignKey("country.id"), nullable=False)

#     fee_type = Column(String(20), nullable=False)  # "flat", "percent", "mixed"
#     flat_fee = Column(Numeric(10, 2), default=0)
#     percent_fee = Column(Numeric(5, 2), default=0)  # 0–100%
#     min_fee = Column(Numeric(10, 2), default=0)
#     max_fee = Column(Numeric(10, 2), nullable=True)

#     is_active = Column(Boolean, default=True)

#     source_country = relationship("Country", foreign_keys=[source_country_id])
#     destination_country = relationship("Country", foreign_keys=[destination_country_id])


# class ProcurementStatus(Enum):
#     PENDING = "pending"
#     SUCCESS = "success"
#     FAILED = "failed"


# class Procurement(Base):
#     __tablename__ = "procurements"

#     id = Column(Integer, primary_key=True, index=True)

#     company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
#     company = relationship("Company", back_populates="procurements")

#     country_id = Column(Integer, ForeignKey("country.id"), nullable=False)
#     country = relationship("Country", back_populates="procurements")

#     bank_name = Column(String(255), nullable=False)

#     slip_number = Column(String(255), nullable=False, unique=True)
#     slip_file_path = Column(String(500), nullable=True)

#     initiation_date = Column(DateTime, default=datetime.now(timezone.utc))
#     validation_date = Column(DateTime, nullable=True)

#     amount = Column(Numeric(18, 2), nullable=False)

#     status = Column(
#         SAEnum(ProcurementStatus), 
#         default=ProcurementStatus.PENDING, 
#         nullable=False
#     )
# from sqlalchemy import (
#     Column, Integer, Text, Numeric, String, DateTime, Boolean, ForeignKey, 
#     UniqueConstraint, Enum as SAEnum, JSON, Index
# )
# from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
# from src.core.database import Base
# from datetime import datetime, timezone
# from enum import Enum


# class TransactionStatus(str, Enum):
#     INITIATED = "initiated"    # funds held
#     SUCCESS = "success"    # debit/credit applied
#     FAILED = "failed"
#     CANCELLED = "cancelled"


# class ProcurementStatus(str, Enum):
#     PENDING = "pending"
#     SUCCESS = "success"
#     FAILED = "failed"


# class PendingStatus(str, Enum):
#     PENDING = "pending"
#     PROCESSING = "processing"
#     DONE = "done"
#     FAILED = "failed"


# class TransactionType(str, Enum):
#     DEPOSIT = "deposit"
#     WITHDRAWAL = "withdrawal"
#     AIRTIME = "airtime"


# # class Transaction(Base):
# #     __tablename__ = "transactions"

# #     id = Column(Integer, primary_key=True, index=True)
    
# #     # Core transaction fields
# #     transaction_type = Column(String(20), nullable=False)  # deposit|withdrawal|airtime
# #     amount = Column(Numeric(14, 2), nullable=False)
# #     msisdn = Column(String(20), nullable=False)    
    
# #     # Status tracking
# #     status = Column(SAEnum(TransactionStatus), default=TransactionStatus.INITIATED, nullable=False)
    
# #     # Foreign keys
# #     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
# #     country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
# #     balance_id = Column(Integer, ForeignKey("company_country_balances.id"), nullable=True)
    
# #     # Partner information - using partner_code instead of partner_id
# #     partner_code = Column(String(100), nullable=False)
# #     service_partner_id = Column(String(100), nullable=True)
    
# #     # Gateway and technical fields
# #     gateway_response = Column(Text, nullable=True)
# #     sim_used = Column(String(20), nullable=True)
# #     error_message = Column(Text, nullable=True)
    
# #     # Balance tracking
# #     before_balance = Column(Numeric(14, 2), nullable=True)
# #     after_balance = Column(Numeric(14, 2), nullable=True)
    
# #     # Timestamps
# #     created_at = Column(DateTime(timezone=True), server_default=func.now())
# #     validated_at = Column(DateTime(timezone=True), nullable=True)
# #     updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# #     # Relationships
# #     company = relationship("Company", back_populates="transactions")
# #     country = relationship("Country", back_populates="transactions")
# #     balance = relationship("CompanyCountryBalance")  # Changed from balance_record


# class Transaction(Base):
#     __abstract__ = True
    
#     id = Column(Integer, primary_key=True, index=True)
#     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)  # Add this
#     pending_transaction_id = Column(Integer, ForeignKey("pending_transactions.id"), nullable=True)  # Add this
#     amount = Column(Numeric(10, 2), nullable=False)
#     msisdn = Column(String(20), nullable=False)
#     destination_country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
#     destination_balance_id = Column(Integer, ForeignKey("company_country_balances.id"), nullable=False)
#     partner_code = Column(String(50), nullable=False)
#     transaction_type = Column(String(20), nullable=False)
#     status = Column(String(20), default="initiated")
#     fee_amount = Column(Numeric(10, 2), default=0)
#     net_amount = Column(Numeric(10, 2), nullable=False)
#     gateway_response = Column(Text)
#     gateway_transaction_id = Column(String(100))
#     error_message = Column(Text)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
#     # Relationships
#     company = relationship("Company")
#     destination_country = relationship("Country")
#     destination_balance = relationship("CompanyCountryBalance")
#     pending_transaction = relationship("PendingTransaction")  # Add this

#     # Property to get the right field name based on transaction type
#     @property
#     def recipient(self):
#         return self.msisdn if self.transaction_type in ["deposit", "airtime"] else None
    
#     @property
#     def sender(self):
#         return self.msisdn if self.transaction_type == "withdrawal" else None


# class DepositTransaction(Transaction):
#     __mapper_args__ = {
#         "polymorphic_identity": "deposit"
#     }
    

# class WithdrawalTransaction(Transaction):
#     __mapper_args__ = {
#         "polymorphic_identity": "withdrawal"
#     }
    

# class AirtimePurchase(Transaction):
#     __mapper_args__ = {
#         "polymorphic_identity": "airtime"
#     }
    

# class PendingTransaction(Base):
#     __tablename__ = "pending_transactions"  # Changed to plural

#     id = Column(Integer, primary_key=True, index=True)
#     transaction_type = Column(String(20), nullable=False)  # deposit | withdrawal | airtime
#     msisdn = Column(String(20), nullable=False)
#     amount = Column(Numeric(14, 2), nullable=False)  # Changed to 14,2
#     partner_code = Column(String(100), nullable=False)  # Changed from partner_id
#     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
#     status = Column(SAEnum(PendingStatus), default=PendingStatus.PENDING)  # Added enum
#     created_at = Column(DateTime(timezone=True), server_default=func.now())

#     # Relationships
#     company = relationship("Company")

# class Country(Base):
#     __tablename__ = "countries"  # Changed to plural

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), nullable=False, unique=True)
#     iso_code = Column(String(3), nullable=False, unique=True)
#     phone_code = Column(String(10), nullable=True)
#     currency = Column(String(10), nullable=True)
#     is_active = Column(Boolean, default=True)
    
#     # Relationships
#     procurements = relationship("Procurement", back_populates="country")
#     transactions = relationship("Transaction", back_populates="country")
#     balances = relationship("CompanyCountryBalance", back_populates="country")  # Added


# class Company(Base):
#     __tablename__ = "companies"  # Changed to plural

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(150), nullable=False, unique=True)
#     email = Column(String(150), nullable=False, unique=True)
#     phone = Column(String(50), nullable=True)
#     address = Column(String(255), nullable=True)
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())

#     # Relationships
#     users = relationship("User", back_populates="company")
#     balances = relationship("CompanyCountryBalance", back_populates="company")
#     procurements = relationship("Procurement", back_populates="company")
#     transactions = relationship("Transaction", back_populates="company")


# class User(Base):
#     __tablename__ = "users"
    
#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String(255), unique=True, index=True, nullable=False)
#     password_hash = Column(String(255), nullable=False)
#     name = Column(String(100), nullable=False)
#     role = Column(String(50), nullable=False, default="user")  # admin, maker, checker, viewer
#     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
#     is_active = Column(Boolean, default=True)
#     last_login = Column(DateTime(timezone=True), nullable=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
#     # Relationships
#     otp_codes = relationship("OTPCode", back_populates="user")
#     blacklisted_tokens = relationship("JWTBlacklist", back_populates="user")
#     refresh_tokens = relationship("RefreshToken", back_populates="user")
#     company = relationship("Company", back_populates="users")


# class CompanyCountryBalance(Base):
#     __tablename__ = "company_country_balances"  # Changed to plural

#     id = Column(Integer, primary_key=True, index=True)
#     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)  # Updated FK
#     country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)  # Updated FK

#     # NEW: Country-specific code per company (ex: SN-WAVE-001)
#     partner_code = Column(String(20), nullable=False)
    
#     # NEW: Dual balance system
#     available_balance = Column(Numeric(14, 2), default=0)
#     held_balance = Column(Numeric(14, 2), default=0)

#     company = relationship("Company", back_populates="balances")
#     country = relationship("Country", back_populates="balances")

#     __table_args__ = (
#         UniqueConstraint("company_id", "country_id", name="uq_company_country"),
#     )

#     @property
#     def effective_balance(self):
#         return self.available_balance - self.held_balance


# class FeeConfig(Base):
#     __tablename__ = "fee_configs"  # Changed to plural

#     id = Column(Integer, primary_key=True, index=True)
#     source_country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)  # Updated FK
#     destination_country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)  # Updated FK

#     fee_type = Column(String(20), nullable=False)  # "flat", "percent", "mixed"
#     flat_fee = Column(Numeric(10, 2), default=0)
#     percent_fee = Column(Numeric(5, 2), default=0)  # 0–100%
#     min_fee = Column(Numeric(10, 2), default=0)
#     max_fee = Column(Numeric(10, 2), nullable=True)

#     is_active = Column(Boolean, default=True)

#     source_country = relationship("Country", foreign_keys=[source_country_id])
#     destination_country = relationship("Country", foreign_keys=[destination_country_id])


# class Procurement(Base):
#     __tablename__ = "procurements"

#     id = Column(Integer, primary_key=True, index=True)
#     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)  # Updated FK
#     country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)  # Updated FK

#     bank_name = Column(String(255), nullable=False)
#     slip_number = Column(String(255), nullable=False, unique=True)
#     slip_file_path = Column(String(500), nullable=True)

#     initiation_date = Column(DateTime(timezone=True), server_default=func.now())
#     validation_date = Column(DateTime(timezone=True), nullable=True)

#     amount = Column(Numeric(18, 2), nullable=False)

#     status = Column(
#         SAEnum(ProcurementStatus), 
#         default=ProcurementStatus.PENDING, 
#         nullable=False
#     )

#     # Relationships
#     company = relationship("Company", back_populates="procurements")
#     country = relationship("Country", back_populates="procurements")


# class JWTBlacklist(Base):
#     __tablename__ = "jwt_blacklist"
    
#     id = Column(Integer, primary_key=True, index=True)
#     jti = Column(String(36), unique=True, index=True, nullable=False)  # JWT ID
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     token = Column(String(500), nullable=False)  # The actual token for reference
#     expires_at = Column(DateTime(timezone=True), nullable=False)
#     revoked_at = Column(DateTime(timezone=True), server_default=func.now())
#     reason = Column(String(50))  # logout, password_change, security_breach
    
#     user = relationship("User", back_populates="blacklisted_tokens")
    
#     __table_args__ = (
#         Index('ix_jwt_blacklist_user_id', 'user_id'),
#         Index('ix_jwt_blacklist_expires', 'expires_at'),
#     )

# class OTPCode(Base):
#     __tablename__ = "otp_codes"
    
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     code = Column(String(6), nullable=False)  # 6-digit OTP
#     purpose = Column(String(20), nullable=False)  # login, reset_password, etc.
#     expires_at = Column(DateTime(timezone=True), nullable=False)
#     is_used = Column(Boolean, default=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
    
#     user = relationship("User", back_populates="otp_codes")
    
#     __table_args__ = (
#         Index('ix_otp_codes_user_purpose', 'user_id', 'purpose'),
#         Index('ix_otp_codes_expires', 'expires_at'),
#     )

# class APIKey(Base):
#     __tablename__ = "api_keys"
    
#     id = Column(Integer, primary_key=True, index=True)
#     company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
#     name = Column(String(100), nullable=False)  # Key name/description
#     key = Column(String(64), unique=True, index=True, nullable=False)  # API key
#     secret = Column(String(128), nullable=False)  # API secret (hashed)
#     is_active = Column(Boolean, default=True)
#     permissions = Column(JSON, nullable=True)  # JSON array of permissions
#     expires_at = Column(DateTime(timezone=True), nullable=True)
#     last_used = Column(DateTime(timezone=True), nullable=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
    
#     company = relationship("Company", back_populates="api_keys")
    
#     __table_args__ = (
#         Index('ix_api_keys_company', 'company_id'),
#         Index('ix_api_keys_active', 'is_active'),
#     )

# class RefreshToken(Base):
#     __tablename__ = "refresh_tokens"
    
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     token = Column(String(64), unique=True, index=True, nullable=False)  # Hashed refresh token
#     device_info = Column(JSON)  # Store device fingerprint
#     expires_at = Column(DateTime(timezone=True), nullable=False)
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
    
#     user = relationship("User", back_populates="refresh_tokens")
    
#     __table_args__ = (
#         Index('ix_refresh_tokens_user_active', 'user_id', 'is_active'),
#     )

# src/models/__init__.py
from sqlalchemy import (
    Column, Integer, Text, Numeric, String, DateTime, Boolean, ForeignKey, 
    UniqueConstraint, Enum as SAEnum, JSON, Index, event
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, declared_attr
from src.core.database import Base
from datetime import datetime, timezone
from enum import Enum


# ========== ENUMS ==========
class TransactionStatus(str, Enum):
    INITIATED = "initiated"    # funds held
    SUCCESS = "success"        # debit/credit applied
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
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    AIRTIME = "airtime"


# ========== MIXINS ==========
class CompanyMixin:
    """Mixin for company-related relationships"""
    @declared_attr
    def company_id(cls):
        return Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    @declared_attr
    def company(cls):
        return relationship("Company")


class CountryMixin:
    """Mixin for country-related relationships"""
    @declared_attr
    def country_id(cls):
        return Column(Integer, ForeignKey("countries.id"), nullable=False)
    
    @declared_attr
    def country(cls):
        return relationship("Country")


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
    
    # Relationships
    procurements = relationship("Procurement", back_populates="country")
    fee_configs_source = relationship("FeeConfig", foreign_keys="[FeeConfig.source_country_id]", back_populates="source_country")
    fee_configs_destination = relationship("FeeConfig", foreign_keys="[FeeConfig.destination_country_id]", back_populates="destination_country")
    balances = relationship("CompanyCountryBalance", back_populates="country")
    transactions = relationship("Transaction", back_populates="country")


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
    transactions = relationship("Transaction", back_populates="company")
    api_keys = relationship("APIKey", back_populates="company")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
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


class FeeConfig(Base):
    __tablename__ = "fee_configs"

    id = Column(Integer, primary_key=True, index=True)
    source_country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    destination_country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    
    # Fee calculation
    fee_type = Column(String(20), nullable=False)  # "flat", "percent", "mixed"
    flat_fee = Column(Numeric(10, 2), default=0)
    percent_fee = Column(Numeric(5, 2), default=0)
    min_fee = Column(Numeric(10, 2), default=0)
    max_fee = Column(Numeric(10, 2), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source_country = relationship("Country", foreign_keys=[source_country_id], back_populates="fee_configs_source")
    destination_country = relationship("Country", foreign_keys=[destination_country_id], back_populates="fee_configs_destination")


class Procurement(Base):
    __tablename__ = "procurements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)

    bank_name = Column(String(255), nullable=False)
    slip_number = Column(String(255), nullable=False, unique=True)
    slip_file_path = Column(String(500), nullable=True)

    initiation_date = Column(DateTime(timezone=True), server_default=func.now())
    validation_date = Column(DateTime(timezone=True), nullable=True)

    amount = Column(Numeric(18, 2), nullable=False)
    status = Column(SAEnum(ProcurementStatus), default=ProcurementStatus.PENDING)

    company = relationship("Company", back_populates="procurements")
    country = relationship("Country", back_populates="procurements")

# ========== BASE (ABSTRACT) TRANSACTION ==========

class TransactionMixin:
    """Mixin class with common fields for all transactions"""
    
    # Common fields
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    msisdn = Column(String(20), nullable=False)
    status = Column(String(20), default='initiated')
    
    # Foreign keys
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    balance_id = Column(Integer, ForeignKey("company_country_balances.id"), nullable=True)
    pending_transaction_id = Column(Integer, ForeignKey("pending_transactions.id"), nullable=True)
    
    # Partner info
    partner_code = Column(String(100), nullable=False)
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
    
    # Email confirmation
    email_confirmation_token = Column(String(64), nullable=True, unique=True)
    email_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Technical fields
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    validated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships using @declared_attr for mixins
    @declared_attr
    def company(cls):
        return relationship("Company")
    
    @declared_attr
    def country(cls):
        return relationship("Country")
    
    @declared_attr
    def balance(cls):
        return relationship("CompanyCountryBalance")
    
    @declared_attr
    def pending_transaction(cls):
        return relationship("PendingTransaction")


# ========== SPECIFIC TRANSACTION MODELS ==========
class DepositTransaction(Base, TransactionMixin):
    __tablename__ = "deposit_transactions"
    
    recipient = Column(String(20), nullable=False)


class WithdrawalTransaction(Base, TransactionMixin):
    __tablename__ = "withdrawal_transactions"
    
    sender = Column(String(20), nullable=False)


class AirtimePurchase(Base, TransactionMixin):
    __tablename__ = "airtime_purchases"
    
    recipient = Column(String(20), nullable=False)


# ========== PENDING TRANSACTION ==========
class PendingTransaction(Base):
    __tablename__ = "pending_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String(20), nullable=False)  # deposit, withdrawal, airtime
    msisdn = Column(String(20), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    partner_code = Column(String(100), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    country_iso = Column(String(3), nullable=True)
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    company = relationship("Company")