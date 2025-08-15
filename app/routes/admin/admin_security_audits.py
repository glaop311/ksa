from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, Optional

from app.core.security.security import get_admin_user
from app.routes.admin.admin_controller import BaseAdminController
from app.schemas.people_audit import SecurityAuditCreate, SecurityAuditUpdate, SecurityAuditResponse

router = APIRouter()
controller = BaseAdminController("LiberandumApiSecurityAudit", "security_audit")

@router.post("/", response_model=SecurityAuditResponse)
async def create_security_audit(audit_data: SecurityAuditCreate, current_user = Depends(get_admin_user)):
    result = await controller.create_entity(audit_data.dict(), current_user)
    return SecurityAuditResponse(**result["entity"])

@router.get("/", response_model=list[SecurityAuditResponse])
async def list_security_audits(current_user = Depends(get_admin_user)):
    result = await controller.get_entities_list(None, current_user)
    entity_key = f"{controller.entity_name.lower()}s"
    entities = result.get(entity_key, [])
    return [SecurityAuditResponse(**audit) for audit in entities]

@router.get("/{audit_id}", response_model=SecurityAuditResponse)
async def get_security_audit(audit_id: str, current_user = Depends(get_admin_user)):
    result = await controller.get_entity_by_id(audit_id, current_user)
    entity_key = controller.entity_name.lower() 
    return SecurityAuditResponse(**result[entity_key])

@router.put("/{audit_id}", response_model=SecurityAuditResponse)
async def update_security_audit(audit_id: str, updates: SecurityAuditUpdate, current_user = Depends(get_admin_user)):
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    result = await controller.update_entity(audit_id, update_data, current_user)

    entity_key = controller.entity_name.lower() 
    return SecurityAuditResponse(**result[entity_key])

@router.delete("/{audit_id}")
async def delete_security_audit(audit_id: str, current_user = Depends(get_admin_user)):
    return await controller.delete_entity(audit_id, current_user)