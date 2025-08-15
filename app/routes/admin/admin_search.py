from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional, Dict, Any

from app.core.database.connector import get_generic_repository
from app.core.security.security import get_admin_user

try:
    from app.services.admin.coingecko_search_service import coingecko_search_service
except ImportError:
    coingecko_search_service = None

router = APIRouter()

@router.get("/coingecko/tokens")
async def search_coingecko_tokens(
    q: str = Query(..., min_length=1, description="Название или символ токена"),
    current_user = Depends(get_admin_user)
):
    if not coingecko_search_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CoinGecko search недоступен"
        )
    
    try:
        results = await coingecko_search_service.search_coins(q, 1000)
        
        return {
            "query": q,
            "results": results,
            "total": len(results),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска: {str(e)}"
        )

@router.get("/coingecko/exchanges")
async def search_coingecko_exchanges(
    q: str = Query(..., min_length=1, description="Название биржи"),
    current_user = Depends(get_admin_user)
):
    if not coingecko_search_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CoinGecko search недоступен"
        )
    
    try:
        results = await coingecko_search_service.search_exchanges(q, 1000)
        
        return {
            "query": q,
            "results": results,
            "total": len(results),
            "message": "Выберите биржу и скопируйте её ID для использования в форме создания"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска: {str(e)}"
        )
    
@router.get("/tokens")
async def search_tokens(
    q: str = Query(..., min_length=1, description="Название или символ токена"),
    show_all: bool = Query(default=False, description="Показать все токены (включая неподтвержденные)"),
    current_user = Depends(get_admin_user)
):
    try:
        tokens_repo = get_generic_repository("LiberandumAggregationToken")
        all_tokens = tokens_repo.list_all(limit=1000)
        
        query_lower = q.lower().strip()
        results = []
        
        for token in all_tokens:
            if token.get('is_deleted', False):
                continue
                
            name = (token.get('name') or '').lower()
            symbol = (token.get('symbol') or '').lower()
            coingecko_id = (token.get('coingecko_id') or '').lower()
            description = (token.get('description') or '').lower()
            description_ru = (token.get('description_ru') or '').lower()
            description_uz = (token.get('description_uz') or '').lower()
            
            if (query_lower in name or 
                query_lower in symbol or 
                query_lower in coingecko_id or
                query_lower in description or
                query_lower in description_ru or
                query_lower in description_uz or
                symbol == query_lower):
                
                token_result = {
                    'id': token.get('id'),
                    'name': token.get('name') or '',
                    'symbol': (token.get('symbol') or '').upper(),
                    'coingecko_id': token.get('coingecko_id') or '',
                    'description_en': token.get('description') or '',
                    'description_ru': token.get('description_ru') or '',
                    'description_uz': token.get('description_uz') or '',
                    'avatar_image': token.get('avatar_image') or '',
                    'website': token.get('website') or '',
                    'approved': token.get('approved', False),
                    'created_at': token.get('created_at') or '',
                    'created_by_admin': token.get('created_by_admin') or ''
                }
                results.append(token_result)
        
        return {
            "table": "LiberandumAggregationToken",
            "query": q,
            "results": results,
            "total": len(results),
            "admin": current_user['email']
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска токенов: {str(e)}"
        )

@router.get("/token-stats")
async def search_token_stats(
    q: str = Query(..., min_length=1, description="Символ или название токена"),
    show_all: bool = Query(default=False, description="Показать все токены (включая неподтвержденные)"),
    current_user = Depends(get_admin_user)
):
    try:
        token_stats_repo = get_generic_repository("LiberandumAggregationTokenStats")
        all_stats = token_stats_repo.list_all(limit=1000)
        
        query_lower = q.lower().strip()
        results = []
        
        for stat in all_stats:
            if stat.get('is_deleted', False):
                continue
            
            if not show_all and not stat.get('approved', False):
                continue
                
            symbol = (stat.get('symbol') or '').lower()
            coin_name = (stat.get('coin_name') or '').lower()
            coingecko_id = (stat.get('coingecko_id') or '').lower()
            
            if (query_lower in symbol or 
                query_lower in coin_name or 
                query_lower in coingecko_id or
                symbol == query_lower):
                
                stat_result = {
                    'id': stat.get('id'),
                    'symbol': (stat.get('symbol') or '').upper(),
                    'coin_name': stat.get('coin_name') or '',
                    'coingecko_id': stat.get('coingecko_id') or '',
                    'price': stat.get('price', 0),
                    'market_cap': stat.get('market_cap', 0),
                    'trading_volume_24h': stat.get('trading_volume_24h', 0),
                    'approved': stat.get('approved', False),
                    'approved_by': stat.get('approved_by') or '',
                    'approved_at': stat.get('approved_at') or '',
                    'rejected': stat.get('rejected', False),
                    'rejection_reason': stat.get('rejection_reason') or '',
                    'created_at': stat.get('created_at') or '',
                    'updated_at': stat.get('updated_at') or ''
                }
                results.append(stat_result)
        
        approved_count = len([r for r in results if r.get('approved', False)])
        pending_count = len([r for r in results if not r.get('approved', False) and not r.get('rejected', False)])
        
        return {
            "table": "LiberandumAggregationTokenStats",
            "query": q,
            "results": results,
            "total": len(results),
            "approved_count": approved_count,
            "pending_count": pending_count,
            "filter": "all" if show_all else "approved_only",
            "admin": current_user['email']
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска статистики токенов: {str(e)}"
        )

