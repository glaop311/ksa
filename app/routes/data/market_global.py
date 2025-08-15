
from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional

from app.schemas.market_global import GlobalMarketResponse
from app.services.market.global_data.coinmarket_cap_global_service import coinmarketcap_global_service

router = APIRouter()

@router.get("/global", response_model=GlobalMarketResponse)
async def get_global_market_data():

    try:
        result = await coinmarketcap_global_service.get_global_market_data()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Глобальные данные рынка временно недоступны"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR][GlobalMarket] - Неожиданная ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера при получении глобальных данных"
        )

@router.get("/global/cache-info")
async def get_cache_info():

    try:
        cache_info = await coinmarketcap_global_service.get_cache_info()
        return {
            "cache_info": cache_info,
            "cache_ttl_hours": 1,
            "description": "Кэш глобальных данных CoinMarketCap обновляется каждый час"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения информации о кэше: {str(e)}"
        )

@router.post("/global/clear-cache")
async def clear_global_cache():

    try:
        success = await coinmarketcap_global_service.clear_cache()
        
        if success:
            return {
                "message": "Кэш успешно очищен",
                "next_request": "Следующий запрос получит свежие данные из API"
            }
        else:
            return {
                "message": "Кэш был пуст или произошла ошибка",
                "status": "no_action_needed"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки кэша: {str(e)}"
        )

@router.get("/global/dominance")
async def get_dominance_data():

    try:
        result = await coinmarketcap_global_service.get_global_market_data()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Данные о доминировании временно недоступны"
            )
        
        return {
            "btc_dominance": result.market_cap.btc_dominance,
            "eth_dominance": result.market_cap.eth_dominance,
            "others_dominance": 100 - result.market_cap.btc_dominance - result.market_cap.eth_dominance,
            "defi_dominance": result.market_cap.defi_dominance,
            "stablecoin_dominance": result.market_cap.stablecoin_dominance,
            "last_updated": result.last_updated,
            "data_source": result.data_source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR][Dominance] - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения данных о доминировании"
        )

@router.get("/global/alt-season")
async def get_alt_season_only():

    try:
        result = await coinmarketcap_global_service.get_global_market_data()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Данные об альтсезоне временно недоступны"
            )
        
        return {
            "alt_season_index": result.alt_season.alt_season_index,
            "status": result.alt_season.status,
            "description": result.alt_season.description,
            "btc_dominance": result.alt_season.btc_dominance,
            "eth_dominance": result.alt_season.eth_dominance,
            "alt_dominance": result.alt_season.alt_dominance,
            "source": result.alt_season.source,
            "last_updated": result.last_updated,
            "data_source": result.data_source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR][AltSeason] - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения данных об альтсезоне"
        )

@router.get("/global/fear-greed")
async def get_fear_greed_only():

    try:
        result = await coinmarketcap_global_service.get_global_market_data()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Индекс страха и жадности временно недоступен"
            )
        

        return {
            "value": result.fear_greed_index.value,
            "value_classification": result.fear_greed_index.value_classification,
            "timestamp": result.fear_greed_index.timestamp,
            "time_until_update": result.fear_greed_index.time_until_update,
            "last_updated": result.last_updated,
            "data_source": result.data_source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR][FearGreed] - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения индекса страха и жадности"
        )