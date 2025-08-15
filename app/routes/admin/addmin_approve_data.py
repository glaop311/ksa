from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Dict, Any
from datetime import datetime

from app.core.security.security import get_admin_user
from app.core.database.connector import get_generic_repository

router = APIRouter()

@router.put("/approve-token")
async def approve_token(
    coingecko_id: str = Body(..., description="CoinGecko ID токена"),
    approved: bool = Body(..., description="Статус подтверждения (true/false)"),
    current_user = Depends(get_admin_user)
):
    try:
        tokens_repo = get_generic_repository("LiberandumAggregationToken")
        token_stats_repo = get_generic_repository("LiberandumAggregationTokenStats")
        
        token_results = tokens_repo.find_by_field("coingecko_id", coingecko_id)
        if not token_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Токен с coingecko_id '{coingecko_id}' не найден"
            )
        
        token = None
        for t in token_results:
            if not t.get('is_deleted', False):
                token = t
                break
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Активный токен с coingecko_id '{coingecko_id}' не найден"
            )
        
        timestamp = datetime.utcnow().isoformat()
        
        token_updates = {
            'approved': approved,
            'approved_by': current_user['id'],
            'approved_at': timestamp,
            'updated_at': timestamp,
            'updated_by_admin': current_user['id']
        }
        
        updated_token = tokens_repo.update_by_id(token['id'], token_updates)
        
        token_stats_results = token_stats_repo.find_by_field("coingecko_id", coingecko_id)
        updated_stats = []
        
        for stats in token_stats_results:
            if not stats.get('is_deleted', False):
                stats_updates = {
                    'approved': approved,
                    'approved_by': current_user['id'],
                    'approved_at': timestamp,
                    'updated_at': timestamp,
                    'updated_by_admin': current_user['id']
                }
                
                updated_stat = token_stats_repo.update_by_id(stats['id'], stats_updates)
                if updated_stat:
                    updated_stats.append(updated_stat)
        
        status_text = "подтвержден" if approved else "отклонен"
        
        return {
            "message": f"Токен {token.get('symbol', 'unknown')} ({coingecko_id}) {status_text}",
            "coingecko_id": coingecko_id,
            "approved": approved,
            "updated_token": updated_token,
            "updated_stats_count": len(updated_stats),
            "updated_stats": updated_stats,
            "admin": current_user['email'],
            "timestamp": timestamp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления статуса токена: {str(e)}"
        )