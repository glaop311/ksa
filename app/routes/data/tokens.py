from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, List
from enum import Enum

from app.services.market.market_service import market_service
from app.schemas.market import RelatedConductor, RelatedSecurityAudit, RelatedWallet, TokenListResponse, TokenDetailResponse, TokenFullStatsResponse, RelatedPerson
from app.schemas.chart import TokenChartResponse
from app.services.market.coingecko_service import coingecko_service
from app.core.database.connector import get_generic_repository
from app.core.security.security import get_current_user_optional
from app.core.database.crud.user import get_user_favorite_tokens

router = APIRouter()

class TokenCategory(str, Enum):
    all = "all"
    favorites = "favorites"
    layer1 = "layer1"
    layer2 = "layer2"
    stablecoin = "stablecoin"
    defi = "defi"
    meme = "meme"
    gaming = "gaming"
    nft = "nft"
    metaverse = "metaverse"
    web3 = "web3"
    infrastructure = "infrastructure"
    dao = "dao"
    privacy = "privacy"
    other = "other"

class SortBy(str, Enum):
    market_cap = "market_cap"
    volume = "volume"
    price = "price"
    price_change_24h = "price_change_24h"
    price_change_7d = "price_change_7d"
    market_cap_rank = "market_cap_rank"
    alphabetical = "alphabetical"
    halal = "halal"
    favorites = "favorites"
    newest = "newest"
    oldest = "oldest"

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

class TimeframeEnum(str, Enum):
    one_hour = "1h"
    twenty_four_hours = "24h"
    seven_days = "7d"
    thirty_days = "30d"
    ninety_days = "90d"
    one_year = "1y"
    max = "max"

class Language(str, Enum):
    en = "en"
    ru = "ru"
    uz = "uz"

async def _get_people_data_for_token(related_people_ids: List[str]) -> List[RelatedPerson]:
    if not related_people_ids:
        return []
    
    try:
        people_repo = get_generic_repository("LiberandumApiPeople")
        people_data = []
        
        for person_id in related_people_ids:
            person = people_repo.get_by_id(person_id)
            if person and not person.get('is_deleted', False):
                people_data.append(RelatedPerson(
                    id=person['id'],
                    full_name=person.get('full_name', ''),
                    avatar_image=person.get('avatar_image'),
                    description=person.get('description'),
                    position=person.get('position'),
                    related_link=person.get('related_link')
                ))
        
        return people_data
    except Exception as e:
        print(f"[ERROR] Failed to get people data: {e}")
        return []

@router.get("/", response_model=TokenListResponse)
async def get_tokens_list(
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    limit: int = Query(default=100, ge=1, le=250, description="Элементов на странице"),
    category: TokenCategory = Query(default=TokenCategory.all, description="Категория токенов"),
    sort_by: SortBy = Query(default=SortBy.market_cap, description="Поле для сортировки"),
    sort_order: SortOrder = Query(default=SortOrder.desc, description="Порядок сортировки"),
    min_market_cap: Optional[float] = Query(default=None, description="Минимальная рыночная капитализация"),
    max_market_cap: Optional[float] = Query(default=None, description="Максимальная рыночная капитализация"),
    min_price: Optional[float] = Query(default=None, description="Минимальная цена"),
    max_price: Optional[float] = Query(default=None, description="Максимальная цена"),
    min_volume: Optional[float] = Query(default=None, description="Минимальный объем торгов 24ч"),
    max_volume: Optional[float] = Query(default=None, description="Максимальный объем торгов 24ч"),
    price_change_24h_min: Optional[float] = Query(default=None, description="Минимальное изменение цены за 24ч (%)"),
    price_change_24h_max: Optional[float] = Query(default=None, description="Максимальное изменение цены за 24ч (%)"),
    halal_only: bool = Query(default=False, description="Только халяльные токены"),
    favorites_only: bool = Query(default=False, description="Только избранные токены"),
    current_user = Depends(get_current_user_optional)
):
    try:
        user_favorites = []
        if current_user and (favorites_only or sort_by == SortBy.favorites or category == TokenCategory.favorites):
            user_favorites = get_user_favorite_tokens(current_user['id'])
            
            if (favorites_only or category == TokenCategory.favorites) and not user_favorites:
                return TokenListResponse(
                    data=[],
                    pagination={
                        "current_page": page,
                        "total_pages": 0,
                        "total_items": 0,
                        "items_per_page": limit
                    }
                )
        
        result = market_service.get_tokens_list_enhanced(
            page=page, 
            limit=limit, 
            category=category.value,
            sort_by=sort_by.value,
            sort_order=sort_order.value,
            min_market_cap=min_market_cap,
            max_market_cap=max_market_cap,
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume,
            max_volume=max_volume,
            price_change_24h_min=price_change_24h_min,
            price_change_24h_max=price_change_24h_max,
            halal_only=halal_only,
            favorites_only=favorites_only or category == TokenCategory.favorites,
            user_favorites=user_favorites
        )
        
        return result
        
    except Exception as e:
        print(f"[ERROR][Market] - Ошибка получения списка токенов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения списка токенов"
        )

