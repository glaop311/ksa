from fastapi import APIRouter, HTTPException, status, Query

from app.services.market.market_service import market_service
from app.schemas.market import ExchangeDetailResponse, ExchangeListResponse, ExchangeResponse, ExchangeHalalStatus
from app.core.database.connector import get_generic_repository
from typing import Dict, Any

router = APIRouter()

def from_db_to_api(exchange_stats: Dict[str, Any], exchange: Dict[str, Any] = None, rank: int = 1) -> ExchangeResponse:
    def safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return default
    
    def safe_int(value, default=0):
        try:
            if value is None:
                return default
            return int(float(str(value).replace(',', '')))
        except (ValueError, TypeError):
            return default
    
    def format_currency(value):
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        elif value >= 1_000:
            return f"${value / 1_000:.2f}K"
        else:
            return f"${value:.2f}"
    
    volume_24h = safe_float(exchange_stats.get('trading_volume_24h'))
    reserves = safe_float(exchange_stats.get('reserves'))
    
    return ExchangeResponse(
        rank=rank,
        id=str(exchange_stats.get('name', 'unknown')).lower().replace(' ', '_'),
        name=str(exchange_stats.get('name', '')),
        image=exchange.get('avatar_image', '') if exchange else '',
        halal_status=ExchangeHalalStatus(
            is_halal=exchange_stats.get('is_halal'),
            score=str(exchange_stats.get('halal_score', '')),
            rating=safe_int(exchange_stats.get('halal_rating'))
        ),
        trust_score=safe_int(exchange_stats.get('trust_score')),
        volume_24h_usd=volume_24h,
        volume_24h_formatted=format_currency(volume_24h),
        reserves_usd=reserves,
        reserves_formatted=format_currency(reserves),
        trading_pairs_count=safe_int(exchange_stats.get('trading_pairs_count')),
        visitors_monthly=str(safe_int(exchange_stats.get('visitors_30d', 0))),
        supported_fiat=exchange_stats.get('list_supported', []),
        supported_fiat_display=', '.join(exchange_stats.get('list_supported', [])[:3]),
        volume_chart_7d=exchange_stats.get('inflows_1w', []),
        exchange_type="centralized"
    )

@router.get("/", response_model=ExchangeListResponse)
async def get_exchanges_list():
    try:
        result = market_service.get_exchanges_list()
        return result
        
    except Exception as e:
        print(f"[ERROR][Market] - Ошибка получения списка бирж: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения списка бирж"
        )

@router.get("/search", response_model=ExchangeListResponse)
async def search_exchanges(
    q: str = Query(..., min_length=1, description="Название биржи"),
    limit: int = Query(default=20, ge=1, le=100, description="Количество результатов")
):
    try:
        exchanges_repo = get_generic_repository("LiberandumAggregationExchanges")
        exchange_stats_repo = get_generic_repository("LiberandumAggregationExchangesStats")
        
        all_exchanges = exchanges_repo.list_all(limit=500)
        all_exchange_stats = exchange_stats_repo.list_all(limit=500)
        
        stats_by_name = {}
        for stat in all_exchange_stats:
            if not stat.get('is_deleted', False):
                name = stat.get('name', '')
                if name:
                    stats_by_name[name] = stat
        
        query_lower = q.lower().strip()
        results = []
        
        for exchange in all_exchanges:
            if exchange.get('is_deleted', False):
                continue
                
            name = exchange.get('name', '').lower()
            coingecko_id = exchange.get('coingecko_id', '').lower()
            
            if (query_lower in name or 
                query_lower in coingecko_id or
                name.startswith(query_lower)):
                
                exchange_name = exchange.get('name', '')
                exchange_stats = stats_by_name.get(exchange_name)
                
                if exchange_stats:
                    exchange_response = from_db_to_api(
                        exchange_stats, 
                        exchange, 
                        len(results) + 1
                    )
                    results.append(exchange_response)
            
            if len(results) >= limit:
                break
        
        return ExchangeListResponse(data=results)
        
    except Exception as e:
        print(f"[ERROR][Market] - Ошибка поиска бирж: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка поиска бирж"
        )

@router.get("/{exchange_id}", response_model=ExchangeDetailResponse)
async def get_exchange_detail(exchange_id: str):
    try:
        result = market_service.get_exchange_detail(exchange_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Биржа не найдена"
            )
        
        exchange_detail = ExchangeDetailResponse(
            id=result.get('id', ''),
            name=result.get('name', ''),
            image=result.get('image', ''),
            halal_status=ExchangeHalalStatus(
                is_halal=result.get('halal_status', {}).get('is_halal'),
                score=result.get('halal_status', {}).get('score', ''),
                rating=result.get('halal_status', {}).get('rating', 0)
            ),
            trust_score=result.get('trust_score', 0),
            volume_24h_usd=result.get('volume_24h_usd', 0),
            total_assets_usd=result.get('total_assets_usd', 0),
            trading_pairs_count=result.get('trading_pairs_count', 0),
            visitors_monthly=str(result.get('visitors_monthly', 0)),
            website_url=result.get('website_url', ''),
            supported_fiat=result.get('supported_fiat', []),
            country=result.get('country'),
            year_established=result.get('year_established')
        )
        
        return exchange_detail
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR][Market] - Ошибка получения биржи {exchange_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения информации о бирже"
        )