@router.get("/exchanges")
async def search_exchanges(
    q: str = Query(..., min_length=1, description="Название биржи"),
    current_user = Depends(get_admin_user)
):
    try:
        exchanges_repo = get_generic_repository("LiberandumAggregationExchanges")
        all_exchanges = exchanges_repo.list_all(limit=1000)
        
        query_lower = q.lower().strip()
        results = []
        
        for exchange in all_exchanges:
            if exchange.get('is_deleted', False):
                continue
                
            name = (exchange.get('name') or '').lower()
            coingecko_id = (exchange.get('coingecko_id') or '').lower()
            
            if (query_lower in name or 
                query_lower in coingecko_id):
                
                results.append({
                    'id': exchange.get('id'),
                    'name': exchange.get('name') or '',
                    'coingecko_id': exchange.get('coingecko_id') or '',
                    'avatar_image': exchange.get('avatar_image') or '',
                    'website': exchange.get('website') or '',
                    'country': exchange.get('country') or '',
                    'created_at': exchange.get('created_at') or '',
                    'created_by_admin': exchange.get('created_by_admin') or ''
                })
            
        return {
            "table": "LiberandumAggregationExchanges",
            "query": q,
            "results": results,
            "total": len(results),
            "admin": current_user['email']
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска бирж: {str(e)}"
        )

@router.get("/exchange-stats")
async def search_exchange_stats(
    q: str = Query(..., min_length=1, description="Название биржи"),
    current_user = Depends(get_admin_user)
):
    try:
        exchange_stats_repo = get_generic_repository("LiberandumAggregationExchangesStats")
        all_stats = exchange_stats_repo.list_all(limit=1000)
        
        query_lower = q.lower().strip()
        results = []
        
        for stat in all_stats:
            if stat.get('is_deleted', False):
                continue
                
            name = (stat.get('name') or '').lower()
            
            if query_lower in name:
                results.append({
                    'id': stat.get('id'),
                    'name': stat.get('name') or '',
                    'exchange_id': stat.get('exchange_id') or '',
                    'trading_volume_24h': stat.get('trading_volume_24h', 0),
                    'trading_volume_1w': stat.get('trading_volume_1w', 0),
                    'reserves': stat.get('reserves', 0),
                    'visitors_30d': stat.get('visitors_30d', 0),
                    'coins_count': stat.get('coins_count', 0),
                    'created_at': stat.get('created_at') or '',
                    'updated_at': stat.get('updated_at') or ''
                })
            
        return {
            "table": "LiberandumAggregationExchangesStats",
            "query": q,
            "results": results,
            "total": len(results),
            "admin": current_user['email']
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска статистики бирж: {str(e)}"
        )

@router.get("/users")
async def search_users(
    q: str = Query(..., min_length=1, description="Email, имя пользователя"),
    current_user = Depends(get_admin_user)
):
    try:
        users_repo = get_generic_repository("users")
        all_users = users_repo.list_all(limit=1000)
        
        query_lower = q.lower().strip()
        results = []
        
        for user in all_users:
            if not user.get('is_active', True):
                continue
                
            email = (user.get('email') or '').lower()
            name = (user.get('name') or '').lower()
            first_name = (user.get('first_name') or '').lower()
            last_name = (user.get('last_name') or '').lower()
            
            if (query_lower in email or 
                query_lower in name or 
                query_lower in first_name or 
                query_lower in last_name):
                
                user_data = {
                    'id': user.get('id'),
                    'email': user.get('email') or '',
                    'name': user.get('name') or '',
                    'first_name': user.get('first_name') or '',
                    'last_name': user.get('last_name') or '',
                    'role': user.get('role', 'user'),
                    'is_verified': user.get('is_verified', False),
                    'is_active': user.get('is_active', True),
                    'auth_provider': user.get('auth_provider', 'local'),
                    'created_at': user.get('created_at') or '',
                    'updated_at': user.get('updated_at') or ''
                }
                results.append(user_data)
        
        return {
            "table": "users",
            "query": q,
            "results": results,
            "total": len(results),
            "admin": current_user['email']
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска пользователей: {str(e)}"
        )