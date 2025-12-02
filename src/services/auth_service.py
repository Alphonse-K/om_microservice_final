# src/services/auth_service.py (Simplified)
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from src.models.transaction import JWTBlacklist, OTPCode, APIKey, RefreshToken, User
from src.core.security import SecurityUtils
from src.schemas.transaction import UserLogin, OTPVerify, APIKeyCreate
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AuthService:
    # ==================== USER AUTHENTICATION ====================
    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
        """
        Authenticate a user by email and password.
        """
        # Find active user by email
        user = db.query(User).filter(
            User.email == login_data.email,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Verify password using SecurityUtils
        if not SecurityUtils.verify_password(login_data.password, user.password_hash):
            return None
        
        return user
    
    # ==================== OTP MANAGEMENT ====================
    @staticmethod
    def generate_otp(db: Session, user: User, purpose: str = "login") -> str:
        """
        Generate and store OTP for user.
        """
        # Invalidate previous OTPs for the same purpose
        db.query(OTPCode).filter(
            OTPCode.user_id == user.id,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False
        ).update({"is_used": True})
        
        # Generate new OTP using SecurityUtils
        otp_code = SecurityUtils.generate_otp()
        expires_at = SecurityUtils.get_otp_expiry()
        
        # Store OTP in database
        otp = OTPCode(
            user_id=user.id,
            code=otp_code,
            purpose=purpose,
            expires_at=expires_at
        )
        
        db.add(otp)
        db.commit()
        
        # TODO: Send OTP via email/SMS
        logger.info(f"OTP for {user.email}: {otp_code}")
        
        return otp_code
    
    @staticmethod
    def verify_otp(db: Session, verify_data: OTPVerify, purpose: str = "login") -> Optional[User]:
        """
        Verify OTP and return user if valid.
        """
        user = db.query(User).filter(
            User.email == verify_data.email,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Find valid OTP
        otp = db.query(OTPCode).filter(
            OTPCode.user_id == user.id,
            OTPCode.code == verify_data.otp_code,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False,
            OTPCode.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not otp:
            return None
        
        # Mark OTP as used
        otp.is_used = True
        db.commit()
        
        return user
    
    # ==================== TOKEN MANAGEMENT ====================
    @staticmethod
    def create_tokens(db: Session, user: User, device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create access and refresh tokens for user.
        """
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "company_id": user.company_id,
            "role": user.role
        }
        
        # Use SecurityUtils to create tokens
        access_token, expires_at, jti = SecurityUtils.create_access_token(token_data)
        refresh_token, refresh_expires_at = SecurityUtils.create_refresh_token(token_data)
        
        # Store hashed refresh token in database
        hashed_refresh_token = SecurityUtils.hash_refresh_token(refresh_token)
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token=hashed_refresh_token,
            device_info=device_info,
            expires_at=refresh_expires_at
        )
        
        db.add(refresh_token_record)
        
        # Update user's last login
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "jti": jti
        }
    
    @staticmethod
    def validate_access_token(db: Session, token: str) -> Optional[User]:
        """
        Validate access token and return user if valid.
        """
        # Verify token using SecurityUtils
        payload = SecurityUtils.verify_access_token(token)
        if not payload:
            return None
        
        # Check if token is blacklisted
        blacklisted = db.query(JWTBlacklist).filter(
            JWTBlacklist.jti == payload.get("jti")
        ).first()
        
        if blacklisted:
            return None
        
        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = db.query(User).filter(
            User.id == int(user_id),
            User.is_active == True
        ).first()
        
        return user
    
    @staticmethod
    def refresh_tokens(db: Session, refresh_token: str, device_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        """
        # Verify refresh token using SecurityUtils
        payload = SecurityUtils.verify_refresh_token(refresh_token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Check if refresh token exists in database
        hashed_token = SecurityUtils.hash_refresh_token(refresh_token)
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token == hashed_token,
            RefreshToken.is_active == True,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not token_record:
            return None
        
        # Get user
        user = db.query(User).filter(
            User.id == int(user_id),
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Invalidate old refresh token
        token_record.is_active = False
        
        # Create new tokens
        return AuthService.create_tokens(db, user, device_info)
    
    # ==================== LOGOUT MANAGEMENT ====================
    @staticmethod
    def logout_user(db: Session, token: str, reason: str = "logout") -> bool:
        """
        Blacklist JWT token on logout.
        """
        payload = SecurityUtils.verify_access_token(token)
        if not payload:
            return False
        
        jti = payload.get("jti")
        user_id = payload.get("sub")
        expires_at = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
        
        # Add to blacklist
        blacklist_entry = JWTBlacklist(
            jti=jti,
            user_id=int(user_id),
            token=token,
            expires_at=expires_at,
            reason=reason
        )
        
        db.add(blacklist_entry)
        
        # Clean up expired blacklist entries
        db.query(JWTBlacklist).filter(
            JWTBlacklist.expires_at < datetime.now(timezone.utc)
        ).delete()
        
        db.commit()
        return True
    
    @staticmethod
    def logout_all_devices(db: Session, user_id: int) -> bool:
        """
        Invalidate all tokens for a user.
        """
        # Invalidate all refresh tokens
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_active == True
        ).update({"is_active": False})
        
        db.commit()
        return True
    
    # ==================== API KEY MANAGEMENT ====================
    @staticmethod
    def create_api_key(db: Session, company_id: int, create_data: APIKeyCreate) -> dict:
        """
        Create API key for a company.
        """
        # Generate keys using SecurityUtils
        api_key = SecurityUtils.generate_api_key()
        api_secret = SecurityUtils.generate_api_secret()
        hashed_secret = SecurityUtils.hash_api_secret(api_secret)
        
        api_key_record = APIKey(
            company_id=company_id,
            name=create_data.name,
            key=api_key,
            secret=hashed_secret,
            permissions=create_data.permissions,
            expires_at=create_data.expires_at
        )
        
        db.add(api_key_record)
        db.commit()
        db.refresh(api_key_record)
        
        # Return the secret only once
        return {
            "id": api_key_record.id,
            "name": api_key_record.name,
            "key": api_key,
            "secret": api_secret,
            "permissions": create_data.permissions,
            "expires_at": create_data.expires_at,
            "created_at": api_key_record.created_at
        }
    
    @staticmethod
    def validate_api_key(db: Session, api_key: str, api_secret: str) -> Optional[APIKey]:
        """
        Validate API key and secret.
        """
        key_record = db.query(APIKey).filter(
            APIKey.key == api_key,
            APIKey.is_active == True
        ).first()
        
        if not key_record:
            return None
        
        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
            return None
        
        # Verify secret using SecurityUtils
        if not SecurityUtils.verify_api_secret(api_secret, key_record.secret):
            return None
        
        # Update last used timestamp
        key_record.last_used = datetime.now(timezone.utc)
        db.commit()
        
        return key_record
    
    @staticmethod
    def get_company_api_keys(db: Session, company_id: int):
        """
        Get all API keys for a company.
        """
        return db.query(APIKey).filter(
            APIKey.company_id == company_id
        ).order_by(APIKey.created_at.desc()).all()
    
    @staticmethod
    def revoke_api_key(db: Session, key_id: int, company_id: int) -> bool:
        """
        Revoke an API key.
        """
        key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.company_id == company_id
        ).first()
        
        if key:
            key.is_active = False
            db.commit()
            return True
        
        return False