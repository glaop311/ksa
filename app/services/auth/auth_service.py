
import httpx
from typing import Dict, Any, Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.security.config import settings
from app.core.database.crud.user import get_user_by_email, create_or_update_google_user, create_tokens_for_user

class GoogleAuthService:
    @staticmethod
    async def get_google_token(code: str) -> Optional[Dict[str, Any]]:
        """
        Обменивает authorization code на токены Google
        """
        if not code:
            print("[ERROR][GoogleAuth] - Отсутствует authorization code")
            return None
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI
            }
            
            try:
                print(f"[DEBUG][GoogleAuth] - Отправляем запрос на {token_url}")
                print(f"[DEBUG][GoogleAuth] - redirect_uri: {settings.GOOGLE_REDIRECT_URI}")
                
                response = await client.post(token_url, data=data)
                
                print(f"[DEBUG][GoogleAuth] - Статус ответа: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text
                    print(f"[ERROR][GoogleAuth] - Ошибка получения токена: {error_text}")
                    
                    # Попробуем распарсить ошибку
                    try:
                        error_json = response.json()
                        error_description = error_json.get('error_description', 'Неизвестная ошибка')
                        print(f"[ERROR][GoogleAuth] - Описание ошибки: {error_description}")
                    except:
                        pass
                    
                    return None
                
                token_data = response.json()
                print(f"[INFO][GoogleAuth] - Токены получены успешно")
                return token_data
                
            except httpx.TimeoutException:
                print(f"[ERROR][GoogleAuth] - Timeout при запросе токена")
                return None
            except Exception as e:
                print(f"[ERROR][GoogleAuth] - Исключение при запросе токена: {e}")
                return None

    @staticmethod
    async def get_google_user_info(token: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе из Google API
        """
        if not token:
            print("[ERROR][GoogleAuth] - Отсутствует access token")
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code != 200:
                    print(f"[ERROR][GoogleAuth] - Ошибка получения данных пользователя: {response.status_code} - {response.text}")
                    return None

                user_info = response.json()
                print(f"[INFO][GoogleAuth] - Данные пользователя получены для: {user_info.get('email')}")
                return user_info
                
            except Exception as e:
                print(f"[ERROR][GoogleAuth] - Исключение при получении данных пользователя: {e}")
                return None

    @staticmethod
    async def create_jwt_for_user(user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает или обновляет пользователя и генерирует JWT токены
        """
        email = user_info.get("email")
        if not email:
            print("[ERROR][GoogleAuth] - Отсутствует email в данных пользователя")
            raise ValueError("Email пользователя не найден")
        
        try:
            # Проверяем существующего пользователя
            db_user = get_user_by_email(email)
            
            if not db_user:
                print(f"[INFO][GoogleAuth] - Создаем нового пользователя: {email}")
                db_user = create_or_update_google_user(
                    email=email,
                    name=user_info.get("name", email.split("@")[0]),
                    first_name=user_info.get("given_name"),
                    last_name=user_info.get("family_name")
                )
            else:
                print(f"[INFO][GoogleAuth] - Обновляем существующего пользователя: {email}")
                db_user = create_or_update_google_user(
                    email=email,
                    name=user_info.get("name", db_user.get("name", "")),
                    first_name=user_info.get("given_name"),
                    last_name=user_info.get("family_name")
                )
            
            # Генерируем JWT токены
            access_token, refresh_token = create_tokens_for_user(db_user['id'])
            
            # Получаем обновленного пользователя с токенами
            from app.core.database.crud.user import get_user
            updated_user = get_user(db_user['id'])
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": updated_user
            }
            
        except Exception as e:
            print(f"[ERROR][GoogleAuth] - Ошибка создания JWT для пользователя: {e}")
            raise e

async def authenticate_google_user(code: str) -> Optional[Dict[str, Any]]:
    """
    Полная аутентификация через Google с authorization code
    """
    if not code:
        print("[ERROR][GoogleAuth] - Отсутствует authorization code")
        return None

    try:
        # Шаг 1: Обмениваем код на токены
        print(f"[INFO][GoogleAuth] - Начинаем аутентификацию с кодом")
        token_data = await GoogleAuthService.get_google_token(code)
        if not token_data:
            print("[ERROR][GoogleAuth] - Не удалось получить токены от Google")
            return None

        # Шаг 2: Получаем access token
        access_token = token_data.get("access_token")
        if not access_token:
            print("[ERROR][GoogleAuth] - Отсутствует access_token в ответе")
            return None

        # Шаг 3: Получаем информацию о пользователе
        user_info = await GoogleAuthService.get_google_user_info(access_token)
        if not user_info:
            print("[ERROR][GoogleAuth] - Не удалось получить данные пользователя")
            return None

        # Шаг 4: Создаем JWT токены
        return await GoogleAuthService.create_jwt_for_user(user_info)

    except Exception as e:
        print(f"[ERROR][GoogleAuth] - Ошибка в authenticate_google_user: {e}")
        return None

async def authenticate_google_user_with_credential(credential: str) -> Optional[Dict[str, Any]]:
    """
    Аутентификация через Google ID Token (для SPA приложений)
    """
    if not credential:
        print("[ERROR][GoogleAuth] - Отсутствует credential")
        return None
    
    try:
        print(f"[INFO][GoogleAuth] - Проверяем ID token")
        
        # Проверяем и декодируем ID token
        id_info = id_token.verify_oauth2_token(
            credential, 
            google_requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        # Извлекаем информацию о пользователе
        user_info = {
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "given_name": id_info.get("given_name"),
            "family_name": id_info.get("family_name"),
            "picture": id_info.get("picture")
        }
        
        print(f"[INFO][GoogleAuth] - ID token проверен для: {user_info.get('email')}")
        
        # Создаем JWT токены
        return await GoogleAuthService.create_jwt_for_user(user_info)
        
    except ValueError as e:
        print(f"[ERROR][GoogleAuth] - Недействительный ID токен: {e}")
        return None
    except Exception as e:
        print(f"[ERROR][GoogleAuth] - Ошибка аутентификации с ID token: {e}")
        return None