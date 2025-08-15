from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security.config import settings
from app.core.database.crud.user import *
from app.schemas.token import Token, TokenRefresh, TokenWithUTC
from app.schemas.user import UserCreate, UserLogin, UserResponse, OTPVerification
from app.core.security.security import create_access_token, verify_token, get_utc_now, format_utc_time
from app.services.auth.otp_service import generate_and_send_otp, verify_otp_code

router = APIRouter()

@router.post("/register", summary="Register User", description="Register a new user and send email verification code")
def register_user(user_in: UserCreate):
    if get_user_by_email(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    user = create_user(user_in, is_verified=False)
    
    otp_sent = generate_and_send_otp(user['email'], "registration")
    if not otp_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка отправки кода подтверждения"
        )
    
    return {
        "message": "Пользователь зарегистрирован. Проверьте email для подтверждения",
        "email": user['email'],
        "requires_verification": True,
        "registered_at": format_utc_time(get_utc_now())
    }

@router.post("/verify-registration", response_model=TokenWithUTC, summary="Verify Registration", description="Verify user registration with OTP code")
def verify_registration(otp_data: OTPVerification):
    user = get_user_by_email(otp_data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    
    if user.get('is_verified', False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь уже подтвержден")
    
    is_valid = verify_otp_code(otp_data.email, otp_data.otp_code, "registration")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный или истекший код подтверждения")
    
    updated_user = verify_user_email(user['id'])
    access_token, refresh_token = create_tokens_for_user(updated_user['id'])
    
    user_with_tokens = get_user(updated_user['id'])
    
    return TokenWithUTC(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=user_with_tokens.get('access_token_expires_at', ''),
        refresh_token_expires_at=user_with_tokens.get('refresh_token_expires_at', ''),
        token_type="bearer",
        issued_at=format_utc_time(get_utc_now())
    )

@router.post("/login", summary="Login User", description="Initiate user login and send OTP code")
def login_for_access_token(user_in: UserLogin):
    user = authenticate_user(user_in.email, user_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    if not user.get('is_verified', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email не подтвержден")
    
    otp_sent = generate_and_send_otp(user['email'], "login")
    if not otp_sent:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка отправки кода подтверждения")
    
    return {
        "message": "Код подтверждения отправлен на email", 
        "email": user['email'],
        "login_initiated_at": format_utc_time(get_utc_now())
    }

@router.post("/verify-login", response_model=TokenWithUTC, summary="Verify Login", description="Verify login with OTP code and get access tokens")
def verify_login_otp(otp_data: OTPVerification):
    user = get_user_by_email(otp_data.email)
    if not user or not user.get('is_verified', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь не найден или не подтвержден")
    
    is_valid = verify_otp_code(otp_data.email, otp_data.otp_code, "login")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный или истекший код подтверждения")
    
    access_token, refresh_token = create_tokens_for_user(user['id'])
    
    user_with_tokens = get_user(user['id'])
    
    return TokenWithUTC(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=user_with_tokens.get('access_token_expires_at', ''),
        refresh_token_expires_at=user_with_tokens.get('refresh_token_expires_at', ''),
        token_type="bearer",
        issued_at=format_utc_time(get_utc_now())
    )

@router.post("/refresh", response_model=TokenWithUTC, summary="Refresh Token", description="Refresh access token using refresh token")
def refresh_token(token_data: TokenRefresh):
    user_id = verify_token(token_data.refresh_token, "refresh")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh token")
    
    user = get_user(user_id)
    if not user or not user.get('is_active', True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден или неактивен")
    
    if user.get('refresh_token') != token_data.refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh token")
    
    try:
        refresh_expires_str = user.get('refresh_token_expires_at', '')
        if refresh_expires_str:
            if refresh_expires_str.endswith('Z'):
                refresh_expires_str = refresh_expires_str[:-1] + '+00:00'
            
            refresh_expires = datetime.fromisoformat(refresh_expires_str)
            if refresh_expires.tzinfo is None:
                refresh_expires = refresh_expires.replace(tzinfo=timezone.utc)
                
            if get_utc_now() > refresh_expires:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token истек")
    except Exception as e:
        print(f"Error parsing refresh token expiry: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh token")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(subject=user_id, expires_delta=access_token_expires)
    
    access_expires = get_utc_now() + access_token_expires
    update_user(user_id, 
                access_token=new_access_token, 
                access_token_expires_at=format_utc_time(access_expires))
    
    return TokenWithUTC(
        access_token=new_access_token,
        refresh_token=token_data.refresh_token,
        access_token_expires_at=format_utc_time(access_expires),
        refresh_token_expires_at=user.get('refresh_token_expires_at', ''),
        token_type="bearer",
        issued_at=format_utc_time(get_utc_now())
    )