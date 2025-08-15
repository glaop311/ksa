from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal

class TokenSparkline(BaseModel):
    price: List[float] = Field(default_factory=list)


class TokenResponse(BaseModel):
    id: str
    symbol: str
    name: str
    image: str = ""
    current_price: float = 0.0
    market_cap: int = 0
    price_change_percentage_24h: float = 0.0
    price_change_percentage_7d: float = 0.0
    sparkline_in_7d: TokenSparkline = Field(default_factory=lambda: TokenSparkline(price=[]))
    is_halal: Optional[bool] = None
    is_layer_one: Optional[bool] = None
    is_stablecoin: Optional[bool] = None
    token_category: Optional[str] = None
    market_cap_rank: Optional[int] = None
    volume_24h: float = 0.0
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    is_favorite: bool = False



class HalalStatus(BaseModel):
    is_halal: Optional[bool] = None  
    verified: Optional[bool] = None
    halal_score: Optional[str] = None

class MarketData(BaseModel):
    market_cap_usd: int = Field(default=0)
    fully_diluted_valuation_usd: int = Field(default=0)
    total_volume_usd: int = Field(default=0)
    circulating_supply_value: Union[int, float] = Field(default=0)
    max_supply_value: Union[int, float] = Field(default=0)
    total_supply_value: Union[int, float] = Field(default=0)

class AllTimeHigh(BaseModel):
    price: float = 0.0
    date: str = ""

class AllTimeLow(BaseModel):
    price: float = 0.0
    date: str = ""

class PriceIndicators24h(BaseModel):
    min: float = 0.0
    max: float = 0.0

class Statistics(BaseModel):
    all_time_high: AllTimeHigh = Field(default_factory=AllTimeHigh)
    all_time_low: AllTimeLow = Field(default_factory=AllTimeLow)
    price_indicators_24h: PriceIndicators24h = Field(default_factory=PriceIndicators24h)

class TokenSocialLinks(BaseModel):
    website: Optional[str] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    reddit: Optional[str] = None
    instagram: Optional[str] = None
    discord: Optional[str] = None
    medium: Optional[str] = None
    youtube: Optional[str] = None
    repo_link: Optional[str] = None
    whitelabel_link: Optional[str] = None

class TokenAdditionalInfo(BaseModel):
    description: Optional[str] = None
    exchanges: List[str] = Field(default_factory=list)
    security_audits: List[str] = Field(default_factory=list)
    related_people: List[str] = Field(default_factory=list)
    related_wallets: List[str] = Field(default_factory=list, description="ID связанных кошельков")
    related_conductors: List[str] = Field(default_factory=list, description="ID связанных проводников")
    coingecko_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tvl: Optional[float] = None
    import_source: Optional[str] = None

class RelatedPerson(BaseModel):
    id: str = Field(..., description="Уникальный идентификатор")
    full_name: str = Field(..., description="Полное имя человека")
    avatar_image: Optional[str] = Field(None, description="Аватар человека")
    description: Optional[str] = Field(None, description="Описание человека")
    position: Optional[str] = Field(None, description="Должность или позиция")
    related_link: Optional[str] = Field(None, description="Ссылка на профиль")
    category: Optional[str] = Field(None, description="Категория человека")

class RelatedWallet(BaseModel):
    id: str = Field(..., description="Уникальный идентификатор кошелька")
    title: str = Field(..., description="Название кошелька")
    image: Optional[str] = Field(None, description="Изображение кошелька")
    url: Optional[str] = Field(None, description="URL кошелька")
    description: Optional[str] = Field(None, description="Описание кошелька")


class RelatedConductor(BaseModel):
    id: str = Field(..., description="Уникальный идентификатор проводника")
    title: str = Field(..., description="Название проводника")
    image: Optional[str] = Field(None, description="Изображение проводника")
    url: Optional[str] = Field(None, description="URL проводника")
    description: Optional[str] = Field(None, description="Описание проводника")

class RelatedSecurityAudit(BaseModel):
    id: str = Field(..., description="Уникальный идентификатор аудита")
    title: str = Field(..., description="Название аудита")
    auditor_name: str = Field(..., description="Имя аудитора")
    link: str = Field(..., description="Ссылка на отчет")
    audit_score: str = Field(..., description="Оценка аудита")

