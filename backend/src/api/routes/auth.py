"""Authentication router with rate limiting, audit hooks, and JWT handling."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_async_session
from ...services.auth import get_auth_service
from ...services.audit import get_audit_service, AuditAction, AuditResource
from ...models.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    LogoutResponse,
    UserProfile
)
from ...config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()
settings = get_settings()


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],  # 5 attempts per minute
    summary="User login",
    description="Authenticate user with email and password"
)
async def login(
    request: LoginRequest,
    http_request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session)
):
    """Authenticate user and return tokens."""
    auth_service = get_auth_service(settings)
    audit_service = get_audit_service(settings)
    
    client_ip = http_request.client.host
    user_agent = http_request.headers.get("user-agent", "")
    
    try:
        # Attempt authentication
        auth_result = await auth_service.authenticate_user(
            session=session,
            email=request.email,
            password=request.password
        )
        
        if not auth_result.success:
            # Log failed login attempt
            await audit_service.log_authentication_event(
                session=session,
                action="login_failed",
                user_id=None,
                success=False,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"email": request.email, "reason": auth_result.error}
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
        # Generate tokens
        tokens = await auth_service.create_tokens(
            session=session,
            user_id=auth_result.user.id,
            additional_claims={"email": auth_result.user.email}
        )
        
        # Log successful login
        await audit_service.log_authentication_event(
            session=session,
            action="login_success",
            user_id=auth_result.user.id,
            success=True,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"email": request.email}
        )
        
        # Set refresh token as HTTP-only cookie if requested
        if request.remember_me:
            response.set_cookie(
                key="refresh_token",
                value=tokens.refresh_token,
                max_age=60 * 60 * 24 * 30,  # 30 days
                httponly=True,
                secure=settings.ENVIRONMENT == "production",
                samesite="strict"
            )
            
        return LoginResponse(
            tokens=tokens,
            user=UserProfile(
                id=auth_result.user.id,
                email=auth_result.user.email,
                full_name=auth_result.user.full_name,
                role=auth_result.user.role,
                is_active=auth_result.user.is_active,
                created_at=auth_result.user.created_at,
                last_login=datetime.utcnow()
            ),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        
        # Log system error
        await audit_service.log_authentication_event(
            session=session,
            action="login_error",
            user_id=None,
            success=False,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"email": request.email, "error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system error"
        )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],  # 10 refreshes per minute
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def refresh_token(
    request: RefreshRequest,
    http_request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """Refresh access token using refresh token."""
    auth_service = get_auth_service(settings)
    audit_service = get_audit_service(settings)
    
    client_ip = http_request.client.host
    user_agent = http_request.headers.get("user-agent", "")
    
    try:
        # Use refresh token from request or Authorization header
        refresh_token = request.refresh_token or credentials.credentials
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required"
            )
            
        # Validate and refresh tokens
        token_result = await auth_service.refresh_tokens(
            session=session,
            refresh_token=refresh_token
        )
        
        if not token_result.success:
            # Log failed refresh attempt
            await audit_service.log_authentication_event(
                session=session,
                action="token_refresh_failed",
                user_id=None,
                success=False,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"reason": token_result.error}
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
        # Log successful refresh
        await audit_service.log_authentication_event(
            session=session,
            action="token_refresh_success",
            user_id=token_result.user_id,
            success=True,
            ip_address=client_ip,
            user_agent=user_agent,
            details={}
        )
        
        return RefreshResponse(
            tokens=token_result.tokens,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh system error"
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=30))],  # 5 logouts per 30 seconds
    summary="User logout",
    description="Logout user and invalidate tokens"
)
async def logout(
    http_request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """Logout user and invalidate refresh token."""
    auth_service = get_auth_service(settings)
    audit_service = get_audit_service(settings)
    
    client_ip = http_request.client.host
    user_agent = http_request.headers.get("user-agent", "")
    
    try:
        # Get current user from token
        current_user = await auth_service.get_current_user(
            session=session,
            token=credentials.credentials
        )
        
        if current_user:
            # Invalidate refresh tokens
            await auth_service.invalidate_user_tokens(
                session=session,
                user_id=current_user.id
            )
            
            # Log successful logout
            await audit_service.log_authentication_event(
                session=session,
                action="logout_success",
                user_id=current_user.id,
                success=True,
                ip_address=client_ip,
                user_agent=user_agent,
                details={"email": current_user.email}
            )
            
        # Clear refresh token cookie
        response.delete_cookie(
            key="refresh_token",
            secure=settings.ENVIRONMENT == "production",
            samesite="strict"
        )
        
        return LogoutResponse(
            success=True,
            message="Logged out successfully"
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return LogoutResponse(
            success=True,  # Always return success for logout
            message="Logout completed"
        )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
    description="Get current authenticated user information"
)
async def get_current_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """Get current user profile."""
    auth_service = get_auth_service(settings)
    
    try:
        current_user = await auth_service.get_current_user(
            session=session,
            token=credentials.credentials
        )
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
            
        return UserProfile(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            last_login=current_user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.post(
    "/verify-token",
    summary="Verify token validity",
    description="Verify if the provided token is valid and not expired"
)
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """Verify token validity."""
    auth_service = get_auth_service(settings)
    
    try:
        is_valid = await auth_service.verify_token(
            session=session,
            token=credentials.credentials
        )
        
        return {
            "valid": is_valid,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return {
            "valid": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Token verification failed"
        }


# Dependency for protecting routes
async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """Dependency to get current active user from token."""
    auth_service = get_auth_service(settings)
    
    try:
        current_user = await auth_service.get_current_user(
            session=session,
            token=credentials.credentials
        )
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
            
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )