# app/schemas/token.py (обновленная версия)

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    refresh_token: str
    access_token_expires_at: str
    refresh_token_expires_at: str

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenPayload(BaseModel):
    sub: Optional[int] = None


class TokenTimeUtils:
    @staticmethod
    def get_utc_now() -> datetime:

        return datetime.now(timezone.utc)
    
    @staticmethod
    def get_utc_timestamp() -> int:

        return int(TokenTimeUtils.get_utc_now().timestamp())
    
    @staticmethod
    def format_utc_time(dt: datetime) -> str:

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    
    @staticmethod
    def parse_utc_time(time_str: str) -> datetime:

        try:
            if time_str.endswith('Z'):
                time_str = time_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return TokenTimeUtils.get_utc_now()

class TokenWithUTC(BaseModel):

    access_token: str
    refresh_token: str
    access_token_expires_at: str
    refresh_token_expires_at: str
    token_type: str = "bearer"
    issued_at: str = Field(default_factory=lambda: TokenTimeUtils.format_utc_time(TokenTimeUtils.get_utc_now()))
    
    class Config:
        json_encoders = {
            datetime: lambda v: TokenTimeUtils.format_utc_time(v)
        }