class TokenDetailResponse(BaseModel):
    id: str
    symbol: str
    name: str
    image: str = ""
    current_price: float = 0.0
    price_change_percentage_24h: float = 0.0
    halal_status: HalalStatus = Field(default_factory=lambda: HalalStatus(is_halal=None, verified=None))
    market_data: MarketData = Field(default_factory=MarketData)
    statistics: Statistics = Field(default_factory=Statistics)
    is_favorite: bool = False
    social_links: TokenSocialLinks = Field(default_factory=TokenSocialLinks)
    additional_info: TokenAdditionalInfo = Field(default_factory=TokenAdditionalInfo)
    approved: bool = False  
    class Config:
        extra = "allow"
    
    related_people_data: List[RelatedPerson] = Field(default_factory=list, description="Данные связанных людей")
    related_wallets_data: List[RelatedWallet] = Field(default_factory=list, description="Данные связанных кошельков")
    related_conductors_data: List[RelatedConductor] = Field(default_factory=list, description="Данные связанных проводников")
    related_security_audits_data: List[RelatedSecurityAudit] = Field(default_factory=list, description="Данные аудитов безопасности")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "bitcoin",
                "symbol": "BTC",
                "name": "Bitcoin",
                "image": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
                "current_price": 42145.32,
                "price_change_percentage_24h": 2.5,
                "halal_status": {
                    "is_halal": True,
                    "verified": True,
                    "halal_score": "82/100"
                },
                "market_data": {
                    "market_cap_usd": 825000000000,
                    "total_volume_usd": 25000000000
                },
                "social_links": {
                    "website": "https://bitcoin.org",
                    "twitter": "bitcoin"
                },
                "additional_info": {
                    "description": "Bitcoin is a decentralized digital currency",
                    "related_people": ["550e8400-e29b-41d4-a716-446655440000"],
                    "related_wallets": ["550e8400-e29b-41d4-a716-446655440001"],
                    "related_conductors": ["550e8400-e29b-41d4-a716-446655440002"]
                },
                "related_people_data": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "full_name": "Сатоши Накамото",
                        "position": "Создатель Bitcoin",
                        "description": "Псевдонимный создатель Bitcoin"
                    }
                ],
                "related_wallets_data": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "title": "MetaMask",
                        "image": "https://example.com/metamask.png",
                        "url": "https://metamask.io"
                    }
                ],
                "related_conductors_data": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440002",
                        "title": "Coinbase",
                        "image": "https://example.com/coinbase.png",
                        "url": "https://coinbase.com"
                    }
                ]
            }
        }

class Pagination(BaseModel):
    current_page: int = 1
    total_pages: int = 0
    total_items: int = 0
    items_per_page: int = 100

class TokenListResponse(BaseModel):
    data: List[TokenResponse] = Field(default_factory=list)
    pagination: Pagination = Field(default_factory=Pagination)

class TokenFilters(BaseModel):
    category: Optional[str] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_volume: Optional[float] = None
    max_volume: Optional[float] = None
    price_change_24h_min: Optional[float] = None
    price_change_24h_max: Optional[float] = None
    halal_only: bool = False
    favorites_only: bool = False

class SortOptions(BaseModel):
    sort_by: str = "market_cap"
    sort_order: str = "desc"

class TokenSearchRequest(BaseModel):
    query: str
    filters: Optional[TokenFilters] = None
    sort: Optional[SortOptions] = None
    limit: int = 20
    
class TokenFullStatsResponse(BaseModel):
    id: str
    symbol: str
    coin_name: str
    coingecko_id: str
    market_cap: Optional[float] = None
    trading_volume_24h: Optional[float] = None
    token_max_supply: Optional[int] = None
    token_total_supply: Optional[int] = None
    transactions_count_30d: Optional[int] = None
    volume_1m_change_1m: Optional[float] = None
    volume_24h_change_24h: Optional[float] = None
    price: Optional[float] = None
    ath: Optional[float] = None
    atl: Optional[float] = None
    liquidity_score: Optional[float] = None
    tvl: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_7d: Optional[float] = None
    price_change_30d: Optional[float] = None
    market_cap_rank: Optional[int] = None
    volume_rank: Optional[int] = None
    created_at: str
    updated_at: str

