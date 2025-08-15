
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

class WalletBase(BaseModel):
    title: str = Field(..., description="Название кошелька", max_length=200)
    image: Optional[str] = Field(None, description="URL изображения или Base64")
    url: Optional[str] = Field(None, description="URL кошелька")
    description: Optional[str] = Field(None, description="Описание кошелька")
    category: Optional[str] = Field(None, description="Категория кошелька (mobile, desktop, hardware, web)")
    supported_currencies: List[str] = Field(default_factory=list, description="Поддерживаемые валюты")
    features: List[str] = Field(default_factory=list, description="Особенности кошелька")

class WalletCreate(WalletBase):
    pass

class WalletUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Название кошелька", max_length=200)
    image: Optional[str] = Field(None, description="URL изображения или Base64")
    url: Optional[str] = Field(None, description="URL кошелька")
    description: Optional[str] = Field(None, description="Описание кошелька")
    category: Optional[str] = Field(None, description="Категория кошелька")
    supported_currencies: Optional[List[str]] = Field(None, description="Поддерживаемые валюты")
    features: Optional[List[str]] = Field(None, description="Особенности кошелька")
    is_deleted: Optional[bool] = Field(None, description="Удален ли кошелек")

class WalletResponse(WalletBase):
    id: str = Field(..., description="Уникальный идентификатор")
    is_deleted: bool = Field(default=False, description="Удален ли кошелек")
    created_at: str = Field(..., description="Дата создания")
    updated_at: str = Field(..., description="Дата обновления")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "MetaMask",
                "image": "https://example.com/metamask-logo.png",
                "url": "https://metamask.io",
                "description": "Популярный браузерный кошелек для Ethereum",
                "category": "web",
                "supported_currencies": ["ETH", "BTC", "USDT"],
                "features": ["DeFi", "NFT", "Staking"],
                "is_deleted": False,
                "created_at": "2024-01-21T10:30:00",
                "updated_at": "2024-01-21T10:30:00"
            }
        }

class ConductorBase(BaseModel):
    title: str = Field(..., description="Название проводника", max_length=200)
    image: Optional[str] = Field(None, description="URL изображения или Base64")
    url: Optional[str] = Field(None, description="URL проводника")
    description: Optional[str] = Field(None, description="Описание проводника")
    category: Optional[str] = Field(None, description="Категория проводника (exchange, dex, broker, p2p)")
    supported_currencies: List[str] = Field(default_factory=list, description="Поддерживаемые валюты")
    features: List[str] = Field(default_factory=list, description="Особенности проводника")
    fees: Optional[str] = Field(None, description="Информация о комиссиях")

class ConductorCreate(ConductorBase):
    pass

class ConductorUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Название проводника", max_length=200)
    image: Optional[str] = Field(None, description="URL изображения или Base64")
    url: Optional[str] = Field(None, description="URL проводника")
    description: Optional[str] = Field(None, description="Описание проводника")
    category: Optional[str] = Field(None, description="Категория проводника")
    supported_currencies: Optional[List[str]] = Field(None, description="Поддерживаемые валюты")
    features: Optional[List[str]] = Field(None, description="Особенности проводника")
    fees: Optional[str] = Field(None, description="Информация о комиссиях")
    is_deleted: Optional[bool] = Field(None, description="Удален ли проводник")

class ConductorResponse(ConductorBase):
    id: str = Field(..., description="Уникальный идентификатор")
    is_deleted: bool = Field(default=False, description="Удален ли проводник")
    created_at: str = Field(..., description="Дата создания")
    updated_at: str = Field(..., description="Дата обновления")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "Coinbase",
                "image": "https://example.com/coinbase-logo.png",
                "url": "https://coinbase.com",
                "description": "Популярная криптовалютная биржа",
                "category": "exchange",
                "supported_currencies": ["BTC", "ETH", "USDT", "ADA"],
                "features": ["Fiat", "Mobile App", "Insurance"],
                "fees": "0.5% торговая комиссия",
                "is_deleted": False,
                "created_at": "2024-01-21T10:30:00",
                "updated_at": "2024-01-21T10:30:00"
            }
        }