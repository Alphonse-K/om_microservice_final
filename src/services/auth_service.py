# src/services/auth_service.py (FINAL CLEAN VERSION)
import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
import os

from src.models.transaction import JWTBlacklist, OTPCode, APIKey, RefreshToken, User, RoleEnum
from src.core.security import SecurityUtils
from src.schemas.transaction import UserLogin, OTPVerify, APIKeyCreate, UserCreate
from src.services.email_service import EmailService

logger = logging.getLogger(__name__)

class AuthService:
    # ==================== USER AUTHENTICATION ====================
    @staticmethod
    def authenticate_user(
        db: Session, 
        login_data: UserLogin, 
        ip_address: str = ""
    ) -> Optional[User]:
        """
        Authenticate user with email and password
        """
        try:
            user = db.query(User).filter(
                User.email == login_data.email,
                User.is_active == True
            ).first()
            
            if not user:
                logger.warning(f"Login attempt failed: User not found for email {login_data.email}")
                return None
            
            if not SecurityUtils.verify_password(login_data.password, user.password_hash):
                logger.warning(f"Login attempt failed: Invalid password for user {user.email}")
                return None
            
            # Update last login time
            user.last_login = datetime.now(timezone.utc)
            db.commit()
            
            # Send login notification email (async to avoid blocking)
            try:
                # Get user agent from somewhere or pass it as parameter
                EmailService.send_login_notification(
                    user.email,
                    user.name,
                    ip_address,
                )
                logger.info(f"Login notification email sent to {user.email}")
            except Exception as email_error:
                logger.error(f"Failed to send login notification email: {str(email_error)}")
                # Don't fail authentication if email fails
            
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None
    
    @staticmethod
    def generate_otp(db: Session, user: User, otp_type: str = "login") -> str:
        """
        Generate and send OTP to user's email
        """
        from src.core.security import SecurityUtils
        
        logger.info(f"=== START generate_otp for user: {user.email}, type: {otp_type} ===")
        
        # Generate OTP code
        otp_code = SecurityUtils.generate_otp()
        logger.info(f"Generated OTP code: {otp_code}")
        
        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        logger.info(f"OTP expires at: {expires_at}")
        
        # Delete any existing OTPs for this user and purpose
        deleted_count = db.query(OTPCode).filter(
            OTPCode.user_id == user.id,
            OTPCode.purpose == otp_type,
            OTPCode.is_used == False
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_count} existing OTPs")
        
        # Create new OTP
        otp_record = OTPCode(
            user_id=user.id,
            code=otp_code,
            purpose=otp_type,
            expires_at=expires_at
        )
        db.add(otp_record)
        db.commit()
        logger.info(f"Created OTP record with ID: {otp_record.id}")
        
        # Send OTP via email
        try:
            logger.info(f"Attempting to send OTP email to: {user.email}")
            logger.info(f"Calling send_otp_email with: email={user.email}, name={user.name}, otp={otp_code}, purpose={otp_type}")
            
            # Call email service
            email_sent = EmailService.send_otp_email(
                user.email,
                user.name,
                otp_code,
                otp_type  # This should be passed
            )
            
            if email_sent:
                logger.info(f"✓ OTP email sent successfully to {user.email}")
            else:
                logger.error(f"✗ EmailService.send_otp_email returned False for {user.email}")
                
        except Exception as email_error:
            logger.error(f"✗ Exception in send_otp_email: {str(email_error)}", exc_info=True)
        
        logger.info(f"=== END generate_otp for user: {user.email} ===")
        return otp_code

    @staticmethod
    def verify_otp(db: Session, verify_data: OTPVerify, otp_type: str = "login") -> Optional[User]:
        """
        Verify OTP code for a user
        """
        try:
            # Find the OTP record
            otp_record = db.query(OTPCode).join(User).filter(
                User.email == verify_data.email,
                OTPCode.code == verify_data.otp_code,
                OTPCode.purpose == otp_type,  # Changed from otp_type to purpose
                OTPCode.is_used == False,
                OTPCode.expires_at > datetime.now(timezone.utc)
            ).first()
            
            if not otp_record:
                logger.warning(f"Invalid OTP attempt for email: {verify_data.email}")
                return None
            
            # Mark OTP as used
            otp_record.is_used = True
            otp_record.used_at = datetime.now(timezone.utc)
            
            # Get user
            user = otp_record.user
            
            # Update user's last login
            user.last_login = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"OTP verified successfully for user: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"OTP verification error: {str(e)}")
            db.rollback()
            return None
    
    # ==================== USER MANAGEMENT ====================
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """
        Create new user with validation and welcome email.
        """
        # Check if email exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")
        
        # Validate password strength
        is_valid, message = SecurityUtils.validate_password_strength(user_data.password)
        if not is_valid:
            raise ValueError(message)
        
        # Create user
        user = User(
            name=user_data.name,
            email=user_data.email,
            password_hash=SecurityUtils.hash_password(user_data.password),
            role=user_data.role,
            company_id=user_data.company_id,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Send welcome email
        try:
            EmailService.send_welcome_email(user.email, user.name)
        except Exception as e:
            logger.warning(f"Failed to send welcome email to {user.email}: {str(e)}")
        
        logger.info(f"User created: {user.email} (ID: {user.id})")
        return user
    
    @staticmethod
    def list_users(db: Session) -> List[User]:
        """Return all users"""
        return db.query(User).all()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def update_user(db: Session, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
        """Update user information safely with Enum support."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            allowed_fields = ["name", "email" "role", "is_active"]

            for field in allowed_fields:
                if field in update_data:
                    if field == "role":
                        # Convert string to RoleEnum
                        try:
                            value = RoleEnum(update_data["role"].upper())  # <-- important
                        except ValueError:
                            raise ValueError(f"Invalid role: {update_data['role']}")
                        setattr(user, field, value)
                    else:
                        setattr(user, field, update_data[field])

            db.commit()
            db.refresh(user)
            return user

        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        """Deactivate user (soft delete)"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        db.commit()
        return True
    
    # ==================== PASSWORD MANAGEMENT ====================
    @staticmethod
    def change_password(
        db: Session, 
        user_id: int, 
        old_password: str, 
        new_password: str, 
        confirm_password: str
    ) -> bool:
        """
        Change user password with validation.
        Requires old password, new password, and confirmation.
        """
        # Get user
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            return False
        
        # Validate password change
        is_valid, message = SecurityUtils.validate_password_change(
            old_password=old_password,
            new_password=new_password,
            confirm_password=confirm_password,
            current_hashed_password=user.password_hash
        )
        
        if not is_valid:
            raise ValueError(message)
        
        # Update password
        user.password_hash = SecurityUtils.hash_password(new_password)
        db.commit()
        
        # Send password change notification
        try:
            EmailService.send_password_change_notification(user.email, user.name)
        except Exception as e:
            logger.warning(f"Failed to send password change email: {str(e)}")
        
        return True
    
    # ==================== TOKEN MANAGEMENT ====================
    @staticmethod
    def create_tokens(db: Session, user: User, device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create access and refresh tokens for user.
        Updates last login time.
        """
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "company_id": user.company_id,
            "role": user.role
        }
        
        # Create tokens
        access_token, expires_at, jti = SecurityUtils.create_access_token(token_data)
        refresh_token, refresh_expires_at = SecurityUtils.create_refresh_token(token_data)
        
        # Store refresh token
        hashed_refresh_token = SecurityUtils.hash_refresh_token(refresh_token)
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token=hashed_refresh_token,
            device_info=device_info,
            expires_at=refresh_expires_at
        )
        
        db.add(refresh_token_record)
        
        # Update last login
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
        Checks token blacklist.
        """
        # Verify token
        payload = SecurityUtils.verify_access_token(token)
        if not payload:
            return None
        
        # Check blacklist
        blacklisted = db.query(JWTBlacklist).filter(
            JWTBlacklist.jti == payload.get("jti")
        ).first()
        
        if blacklisted:
            return None
        
        # Get user
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        return db.query(User).filter(
            User.id == int(user_id),
            User.is_active == True
        ).first()
    
    @staticmethod
    def refresh_tokens(db: Session, refresh_token: str, device_info: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token.
        Invalidates old refresh token.
        """
        # Verify refresh token
        payload = SecurityUtils.verify_refresh_token(refresh_token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Find refresh token in database
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
    
    @staticmethod
    def logout_user(db: Session, token: str, reason: str = "logout") -> bool:
        """
        Blacklist JWT token on logout.
        """
        payload = SecurityUtils.verify_access_token(token)
        if not payload:
            return False
        
        # Add to blacklist
        jti = payload.get("jti")
        user_id = payload.get("sub")
        expires_at = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
        
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
        Invalidate all refresh tokens for a user.
        """
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
        Returns key and secret (secret only shown once).
        """
        # Generate keys
        api_key = SecurityUtils.generate_api_key()
        api_secret = SecurityUtils.generate_api_secret()
        hashed_secret = SecurityUtils.hash_api_secret(api_secret)
        
        # Store API key
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
        
        # Return with secret (only shown once)
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
        Updates last used timestamp.
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
        
        # Verify secret
        if not SecurityUtils.verify_api_secret(api_secret, key_record.secret):
            return None
        
        # Update last used
        key_record.last_used = datetime.now(timezone.utc)
        db.commit()
        
        return key_record
    
    @staticmethod
    def get_company_api_keys(db: Session, company_id: int):
        """Get all API keys for a company"""
        return db.query(APIKey).filter(
            APIKey.company_id == company_id
        ).order_by(APIKey.created_at.desc()).all()
    
    @staticmethod
    def revoke_api_key(db: Session, key_id: int, company_id: int) -> bool:
        """Revoke an API key"""
        key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.company_id == company_id
        ).first()
        
        if key:
            key.is_active = False
            db.commit()
            return True
        
        return False