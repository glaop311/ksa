from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone

from app.core.database.connector import get_user_repository
from app.core.security.security import get_password_hash, verify_password, create_access_token, create_refresh_token, get_utc_now, format_utc_time
from app.core.security.config import settings
from app.schemas.user import UserCreate

def get_repository():
    repo = get_user_repository()
    if not repo:
        raise RuntimeError("Репозиторий пользователей недоступен")
    return repo

def create_tokens_for_user(user_id: str) -> Tuple[str, str]:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user_id, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(subject=user_id)
    
    repo = get_repository()
    
    access_expires = get_utc_now() + access_token_expires
    refresh_expires = get_utc_now() + timedelta(days=30)
    
    repo.update_tokens(user_id, access_token, refresh_token, access_expires, refresh_expires)
    
    return access_token, refresh_token

def refresh_access_token(refresh_token: str) -> Optional[Tuple[str, str]]:
    from app.core.security.security import verify_token
    
    user_id = verify_token(refresh_token, "refresh")
    if not user_id:
        return None
    
    repo = get_repository()
    user = repo.get_user_by_refresh_token(refresh_token)
    
    if not user or user['id'] != user_id:
        return None
    
    if not user.get('is_active', True):
        return None
    
    try:
        refresh_expires_str = user.get('refresh_token_expires_at', '')
        if refresh_expires_str:
            if refresh_expires_str.endswith('Z'):
                refresh_expires_str = refresh_expires_str[:-1] + '+00:00'
            
            refresh_expires = datetime.fromisoformat(refresh_expires_str)
            if refresh_expires.tzinfo is None:
                refresh_expires = refresh_expires.replace(tzinfo=timezone.utc)
                
            if get_utc_now() > refresh_expires:
                print(f"Refresh token expired: {get_utc_now()} > {refresh_expires}")
                return None
    except Exception as e:
        print(f"Error parsing refresh token expiry: {e}")
        return None
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(subject=user_id, expires_delta=access_token_expires)
    
    access_expires = get_utc_now() + access_token_expires
    repo.update_user(user_id, {
        'access_token': new_access_token,
        'access_token_expires_at': format_utc_time(access_expires)
    })
    
    return new_access_token, refresh_token

def add_token_to_favorites(user_id: str, token_id: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    user = repo.get_user_by_id(user_id)
    
    if not user:
        return None
    
    current_favorites = user.get('favorite_tokens', [])
    
    if token_id not in current_favorites:
        current_favorites.append(token_id)
        
        updated_user = repo.update_user(user_id, {'favorite_tokens': current_favorites})
        print(f"[INFO][Favorites] - Токен {token_id} добавлен в избранное пользователя {user_id}")
        return updated_user
    
    return user

def remove_token_from_favorites(user_id: str, token_id: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    user = repo.get_user_by_id(user_id)
    
    if not user:
        return None
    
    current_favorites = user.get('favorite_tokens', [])
    
    if token_id in current_favorites:
        current_favorites.remove(token_id)
        
        updated_user = repo.update_user(user_id, {'favorite_tokens': current_favorites})
        print(f"[INFO][Favorites] - Токен {token_id} удален из избранного пользователя {user_id}")
        return updated_user
    
    return user

def get_user_favorite_tokens(user_id: str) -> List[str]:
    repo = get_repository()
    user = repo.get_user_by_id(user_id)
    
    if not user:
        return []
    
    return user.get('favorite_tokens', [])

def clear_user_favorites(user_id: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    updated_user = repo.update_user(user_id, {'favorite_tokens': []})
    
    if updated_user:
        print(f"[INFO][Favorites] - Избранное очищено для пользователя {user_id}")
    
    return updated_user

def is_token_favorite(user_id: str, token_id: str) -> bool:
    favorites = get_user_favorite_tokens(user_id)
    return token_id in favorites

def create_user(user_in: UserCreate, is_verified: bool = False, auth_provider: str = "local") -> Dict[str, Any]:
    repo = get_repository()
    
    # Генерируем имя из email если не указано
    email_name = user_in.email.split('@')[0]
    display_name = f"{getattr(user_in, 'first_name', '') or ''} {getattr(user_in, 'last_name', '') or ''}".strip() or email_name
    
    user_data = {
        "email": user_in.email,
        "name": display_name,
        "hashed_password": get_password_hash(user_in.password) if hasattr(user_in, 'password') and user_in.password else "",
        "first_name": getattr(user_in, 'first_name', '') or '',
        "last_name": getattr(user_in, 'last_name', '') or '',
        "is_verified": is_verified,
        "is_active": True,
        "auth_provider": auth_provider,
        "role": "user",
        "favorite_tokens": [] 
    }
    
    return repo.create_user(user_data)

def create_or_update_google_user(email: str, name: str, first_name: str = None, last_name: str = None) -> Dict[str, Any]:
    repo = get_repository()
    
    existing_user = repo.get_user_by_email(email)
    
    if existing_user:
        updates = {
            "name": name,
            "first_name": first_name or "",
            "last_name": last_name or "",
            "is_verified": True,  
            "auth_provider": "google"
        }
        
        if 'favorite_tokens' not in existing_user:
            updates['favorite_tokens'] = []
        
        updated_user = repo.update_user(existing_user['id'], updates)
        return updated_user
    else:
        user_data = {
            "email": email,
            "name": name,
            "hashed_password": "",  
            "first_name": first_name or "",
            "last_name": last_name or "",
            "is_verified": True,
            "is_active": True,
            "auth_provider": "google",
            "role": "user",
            "favorite_tokens": [] 
        }
        
        new_user = repo.create_user(user_data)
        return new_user

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    return repo.get_user_by_id(user_id)

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    return repo.get_user_by_email(email)

def get_user_by_name(name: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    return repo.get_user_by_name(name)

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    if not user:
        print(f"[INFO][AUTH] - Пользователь с email {email} не найден")
        return None
    
    if not user.get('hashed_password'):
        print(f"[INFO][AUTH] - У пользователя {email} нет пароля (возможно Google аккаунт)")
        return None
    
    if not verify_password(password, user['hashed_password']):
        print(f"[INFO][AUTH] - Неверный пароль для пользователя {email}")
        return None
    
    if not user.get('is_active', True):
        print(f"[INFO][AUTH] - Пользователь {email} неактивен")
        return None
    
    return user

def update_user(user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    
    updates = {k: v for k, v in kwargs.items() if v is not None}
    
    if not updates:
        return get_user(user_id)
    
    return repo.update_user(user_id, updates)

def update_user_role(user_id: str, role: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    return repo.update_user_role(user_id, role)

def verify_user_email(user_id: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    return repo.verify_user_email(user_id)

def deactivate_user(user_id: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    return repo.deactivate_user(user_id)

def activate_user(user_id: str) -> Optional[Dict[str, Any]]:
    repo = get_repository()
    return repo.activate_user(user_id)

def change_user_password(user_id: str, new_password: str) -> Optional[Dict[str, Any]]:
    hashed_password = get_password_hash(new_password)
    return update_user(user_id, hashed_password=hashed_password)

def logout_user(user_id: str) -> bool:
    repo = get_repository()
    result = repo.clear_tokens(user_id)
    return result is not None