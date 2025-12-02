# # src/core/security.py (Updated)
# from passlib.context import CryptContext
# from jose import JWTError, jwt
# from datetime import datetime, timezone, timedelta
# import secrets
# import hashlib
# import hmac
# import uuid
# from typing import Optional, Dict, Any
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Configuration
# SECRET_KEY = os.getenv("SECRET_KEY")
# if not SECRET_KEY:
#     raise ValueError("SECRET_KEY environment variable is required")

# REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", SECRET_KEY + "refresh")

# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 minutes
# REFRESH_TOKEN_EXPIRE_DAYS = 30
# OTP_EXPIRE_MINUTES = 5
# API_KEY_LENGTH = 32
# API_SECRET_LENGTH = 64

# pwd_context = CryptContext(
#     schemes=["bcrypt_sha256"], 
#     bcrypt_sha256__default_rounds=12,
#     deprecated="auto"
# )

# class SecurityUtils:
#     # ==================== PASSWORD HANDLING ====================
#     @staticmethod
#     def hash_password(password: str) -> str:
#         """
#         Hash a password securely.
#         Uses bcrypt_sha256 which automatically handles passwords longer than 72 bytes.
#         """
#         if not password:
#             raise ValueError("Password cannot be empty")
        
#         # Simple validation
#         if len(password) < 1:
#             raise ValueError("Password cannot be empty")
        
#         # bcrypt_sha256 will handle long passwords automatically
#         return pwd_context.hash(password)
    
#     @staticmethod
#     def verify_password(plain_password: str, hashed_password: str) -> bool:
#         """
#         Verify a password against its hash.
#         """
#         if not plain_password:
#             return False
        
#         try:
#             return pwd_context.verify(plain_password, hashed_password)
#         except Exception:
#             return False    
        
#     # ==================== JWT TOKEN GENERATION ====================
#     @staticmethod
#     def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, datetime, str]:
#         """Create JWT access token with jti claim"""
#         to_encode = data.copy()
#         jti = str(uuid.uuid4())
        
#         if expires_delta:
#             expire = datetime.now(timezone.utc) + expires_delta
#         else:
#             expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
#         to_encode.update({
#             "exp": expire,
#             "iat": datetime.now(timezone.utc),
#             "jti": jti,
#             "type": "access"
#         })
        
#         encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#         return encoded_jwt, expire, jti
    
#     @staticmethod
#     def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, datetime]:
#         """Create JWT refresh token"""
#         to_encode = data.copy()
        
#         if expires_delta:
#             expire = datetime.now(timezone.utc) + expires_delta
#         else:
#             expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
#         to_encode.update({
#             "exp": expire,
#             "iat": datetime.now(timezone.utc),
#             "type": "refresh"
#         })
        
#         encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
#         return encoded_jwt, expire
    
#     # ==================== TOKEN VERIFICATION ====================
#     @staticmethod
#     def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
#         """Verify JWT access token"""
#         try:
#             payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#             if payload.get("type") != "access":
#                 return None
#             return payload
#         except JWTError:
#             return None
    
#     @staticmethod
#     def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
#         """Verify JWT refresh token"""
#         try:
#             payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
#             if payload.get("type") != "refresh":
#                 return None
#             return payload
#         except JWTError:
#             return None
    
#     # ==================== OTP GENERATION ====================
#     @staticmethod
#     def generate_otp() -> str:
#         return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
#     @staticmethod
#     def get_otp_expiry() -> datetime:
#         return datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    
#     # ==================== API KEY GENERATION ====================
#     @staticmethod
#     def generate_api_key() -> str:
#         return secrets.token_urlsafe(API_KEY_LENGTH)
    
#     @staticmethod
#     def generate_api_secret() -> str:
#         return secrets.token_urlsafe(API_SECRET_LENGTH)
    
#     @staticmethod
#     def hash_api_secret(secret: str) -> str:
#         return pwd_context.hash(secret)
    
#     @staticmethod
#     def verify_api_secret(plain_secret: str, hashed_secret: str) -> bool:
#         return pwd_context.verify(plain_secret, hashed_secret)
    
#     # ==================== REFRESH TOKEN HASHING ====================
#     @staticmethod
#     def hash_refresh_token(token: str) -> str:
#         """Hash refresh token for database storage"""
#         return pwd_context.hash(token)
    
#     @staticmethod
#     def verify_refresh_token_hash(plain_token: str, hashed_token: str) -> bool:
#         """Verify refresh token hash"""
#         return pwd_context.verify(plain_token, hashed_token)
    
#     # ==================== HMAC SIGNATURE ====================
#     @staticmethod
#     def generate_hmac_signature(secret: str, message: str) -> str:
#         """Generate HMAC signature for API calls"""
#         return hmac.new(
#             secret.encode(),
#             message.encode(),
#             hashlib.sha256
#         ).hexdigest()
    
#     @staticmethod
#     def verify_hmac_signature(secret: str, message: str, signature: str) -> bool:
#         """Verify HMAC signature"""
#         expected_signature = SecurityUtils.generate_hmac_signature(secret, message)
#         return hmac.compare_digest(expected_signature, signature)

# src/core/security.py
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
import secrets
import hashlib
import hmac
import uuid
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
import bcrypt  # Import bcrypt directly

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

class SecurityUtils:
    # ==================== PASSWORD HANDLING ====================
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password securely using bcrypt directly.
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Generate salt and hash with bcrypt
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_bytes.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash using bcrypt directly.
        """
        if not plain_password or not hashed_password:
            return False
        
        try:
            # Convert to bytes
            password_bytes = plain_password.encode('utf-8')
            hash_bytes = hashed_password.encode('utf-8')
            
            # Use bcrypt.checkpw directly
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            return False
    
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
    
    # ==================== OTP GENERATION ====================
    @staticmethod
    def generate_otp() -> str:
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    @staticmethod
    def get_otp_expiry() -> datetime:
        return datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    
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