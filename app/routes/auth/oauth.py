# app/routes/auth/oauth.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import RedirectResponse

from app.core.security.config import settings
from app.schemas.token import TokenWithUTC
from app.schemas.user import GoogleAuthRequest
from app.services.auth.auth_service import authenticate_google_user, authenticate_google_user_with_credential
from app.core.security.security import format_utc_time, get_utc_now

router = APIRouter()

@router.get("/google/login")
def login_google():
    """
    Генерирует URL для авторизации через Google
    Фронтенд должен перенаправить пользователя на этот URL
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Google OAuth не настроен"
        )
    
    # Создаем URL для авторизации Google
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&access_type=offline"
        "&prompt=consent"
    )
    
    return {"auth_url": google_auth_url}

@router.get("/google/callback")
async def google_callback(request: Request):
    """
    Callback URL для Google OAuth
    Google перенаправляет сюда после авторизации с кодом
    
    ВАЖНО: Этот эндпоинт используется только если redirect_uri 
    указывает напрямую на ваш API
    """
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Ошибка Google OAuth: {error}"
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Отсутствует код авторизации от Google"
        )
    
    auth_result = await authenticate_google_user(code)
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Ошибка аутентификации через Google"
        )
    
    # Возвращаем токены в формате TokenWithUTC
    user_with_tokens = auth_result["user"]
    
    return TokenWithUTC(
        access_token=auth_result["access_token"],
        refresh_token=auth_result["refresh_token"],
        access_token_expires_at=user_with_tokens.get('access_token_expires_at', ''),
        refresh_token_expires_at=user_with_tokens.get('refresh_token_expires_at', ''),
        token_type="bearer",
        issued_at=format_utc_time(get_utc_now())
    )

@router.post("/google/auth", response_model=TokenWithUTC)
async def auth_google(google_auth: GoogleAuthRequest):
    """
    Основной эндпоинт для фронтенда
    Принимает код от Google и возвращает JWT токены
    
    Этот эндпоинт должен использовать ваш фронтенд!
    """
    if not google_auth.credential and not google_auth.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется код авторизации (code) или credential (ID token)"
        )
    
    auth_result = None
    
    try:
        # Способ 1: Обработка ID token (рекомендуется для SPA)
        if google_auth.credential:
            auth_result = await authenticate_google_user_with_credential(google_auth.credential)
        
        # Способ 2: Обработка authorization code (для серверных приложений)
        elif google_auth.code:
            auth_result = await authenticate_google_user(google_auth.code)
        
        if not auth_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Ошибка аутентификации через Google"
            )
        
        # Возвращаем токены в правильном формате
        user_with_tokens = auth_result["user"]
        
        return TokenWithUTC(
            access_token=auth_result["access_token"],
            refresh_token=auth_result["refresh_token"],
            access_token_expires_at=user_with_tokens.get('access_token_expires_at', ''),
            refresh_token_expires_at=user_with_tokens.get('refresh_token_expires_at', ''),
            token_type="bearer",
            issued_at=format_utc_time(get_utc_now())
        )
        
    except Exception as e:
        print(f"[ERROR][GoogleAuth] - Подробности ошибки: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка при обработке Google аутентификации"
        )

@router.get("/google/status")
def google_oauth_status():
    """
    Проверка конфигурации Google OAuth
    """
    is_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    
    return {
        "enabled": is_configured,
        "client_id_configured": bool(settings.GOOGLE_CLIENT_ID),
        "client_secret_configured": bool(settings.GOOGLE_CLIENT_SECRET),
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "endpoints": {
            "login": "/auth/oauth/google/login",
            "callback": "/auth/oauth/google/callback", 
            "api_auth": "/auth/oauth/google/auth"  # <- Основной эндпоинт для фронтенда
        }
    }