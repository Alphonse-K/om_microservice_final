# src/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from src.core.auth_dependencies import get_db, get_current_user, get_optional_user, require_role
from src.core.security import SecurityUtils
from src.services.auth_service import AuthService
from src.schemas.transaction import *
from src.models.transaction import User
import logging

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post("/login", response_model=OTPResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Step 1: Login with email and password to receive OTP
    """
    user = AuthService.authenticate_user(db, login_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    otp_code = AuthService.generate_otp(db, user, "login")
    
    return {
        "message": "OTP sent successfully",
        "expires_in": 600  # 10 minutes
    }

@auth_router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(
    verify_data: OTPVerify, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 2: Verify OTP to receive JWT tokens
    """
    user = AuthService.verify_otp(db, verify_data, "login")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )
    
    # Extract device info
    device_info = {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None
    }
    
    tokens = AuthService.create_tokens(db, user, device_info)
    
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
        "expires_at": tokens["expires_at"],
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "company_id": user.company_id
        }
    }

@auth_router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    device_info = {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None
    }
    
    tokens = AuthService.refresh_tokens(db, refresh_data.refresh_token, device_info)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user info from the new token
    payload = SecurityUtils.verify_access_token(tokens["access_token"])
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
        "expires_at": tokens["expires_at"],
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "company_id": user.company_id
        }
    }

@auth_router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user by blacklisting the current token
    """
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization header"
        )
    
    token = auth_header.replace("Bearer ", "")
    AuthService.logout_user(db, token)
    
    return {"message": "Logged out successfully"}

@auth_router.post("/logout-all", response_model=LogoutResponse)
def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout from all devices by invalidating all refresh tokens
    """
    AuthService.logout_all_devices(db, current_user.id)
    
    return {"message": "Logged out from all devices successfully"}

# API Key Management Routes
@auth_router.post("/api-keys", response_model=APIKeyResponse)
def create_api_key(
    create_data: APIKeyCreate,
    current_user: User = Depends(require_role(["admin", "maker"])),
    db: Session = Depends(get_db)
):
    """
    Create new API key for machine-to-machine communication
    """
    result = AuthService.create_api_key(db, current_user.company_id, create_data)
    return result

@auth_router.get("/api-keys", response_model=list[APIKeyListResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user's company
    """
    keys = AuthService.get_company_api_keys(db, current_user.company_id)
    return keys

@auth_router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(require_role(["admin", "maker"])),
    db: Session = Depends(get_db)
):
    """
    Revoke (disable) an API key
    """
    success = AuthService.revoke_api_key(db, key_id, current_user.company_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key revoked successfully"}

# Utility endpoints
@auth_router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return current_user