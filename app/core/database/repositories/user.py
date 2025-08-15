# app/core/database/repositories/user.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from typing import Dict, Any, Optional, List
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone
import uuid

from ..base import BaseDynamoDBConnector

class UserRepository(BaseDynamoDBConnector):
    def __init__(self, table_name: str = "users"):
        super().__init__()
        self.table_name = table_name
        
        # DynamoDB зарезервированные слова, которые нужно экранировать
        self.reserved_keywords = {
            'name', 'role', 'status', 'timestamp', 'data', 'size', 'type',
            'key', 'value', 'order', 'index', 'count', 'group', 'state',
            'update', 'delete', 'select', 'insert', 'from', 'where'
        }
    
    def _build_safe_update_expression(self, updates: Dict[str, Any]) -> tuple:
        """
        Создает безопасный UpdateExpression с учетом зарезервированных слов
        """
        update_expression = "SET "
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        for field, value in updates.items():
            if field == 'id':  # Никогда не обновляем ID
                continue
                
            # Проверяем, является ли поле зарезервированным словом
            if field.lower() in self.reserved_keywords:
                # Используем плейсхолдер для зарезервированного слова
                name_placeholder = f"#{field}"
                value_placeholder = f":{field}"
                
                expression_attribute_names[name_placeholder] = field
                expression_attribute_values[value_placeholder] = value
                
                update_expression += f"{name_placeholder} = {value_placeholder}, "
            else:
                # Обычное поле
                value_placeholder = f":{field}"
                expression_attribute_values[value_placeholder] = value
                update_expression += f"{field} = {value_placeholder}, "
        
        # Убираем последнюю запятую
        update_expression = update_expression.rstrip(", ")
        
        return update_expression, expression_attribute_names, expression_attribute_values
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        user_data['id'] = str(uuid.uuid4())
        
        defaults = {
            'is_verified': False,
            'is_active': True,
            'auth_provider': 'local',
            'role': 'user',
            'access_token': '',
            'refresh_token': '',
            'access_token_expires_at': '',
            'refresh_token_expires_at': '',
            'favorite_tokens': []
        }
        
        for key, value in defaults.items():
            user_data.setdefault(key, value)
        
        return self.create_item(self.table_name, user_data)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        user = self.get_item(self.table_name, {'id': user_id})
        if user and 'favorite_tokens' not in user:
            self.update_user(user_id, {'favorite_tokens': []})
            user['favorite_tokens'] = []
        return user
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        items = self.query_items(
            self.table_name,
            key_condition=Key('email').eq(email),
            index_name='email-index'
        )
        user = items[0] if items else None
        if user and 'favorite_tokens' not in user:
            self.update_user(user['id'], {'favorite_tokens': []})
            user['favorite_tokens'] = []
        return user
    
    def get_user_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        items = self.query_items(
            self.table_name,
            key_condition=Key('name').eq(name),
            index_name='name-index'
        )
        user = items[0] if items else None
        if user and 'favorite_tokens' not in user:
            self.update_user(user['id'], {'favorite_tokens': []})
            user['favorite_tokens'] = []
        return user
    
    def get_user_by_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        items = self.scan_items(
            self.table_name,
            filter_expression=Attr('refresh_token').eq(refresh_token)
        )
        user = items[0] if items else None
        if user and 'favorite_tokens' not in user:
            self.update_user(user['id'], {'favorite_tokens': []})
            user['favorite_tokens'] = []
        return user
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обновляет пользователя с безопасной обработкой зарезервированных слов
        """
        try:
            # Обрабатываем datetime поля
            if 'access_token_expires_at' in updates and isinstance(updates['access_token_expires_at'], datetime):
                if updates['access_token_expires_at'].tzinfo is None:
                    updates['access_token_expires_at'] = updates['access_token_expires_at'].replace(tzinfo=timezone.utc)
                updates['access_token_expires_at'] = updates['access_token_expires_at'].isoformat()
            
            if 'refresh_token_expires_at' in updates and isinstance(updates['refresh_token_expires_at'], datetime):
                if updates['refresh_token_expires_at'].tzinfo is None:
                    updates['refresh_token_expires_at'] = updates['refresh_token_expires_at'].replace(tzinfo=timezone.utc)
                updates['refresh_token_expires_at'] = updates['refresh_token_expires_at'].isoformat()
            
            # Добавляем updated_at
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            # Создаем безопасное выражение обновления
            update_expression, attr_names, attr_values = self._build_safe_update_expression(updates)
            
            if not attr_values:  # Нечего обновлять
                return self.get_user_by_id(user_id)
            
            table = self.get_table(self.table_name)
            
            # Параметры для update_item
            update_params = {
                'Key': {'id': user_id},
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': attr_values,
                'ReturnValues': 'ALL_NEW'
            }
            
            # Добавляем ExpressionAttributeNames только если есть зарезервированные слова
            if attr_names:
                update_params['ExpressionAttributeNames'] = attr_names
            
            print(f"[DEBUG][UserRepo] - UpdateExpression: {update_expression}")
            print(f"[DEBUG][UserRepo] - AttributeNames: {attr_names}")
            print(f"[DEBUG][UserRepo] - AttributeValues: {list(attr_values.keys())}")
            
            response = table.update_item(**update_params)
            
            return response.get('Attributes')
            
        except Exception as e:
            print(f"[ERROR][UserRepo] - Ошибка обновления пользователя {user_id}: {e}")
            print(f"[ERROR][UserRepo] - Updates: {updates}")
            return None
    
    def update_tokens(self, user_id: str, access_token: str, refresh_token: str, 
                     access_expires: datetime, refresh_expires: datetime) -> Optional[Dict[str, Any]]:
        """
        Обновляет токены пользователя
        """
        if access_expires.tzinfo is None:
            access_expires = access_expires.replace(tzinfo=timezone.utc)
        if refresh_expires.tzinfo is None:
            refresh_expires = refresh_expires.replace(tzinfo=timezone.utc)
            
        updates = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'access_token_expires_at': access_expires.isoformat(),
            'refresh_token_expires_at': refresh_expires.isoformat()
        }
        return self.update_user(user_id, updates)
    
    def clear_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        updates = {
            'access_token': '',
            'refresh_token': '',
            'access_token_expires_at': '',
            'refresh_token_expires_at': ''
        }
        return self.update_user(user_id, updates)
    
    def verify_user_email(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.update_user(user_id, {'is_verified': True})
    
    def deactivate_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.update_user(user_id, {'is_active': False})
    
    def activate_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.update_user(user_id, {'is_active': True})
    
    def update_user_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        valid_roles = ['user', 'pro_user', 'admin']
        if role not in valid_roles:
            raise ValueError(f"Недопустимая роль: {role}")
        return self.update_user(user_id, {'role': role})
    
    def get_users_by_provider(self, auth_provider: str) -> List[Dict[str, Any]]:
        return self.scan_items(
            self.table_name,
            filter_expression=Attr('auth_provider').eq(auth_provider)
        )
    
    def get_active_users(self) -> List[Dict[str, Any]]:
        return self.scan_items(
            self.table_name,
            filter_expression=Attr('is_active').eq(True)
        )
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        return self.scan_items(
            self.table_name,
            filter_expression=Attr('role').eq(role)
        )
    
    def add_favorite_token(self, user_id: str, token_id: str) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        current_favorites = user.get('favorite_tokens', [])
        if token_id not in current_favorites:
            current_favorites.append(token_id)
            return self.update_user(user_id, {'favorite_tokens': current_favorites})
        
        return user
    
    def remove_favorite_token(self, user_id: str, token_id: str) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        current_favorites = user.get('favorite_tokens', [])
        if token_id in current_favorites:
            current_favorites.remove(token_id)
            return self.update_user(user_id, {'favorite_tokens': current_favorites})
        
        return user
    
    def get_favorite_tokens(self, user_id: str) -> List[str]:
        user = self.get_user_by_id(user_id)
        return user.get('favorite_tokens', []) if user else []
    
    def clear_favorite_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.update_user(user_id, {'favorite_tokens': []})
    
    def is_token_favorite(self, user_id: str, token_id: str) -> bool:
        favorites = self.get_favorite_tokens(user_id)
        return token_id in favorites
    
    def get_users_with_favorite_token(self, token_id: str) -> List[Dict[str, Any]]:
        return self.scan_items(
            self.table_name,
            filter_expression=Attr('favorite_tokens').contains(token_id)
        )