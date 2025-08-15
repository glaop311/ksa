from fastapi import HTTPException, status
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import uuid

from app.core.security.permissions import require_admin
from app.core.database.connector import get_generic_repository
from app.core.security.security import get_admin_user

class BaseAdminController:
    def __init__(self, table_name: str, entity_name: str):
        self.table_name = table_name
        self.entity_name = entity_name
    
    def _get_repository(self):
        return get_generic_repository(self.table_name)
    
    def _convert_floats_to_decimals(self, data: Dict[str, Any]) -> Dict[str, Any]:

        converted_data = {}
        
        for key, value in data.items():
            if isinstance(value, float):
                converted_data[key] = Decimal(str(value))
            elif isinstance(value, list):

                converted_data[key] = [
                    Decimal(str(item)) if isinstance(item, float) else item 
                    for item in value
                ]
            elif isinstance(value, dict):

                converted_data[key] = self._convert_floats_to_decimals(value)
            else:

                converted_data[key] = value
        
        return converted_data
    
    def _add_audit_fields(self, data: Dict[str, Any], admin_id: str, action: str) -> Dict[str, Any]:
        timestamp = datetime.now().isoformat()
        
        if action == "create":
            data.update({
                'id': str(uuid.uuid4()),
                'created_at': timestamp,
                'updated_at': timestamp,
                'is_deleted': False,
                'created_by_admin': admin_id
            })
        elif action == "update":
            data.update({
                'updated_at': timestamp,
                'updated_by_admin': admin_id
            })
        elif action == "delete":
            data.update({
                'is_deleted': True,
                'deleted_at': timestamp,
                'deleted_by_admin': admin_id
            })
        
        return data
    
    async def create_entity(self, entity_data: Dict[str, Any], current_user: Dict[str, Any]):
        try:
            repo = self._get_repository()
            
            entity_data = self._convert_floats_to_decimals(entity_data)
            
            if self.table_name == "LiberandumAggregationTokenStats" and 'approved' not in entity_data:
                entity_data['approved'] = False
            
            entity_data = self._add_audit_fields(entity_data, current_user['id'], "create")
            created_entity = repo.create(entity_data, auto_id=False)
            
            return {
                "message": f"{self.entity_name} создан",
                "entity": created_entity,
                "admin": current_user['email']
            }
        except Exception as e:
            print(f"[ERROR][BaseAdminController] - Ошибка создания {self.entity_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Ошибка создания {self.entity_name.lower()}: {str(e)}"
            )
    
    async def get_entities_list(self, limit: Optional[int], current_user: Dict[str, Any]):
        try:
            repo = self._get_repository()
            items = repo.scan_items(self.table_name, limit=limit)
            active_items = [item for item in items if not item.get('is_deleted', False)]
            
            if self.table_name == "LiberandumAggregationToken":
                for item in active_items:
                    item['description_en'] = item.get('description', '')
                    item['description_ru'] = item.get('description_ru', '')
                    item['description_uz'] = item.get('description_uz', '')
            elif self.table_name == "LiberandumAggregationTokenStats":
                for item in active_items:
                    if 'approved' not in item:
                        item['approved'] = False
            
            return {
                "total": len(active_items),
                f"{self.entity_name.lower()}s": active_items,
                "admin": current_user['email']
            }
        except Exception as e:
            print(f"[ERROR][BaseAdminController] - Ошибка получения списка {self.entity_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Ошибка получения списка {self.entity_name.lower()}: {str(e)}"
            )
    
    async def get_entity_by_id(self, entity_id: str, current_user: Dict[str, Any]):
        try:
            repo = self._get_repository()
            entity = repo.get_by_id(entity_id)
            
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"{self.entity_name} не найден"
                )
            
            if self.table_name == "LiberandumAggregationToken":
                entity['description_en'] = entity.get('description', '')
                entity['description_ru'] = entity.get('description_ru', '')
                entity['description_uz'] = entity.get('description_uz', '')
            elif self.table_name == "LiberandumAggregationTokenStats":
                if 'approved' not in entity:
                    entity['approved'] = False
            
            return {
                f"{self.entity_name.lower()}": entity,
                "admin": current_user['email']
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERROR][BaseAdminController] - Ошибка получения {self.entity_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Ошибка получения {self.entity_name.lower()}: {str(e)}"
            )
    
    async def update_entity(self, entity_id: str, updates: Dict[str, Any], current_user: Dict[str, Any]):
        try:
            repo = self._get_repository()
            
            existing_entity = repo.get_by_id(entity_id)
            if not existing_entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"{self.entity_name} не найден"
                )
            
            updates = self._convert_floats_to_decimals(updates)
            
            if self.table_name == "LiberandumAggregationToken" and 'description_en' in updates:
                updates['description'] = updates['description_en']
            
            updates = self._add_audit_fields(updates, current_user['id'], "update")
            
            print(f"[DEBUG][BaseAdminController] - Обновление {self.entity_name}:")
            print(f"   Entity ID: {entity_id}")
            print(f"   Updates (после конвертации): {list(updates.keys())}")
            for key, value in updates.items():
                if isinstance(value, Decimal):
                    print(f"   {key}: {value} (Decimal)")
                elif isinstance(value, float):
                    print(f"   {key}: {value} (float - ОШИБКА!)")
                else:
                    print(f"   {key}: {type(value).__name__}")
            
            updated_entity = repo.update_by_id(entity_id, updates)
            
            if self.table_name == "LiberandumAggregationToken" and updated_entity:
                updated_entity['description_en'] = updated_entity.get('description', '')
                updated_entity['description_ru'] = updated_entity.get('description_ru', '')
                updated_entity['description_uz'] = updated_entity.get('description_uz', '')
            elif self.table_name == "LiberandumAggregationTokenStats" and updated_entity:
                if 'approved' not in updated_entity:
                    updated_entity['approved'] = False
            
            return {
                "message": f"{self.entity_name} обновлен",
                f"{self.entity_name.lower()}": updated_entity,
                "admin": current_user['email']
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERROR][BaseAdminController] - Ошибка обновления {self.entity_name}: {e}")
            print(f"[ERROR][BaseAdminController] - Updates: {updates}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Ошибка обновления {self.entity_name.lower()}: {str(e)}"
            )
    
    async def delete_entity(self, entity_id: str, current_user: Dict[str, Any]):
        try:
            repo = self._get_repository()
            
            existing_entity = repo.get_by_id(entity_id)
            if not existing_entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"{self.entity_name} не найден"
                )
            
            delete_data = self._add_audit_fields({}, current_user['id'], "delete")
            repo.update_by_id(entity_id, delete_data)
            
            return {
                "message": f"{self.entity_name} удален",
                f"{self.entity_name.lower()}_id": entity_id,
                "admin": current_user['email']
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERROR][BaseAdminController] - Ошибка удаления {self.entity_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Ошибка удаления {self.entity_name.lower()}: {str(e)}"
            )