@router.get("/search", response_model=TokenListResponse)
async def search_tokens(
    q: str = Query(..., min_length=1, description="Название или символ токена"),
    limit: int = Query(default=20, ge=1, le=100, description="Количество результатов"),
    category: TokenCategory = Query(default=TokenCategory.all, description="Фильтр по категории"),
    sort_by: SortBy = Query(default=SortBy.market_cap, description="Тип сортировки результатов"),
    halal_only: bool = Query(default=False, description="Только халяльные токены"),
    current_user = Depends(get_current_user_optional)
):
    try:
        user_favorites = []
        if current_user:
            user_favorites = get_user_favorite_tokens(current_user['id'])
        
        result = market_service.search_tokens_enhanced(
            query=q,
            limit=limit,
            category=category.value,
            sort_by=sort_by.value,
            halal_only=halal_only,
            user_favorites=user_favorites
        )
        
        return result
        
    except Exception as e:
        print(f"[ERROR][Market] - Ошибка поиска токенов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка поиска токенов"
        )

@router.get("/{token_id}/stats", response_model=TokenFullStatsResponse)
async def get_token_full_stats(token_id: str):
    try:
        result = market_service.get_token_full_stats(token_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статистика для токена '{token_id}' не найдена"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR][Market] - Ошибка получения полной статистики токена {token_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики токена"
        )

@router.get("/{token_id}", response_model=TokenDetailResponse)
async def get_token_detail(
    token_id: str,
    lang: Language = Query(default=Language.en, description="Язык отображения"),
    current_user = Depends(get_current_user_optional)
):

    try:
        result = market_service.get_token_detail(token_id, lang.value)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Токен не найден"
            )
        

        if current_user:
            user_favorites = get_user_favorite_tokens(current_user['id'])
            result.is_favorite = token_id in user_favorites
        

        if result.additional_info:

            related_people_ids = result.additional_info.related_people if result.additional_info.related_people else []
            people_data = await _get_people_data_for_token(related_people_ids)
            result.related_people_data = people_data
            

            related_wallet_ids = []
            if hasattr(result.additional_info, 'related_wallets') and result.additional_info.related_wallets:
                related_wallet_ids = result.additional_info.related_wallets
            elif result.additional_info and 'related_wallets_data' in result.additional_info.__dict__:
                related_wallet_ids = result.additional_info.related_wallets_data or []
            wallets_data = await _get_wallets_data_for_token(related_wallet_ids)
            result.related_wallets_data = wallets_data
            

            related_conductor_ids = []
            if hasattr(result.additional_info, 'related_conductors') and result.additional_info.related_conductors:
                related_conductor_ids = result.additional_info.related_conductors
            elif result.additional_info and 'related_conductors_data' in result.additional_info.__dict__:
                related_conductor_ids = result.additional_info.related_conductors_data or []
            conductors_data = await _get_conductors_data_for_token(related_conductor_ids)
            result.related_conductors_data = conductors_data
            
            security_audit_ids = result.additional_info.security_audits if result.additional_info.security_audits else []
            audits_data = await _get_security_audits_data_for_token(security_audit_ids)
            result.related_security_audits_data = audits_data
        else:

            result.related_people_data = []
            result.related_wallets_data = []
            result.related_conductors_data = []
            result.related_security_audits_data = []
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR][Market] - Ошибка получения токена {token_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения информации о токене"
        )
    

