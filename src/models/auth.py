# src/models/auth.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime, timezone, timedelta
import secrets
from src.core.database import Base

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="sessions")

class OTPCode(Base):
    __tablename__ = "otp_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(6), nullable=False)  # 6-digit OTP
    purpose = Column(String(20), nullable=False)  # login, reset_password, etc.
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="otp_codes")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100), nullable=False)  # Key name/description
    key = Column(String(64), unique=True, index=True, nullable=False)  # API key
    secret = Column(String(128), nullable=False)  # API secret (hashed)
    is_active = Column(Boolean, default=True)
    permissions = Column(String(500), nullable=True)  # JSON string of permissions
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company", back_populates="api_keys")

# Update User model to include relationships
class User(Base):
    __tablename__ = "users"
    
    # ... existing fields ...
    sessions = relationship("UserSession", back_populates="user")
    otp_codes = relationship("OTPCode", back_populates="user")

# Update Company model
class Company(Base):
    __tablename__ = "companies"
    
    # ... existing fields ...
    api_keys = relationship("APIKey", back_populates="company")