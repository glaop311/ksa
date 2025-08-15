from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Dict, Any, Optional, List

from app.core.security.security import get_admin_user
from app.routes.admin.admin_controller import BaseAdminController
from app.schemas.people_audit import PersonCreate, PersonUpdate, PersonResponse
from app.core.database.connector import get_generic_repository

router = APIRouter()
controller = BaseAdminController("LiberandumApiPeople", "person")

@router.post("/", response_model=PersonResponse)
async def create_person(person_data: PersonCreate, current_user = Depends(get_admin_user)):
    result = await controller.create_entity(person_data.dict(), current_user)
    return PersonResponse(**result["entity"])

@router.get("/", response_model=list[PersonResponse])
async def list_people( current_user = Depends(get_admin_user)):
    result = await controller.get_entities_list(current_user)
    return [PersonResponse(**person) for person in result["persons"]]

@router.get("/search", response_model=list[PersonResponse])
async def search_people(
    q: str = Query(..., min_length=1, description="Поиск по имени, описанию или позиции"),
    limit: int = Query(default=50, ge=1, le=200, description="Количество результатов"),
    current_user = Depends(get_admin_user)
):
    try:
        people_repo = get_generic_repository("LiberandumApiPeople")
        all_people = people_repo.list_all(limit=1000)
        
        query_lower = q.lower().strip()
        results = []
        
        for person in all_people:
            if person.get('is_deleted', False):
                continue
                
            full_name = person.get('full_name', '').lower()
            description = person.get('description', '').lower()
            position = person.get('position', '').lower()
            
            if (query_lower in full_name or 
                query_lower in description or 
                query_lower in position or
                full_name.startswith(query_lower)):
                
                results.append(PersonResponse(**person))
            
            if len(results) >= limit:
                break
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска людей: {str(e)}"
        )

@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(person_id: str, current_user = Depends(get_admin_user)):
    result = await controller.get_entity_by_id(person_id, current_user)
    return PersonResponse(**result["person"])

@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(person_id: str, updates: PersonUpdate, current_user = Depends(get_admin_user)):
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    result = await controller.update_entity(person_id, update_data, current_user)
    return PersonResponse(**result["person"])

@router.delete("/{person_id}")
async def delete_person(person_id: str, current_user = Depends(get_admin_user)):
    return await controller.delete_entity(person_id, current_user)