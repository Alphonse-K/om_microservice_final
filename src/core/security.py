# src/core/security.py (FINAL COMPLETE VERSION)
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
import secrets
import hashlib
import hmac
import uuid
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", SECRET_KEY + "refresh")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
OTP_EXPIRE_MINUTES = 5
API_KEY_LENGTH = 32
API_SECRET_LENGTH = 64

class SecurityUtils:
    # ==================== PASSWORD HANDLING ====================
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Validate password length
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_bytes.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password using bcrypt"""
        if not plain_password or not hashed_password:
            return False
        
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if not password:
            return False, "Password cannot be empty"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        if len(password) > 128:
            return False, "Password cannot exceed 128 characters"
        
        # At least one number
        if not any(char.isdigit() for char in password):
            return False, "Password must contain at least one number"
        
        # At least one uppercase
        if not any(char.isupper() for char in password):
            return False, "Password must contain at least one uppercase letter"
        
        # At least one lowercase
        if not any(char.islower() for char in password):
            return False, "Password must contain at least one lowercase letter"
        
        return True, "Password is strong"
    
    @staticmethod
    def validate_password_change(
        old_password: str, 
        new_password: str, 
        confirm_password: str,
        current_hashed_password: str
    ) -> tuple[bool, str]:
        """Validate password change request"""
        # Check old password
        if not SecurityUtils.verify_password(old_password, current_hashed_password):
            return False, "Old password is incorrect"
        
        # Check if new passwords match
        if new_password != confirm_password:
            return False, "New passwords do not match"
        
        # Check if new password is different from old
        if old_password == new_password:
            return False, "New password must be different from old password"
        
        # Validate new password strength
        is_valid, message = SecurityUtils.validate_password_strength(new_password)
        if not is_valid:
            return False, message
        
        return True, "Password change is valid"
    
    # ==================== OTP HANDLING ====================
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    @staticmethod
    def get_otp_expiry(minutes: int = 5) -> datetime:
        """Get OTP expiry datetime (with parameter)"""
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)
    
    # Add this method for backward compatibility (no parameters)
    @staticmethod
    def get_otp_expiry_default() -> datetime:
        """Get OTP expiry datetime (default 5 minutes) - for backward compatibility"""
        return datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    
    @staticmethod
    def is_otp_expired(expires_at: datetime) -> bool:
        """Check if OTP is expired"""
        return datetime.now(timezone.utc) > expires_at
    
    # ==================== PASSWORD RESET TOKEN ====================
    @staticmethod
    def generate_password_reset_token() -> str:
        """Generate password reset token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def get_password_reset_expiry(minutes: int = 15) -> datetime:
        """Get password reset expiry"""
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)
    
    # ==================== JWT TOKEN GENERATION ====================
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, datetime, str]:
        """Create JWT access token with jti claim"""
        to_encode = data.copy()
        jti = str(uuid.uuid4())
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": jti,
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt, expire, jti
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
        """Create JWT refresh token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt, expire
    
    # ==================== TOKEN VERIFICATION ====================
    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT access token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "access":
                return None
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT refresh token"""
        try:
            payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh":
                return None
            return payload
        except JWTError:
            return None
    
    # ==================== API KEY GENERATION ====================
    @staticmethod
    def generate_api_key() -> str:
        return secrets.token_urlsafe(API_KEY_LENGTH)
    
    @staticmethod
    def generate_api_secret() -> str:
        return secrets.token_urlsafe(API_SECRET_LENGTH)
    
    @staticmethod
    def hash_api_secret(secret: str) -> str:
        return SecurityUtils.hash_password(secret)
    
    @staticmethod
    def verify_api_secret(plain_secret: str, hashed_secret: str) -> bool:
        return SecurityUtils.verify_password(plain_secret, hashed_secret)
    
    # ==================== REFRESH TOKEN HASHING ====================
    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Hash refresh token for database storage"""
        return SecurityUtils.hash_password(token)
    
    @staticmethod
    def verify_refresh_token_hash(plain_token: str, hashed_token: str) -> bool:
        """Verify refresh token hash"""
        return SecurityUtils.verify_password(plain_token, hashed_token)
    
    # ==================== HMAC SIGNATURE ====================
    @staticmethod
    def generate_hmac_signature(secret: str, message: str) -> str:
        """Generate HMAC signature for API calls"""
        return hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_hmac_signature(secret: str, message: str, signature: str) -> bool:
        """Verify HMAC signature"""
        expected_signature = SecurityUtils.generate_hmac_signature(secret, message)
        return hmac.compare_digest(expected_signature, signature)

