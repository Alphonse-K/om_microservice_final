# src/core/security.py
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
import secrets
import hashlib
import hmac
import uuid
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", SECRET_KEY + "refresh")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 30
OTP_EXPIRE_MINUTES = 5
API_KEY_LENGTH = 32
API_SECRET_LENGTH = 64

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityUtils:
    # Password hashing
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    # JWT Token Generation
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
    
    # OTP Generation
    @staticmethod
    def generate_otp() -> str:
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    @staticmethod
    def get_otp_expiry() -> datetime:
        return datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    
    # API Key Generation
    @staticmethod
    def generate_api_key() -> str:
        return secrets.token_urlsafe(API_KEY_LENGTH)
    
    @staticmethod
    def generate_api_secret() -> str:
        return secrets.token_urlsafe(API_SECRET_LENGTH)
    
    @staticmethod
    def hash_api_secret(secret: str) -> str:
        return pwd_context.hash(secret)
    
    @staticmethod
    def verify_api_secret(plain_secret: str, hashed_secret: str) -> bool:
        return pwd_context.verify(plain_secret, hashed_secret)
    
    # Refresh Token Hashing
    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return pwd_context.hash(token)
    
    @staticmethod
    def verify_refresh_token_hash(plain_token: str, hashed_token: str) -> bool:
        return pwd_context.verify(plain_token, hashed_token)
    
    # HMAC Signature for API calls
    @staticmethod
    def generate_hmac_signature(secret: str, message: str) -> str:
        return hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_hmac_signature(secret: str, message: str, signature: str) -> bool:
        expected_signature = SecurityUtils.generate_hmac_signature(secret, message)
        return hmac.compare_digest(expected_signature, signature)