@router.get("/{token_id}/chart", response_model=TokenChartResponse)
async def get_token_chart(
    token_id: str,
    timeframe: TimeframeEnum = Query(..., description="Timeframe for chart data"),
    currency: str = Query("usd", description="Currency for price data"),
):
    try:
        coingecko_id = _resolve_coingecko_id(token_id)
        
        chart_data = await coingecko_service.get_token_chart_data(
            token_id=coingecko_id,
            timeframe=timeframe.value,
            currency=currency
        )
        
        if not chart_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Chart data not found for token: {token_id}"
            )
            
        return TokenChartResponse(**chart_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting chart for token {token_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error while fetching chart data"
        )

def _resolve_coingecko_id(token_id: str) -> str:
    token_stats_repo = market_service._get_repository(market_service.token_stats_table)
    
    coingecko_id = token_id.lower()
    if token_id.upper() == "BTC":
        coingecko_id = "bitcoin"
    elif token_id.upper() == "ETH":
        coingecko_id = "ethereum"
    elif token_id.lower() == "bitcoin":
        coingecko_id = "bitcoin"
    else:
        token_stats_results = token_stats_repo.find_by_field('symbol', token_id.upper())
        if token_stats_results:
            unique_stats = market_service._remove_duplicates_by_symbol(token_stats_results)
            if unique_stats:
                coingecko_id = unique_stats[0].get('coingecko_id', token_id.lower())
        else:
            token_stats_results = token_stats_repo.find_by_field('coingecko_id', token_id.lower())
            if token_stats_results:
                unique_stats = market_service._remove_duplicates_by_symbol(token_stats_results)
                if unique_stats:
                    coingecko_id = unique_stats[0].get('coingecko_id', token_id.lower())
    
    return coingecko_id



async def _get_people_data_for_token(related_people_ids: List[str]) -> List[RelatedPerson]:

    if not related_people_ids:
        return []
    
    try:
        people_repo = get_generic_repository("LiberandumApiPeople")
        people_data = []
        
        for person_id in related_people_ids:
            person = people_repo.get_by_id(person_id)
            if person and not person.get('is_deleted', False):
                people_data.append(RelatedPerson(
                    id=person['id'],
                    full_name=person.get('full_name', ''),
                    avatar_image=person.get('avatar_image'),
                    description=person.get('description'),
                    position=person.get('position'),
                    related_link=person.get('related_link')
                ))
        
        return people_data
    except Exception as e:
        print(f"[ERROR] Failed to get people data: {e}")
        return []

async def _get_wallets_data_for_token(related_wallet_ids: List[str]) -> List[RelatedWallet]:

    if not related_wallet_ids:
        return []
    
    try:
        wallets_repo = get_generic_repository("LiberandumApiWallets")
        wallets_data = []
        
        for wallet_id in related_wallet_ids:
            wallet = wallets_repo.get_by_id(wallet_id)
            if wallet and not wallet.get('is_deleted', False):
                wallets_data.append(RelatedWallet(
                    id=wallet['id'],
                    title=wallet.get('title', ''),
                    image=wallet.get('image'),
                    url=wallet.get('url')
                ))
        
        return wallets_data
    except Exception as e:
        print(f"[ERROR] Failed to get wallets data: {e}")
        return []

async def _get_conductors_data_for_token(related_conductor_ids: List[str]) -> List[RelatedConductor]:

    if not related_conductor_ids:
        return []
    
    try:
        conductors_repo = get_generic_repository("LiberandumApiConductors")
        conductors_data = []
        
        for conductor_id in related_conductor_ids:
            conductor = conductors_repo.get_by_id(conductor_id)
            if conductor and not conductor.get('is_deleted', False):
                conductors_data.append(RelatedConductor(
                    id=conductor['id'],
                    title=conductor.get('title', ''),
                    image=conductor.get('image'),
                    url=conductor.get('url')
                ))
        
        return conductors_data
    except Exception as e:
        print(f"[ERROR] Failed to get conductors data: {e}")
        return []

async def _get_security_audits_data_for_token(security_audit_ids: List[str]) -> List[RelatedSecurityAudit]:

    if not security_audit_ids:
        return []
    
    try:
        audits_repo = get_generic_repository("LiberandumApiSecurityAudit")
        audits_data = []
        
        for audit_id in security_audit_ids:
            audit = audits_repo.get_by_id(audit_id)
            if audit and not audit.get('is_deleted', False):
                audits_data.append(RelatedSecurityAudit(
                    id=audit['id'],
                    title=audit.get('title', ''),
                    auditor_name=audit.get('auditor_name', ''),
                    link=audit.get('link', ''),
                    audit_score=audit.get('audit_score', '')
                ))
        
        return audits_data
    except Exception as e:
        print(f"[ERROR] Failed to get security audits data: {e}")
        return []
