from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Dict, Any, Optional, List

from app.core.security.security import get_admin_user
from app.routes.admin.admin_controller import BaseAdminController
from app.schemas.wallte_conductors import ConductorCreate, ConductorUpdate, ConductorResponse
from app.core.database.connector import get_generic_repository

router = APIRouter()
controller = BaseAdminController("LiberandumApiConductors", "conductor")

@router.post("/", response_model=ConductorResponse)
async def create_conductor(conductor_data: ConductorCreate, current_user = Depends(get_admin_user)):

    result = await controller.create_entity(conductor_data.dict(), current_user)
    return ConductorResponse(**result["entity"])

@router.get("/", response_model=List[ConductorResponse])
async def list_conductors(current_user = Depends(get_admin_user)):

    result = await controller.get_entities_list(None, current_user)
    return [ConductorResponse(**conductor) for conductor in result["conductors"]]

@router.get("/search", response_model=List[ConductorResponse])
async def search_conductors(
    q: str = Query(..., min_length=1, description="Поиск по названию"),
    limit: int = Query(default=50, ge=1, le=200, description="Количество результатов"),
    current_user = Depends(get_admin_user)
):

    try:
        conductors_repo = get_generic_repository("LiberandumApiConductors")
        all_conductors = conductors_repo.list_all(limit=1000)
        
        query_lower = q.lower().strip()
        results = []
        
        for conductor in all_conductors:
            if conductor.get('is_deleted', False):
                continue
                
            title = conductor.get('title', '').lower()
            url = conductor.get('url', '').lower()
            
            if (query_lower in title or 
                query_lower in url or
                title.startswith(query_lower)):
                
                results.append(ConductorResponse(**conductor))
            
            if len(results) >= limit:
                break
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска проводников: {str(e)}"
        )

@router.get("/{conductor_id}", response_model=ConductorResponse)
async def get_conductor(conductor_id: str, current_user = Depends(get_admin_user)):

    result = await controller.get_entity_by_id(conductor_id, current_user)
    return ConductorResponse(**result["conductor"])

@router.put("/{conductor_id}", response_model=ConductorResponse)
async def update_conductor(conductor_id: str, updates: ConductorUpdate, current_user = Depends(get_admin_user)):

    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    result = await controller.update_entity(conductor_id, update_data, current_user)
    return ConductorResponse(**result["conductor"])

@router.delete("/{conductor_id}")
async def delete_conductor(conductor_id: str, current_user = Depends(get_admin_user)):

    return await controller.delete_entity(conductor_id, current_user)