class ExchangeHalalStatus(BaseModel):
    is_halal: Optional[bool] = None
    score: str = ""
    rating: int = 0

class ExchangeResponse(BaseModel):
    rank: int = 0
    id: str
    name: str
    image: str = ""
    halal_status: ExchangeHalalStatus = Field(default_factory=lambda: ExchangeHalalStatus(is_halal=None))
    trust_score: int = 0
    volume_24h_usd: Union[int, float] = 0
    volume_24h_formatted: str = "$0"
    reserves_usd: Union[int, float] = 0
    reserves_formatted: str = "$0"
    trading_pairs_count: int = 0
    visitors_monthly: str = "0"
    supported_fiat: List[str] = Field(default_factory=list)
    supported_fiat_display: str = ""
    volume_chart_7d: List[Union[int, float]] = Field(default_factory=list)
    exchange_type: str = "centralized"

class ExchangeDetailResponse(BaseModel):
    id: str
    name: str
    image: str = ""
    halal_status: ExchangeHalalStatus = Field(default_factory=lambda: ExchangeHalalStatus(is_halal=None))
    trust_score: int = 0
    volume_24h_usd: Union[int, float] = 0
    total_assets_usd: Union[int, float] = 0
    trading_pairs_count: int = 0
    visitors_monthly: str = "0"
    website_url: str = ""
    supported_fiat: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    year_established: Optional[int] = None

class ExchangeListResponse(BaseModel):
    data: List[ExchangeResponse] = Field(default_factory=list)

class TokenDataConverter(BaseModel):
    @staticmethod
    def from_db_to_api(token_stats: Dict[str, Any], token: Dict[str, Any] = None, is_favorite: bool = False) -> TokenResponse:
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
        
        def safe_bool(value):
            if value is None:
                return None
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        
        sparkline_data = token_stats.get('sparkline_7d', [])
        if not isinstance(sparkline_data, list):
            sparkline_data = []
        
        symbol = str(token_stats.get('symbol', '')).upper()
        name = str(token_stats.get('coin_name', '')).lower()
        
        token_category = token_stats.get('token_category') or (token.get('token_category') if token else None)
        if not token_category:
            if symbol in ['USDT', 'USDC', 'DAI', 'BUSD', 'FRAX', 'TUSD']:
                token_category = "stablecoin"
            elif symbol in ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'AVAX', 'MATIC', 'DOT', 'ATOM']:
                token_category = "layer1"
            elif 'layer' in name or 'l2' in name:
                token_category = "layer2"
            elif any(word in name for word in ['defi', 'swap', 'finance', 'lending']):
                token_category = "defi"
            elif any(word in name for word in ['meme', 'doge', 'shib', 'pepe']):
                token_category = "meme"
            else:
                token_category = "other"
        
        return TokenResponse(
            id=token_stats.get('coingecko_id', token_stats.get('symbol', 'unknown')),
            symbol=str(token_stats.get('symbol', 'UNKNOWN')).upper(),
            name=str(token_stats.get('coin_name', 'Unknown Token')),
            image=token.get('avatar_image', '') if token else '',
            current_price=safe_float(token_stats.get('price')),
            market_cap=safe_int(token_stats.get('market_cap')),
            price_change_percentage_24h=safe_float(token_stats.get('volume_24h_change_24h')),
            price_change_percentage_7d=safe_float(token_stats.get('price_change_percentage_7d')),
            sparkline_in_7d=TokenSparkline(price=sparkline_data),
            is_halal=safe_bool(token_stats.get('is_halal') or (token.get('is_halal') if token else None)),
            is_layer_one=token_category == "layer1",
            is_stablecoin=token_category == "stablecoin",
            token_category=token_category,
            market_cap_rank=safe_int(token_stats.get('market_cap_rank')),
            volume_24h=safe_float(token_stats.get('trading_volume_24h')),
            total_supply=safe_float(token_stats.get('token_total_supply')),
            max_supply=safe_float(token_stats.get('token_max_supply')),
            is_favorite=is_favorite  
        )