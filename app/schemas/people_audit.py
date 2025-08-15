# app/schemas/people_audit.py - ОБНОВЛЕННАЯ ВЕРСИЯ

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PersonBase(BaseModel):
    full_name: str = Field(..., description="Полное имя человека", max_length=200)
    avatar_image: Optional[str] = Field(None, description="Base64 изображение или URL")
    description: Optional[str] = Field(None, description="Описание человека")
    position: Optional[str] = Field(None, description="Должность или позиция")
    related_link: Optional[str] = Field(None, description="Ссылка на профиль или сайт")
    category: Optional[str] = Field(None, description="Категория человека (founder, developer, advisor, etc.)")

class PersonCreate(PersonBase):
    pass

class PersonUpdate(BaseModel):
    full_name: Optional[str] = Field(None, description="Полное имя человека", max_length=200)
    avatar_image: Optional[str] = Field(None, description="Base64 изображение или URL")
    description: Optional[str] = Field(None, description="Описание человека")
    position: Optional[str] = Field(None, description="Должность или позиция")
    related_link: Optional[str] = Field(None, description="Ссылка на профиль или сайт")
    category: Optional[str] = Field(None, description="Категория человека (founder, developer, advisor, etc.)")
    is_deleted: Optional[bool] = Field(None, description="Удален ли человек")

class PersonResponse(PersonBase):
    id: str = Field(..., description="Уникальный идентификатор")
    is_deleted: bool = Field(default=False, description="Удален ли человек")
    created_at: str = Field(..., description="Дата создания")
    updated_at: str = Field(..., description="Дата обновления")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "full_name": "Виталик Бутерин",
                "avatar_image": "https://example.com/avatar.jpg",
                "description": "Основатель Ethereum",
                "position": "Основатель",
                "related_link": "https://vitalik.ca",
                "category": "founder",
                "is_deleted": False,
                "created_at": "2024-01-21T10:30:00",
                "updated_at": "2024-01-21T10:30:00"
            }
        }

# Остальные модели без изменений...
class SecurityAuditBase(BaseModel):
    title: str = Field(..., description="Название аудита", max_length=300)
    auditor_name: str = Field(..., description="Имя аудитора")
    link: str = Field(..., description="Ссылка на отчет аудита")
    audit_score: str = Field(..., description="Оценка аудита")

class SecurityAuditCreate(SecurityAuditBase):
    pass

class SecurityAuditUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Название аудита", max_length=300)
    auditor_name: Optional[str] = Field(None, description="Имя аудитора")
    link: Optional[str] = Field(None, description="Ссылка на отчет аудита")
    audit_score: Optional[str] = Field(None, description="Оценка аудита")
    is_deleted: Optional[bool] = Field(None, description="Удален ли аудит")

class SecurityAuditResponse(SecurityAuditBase):
    id: str = Field(..., description="Уникальный идентификатор")
    is_deleted: bool = Field(default=False, description="Удален ли аудит")
    created_at: str = Field(..., description="Дата создания")
    updated_at: str = Field(..., description="Дата обновления")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "Smart Contract Security Audit",
                "auditor_name": "ConsenSys Diligence",
                "link": "https://consensys.net/audit-report",
                "audit_score": "95/100",
                "is_deleted": False,
                "created_at": "2024-01-21T10:30:00",
                "updated_at": "2024-01-21T10:30:00"
            }
        }