from typing import List, Optional, Dict, Any, Set
from datetime import datetime

from app.core.database.connector import get_generic_repository
from app.schemas.market import (
    TokenAdditionalInfo, TokenResponse, TokenDetailResponse, TokenListResponse, TokenFullStatsResponse,
    ExchangeListResponse, TokenSocialLinks, TokenSparkline,
    HalalStatus, MarketData, Statistics, AllTimeHigh, AllTimeLow, PriceIndicators24h
)

class MarketDataService:
    def __init__(self):
        self.token_stats_table = "LiberandumAggregationTokenStats"
        self.tokens_table = "LiberandumAggregationToken"
        self.exchange_stats_table = "LiberandumAggregationExchangesStats"
        self.exchanges_table = "LiberandumAggregationExchanges"

    def _get_repository(self, table_name: str):
        repo = get_generic_repository(table_name)
        if not repo:
            raise RuntimeError(f"Репозиторий для таблицы {table_name} недоступен")
        return repo

    def _remove_duplicates_by_symbol(self, token_stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_symbols: Set[str] = set()
        unique_tokens = []
        
        sorted_tokens = sorted(
            token_stats, 
            key=lambda x: x.get('updated_at', ''), 
            reverse=True
        )
        
        for token in sorted_tokens:
            symbol = token.get('symbol', '').upper()
            if symbol and symbol not in seen_symbols:
                seen_symbols.add(symbol)
                unique_tokens.append(token)
        
        return unique_tokens

    def _filter_approved_tokens(self, token_stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [token for token in token_stats if token.get('approved', False)]
  
    def get_tokens_list_enhanced(
        self, 
        page: int = 1, 
        limit: int = 100, 
        category: str = "all",
        sort_by: str = "market_cap",
        sort_order: str = "desc",
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_volume: Optional[float] = None,
        max_volume: Optional[float] = None,
        price_change_24h_min: Optional[float] = None,
        price_change_24h_max: Optional[float] = None,
        halal_only: bool = False,
        favorites_only: bool = False,
        user_favorites: List[str] = None
    ) -> TokenListResponse:
        try:
            token_stats_repo = self._get_repository(self.token_stats_table)
            tokens_repo = self._get_repository(self.tokens_table)
            
            if user_favorites is None:
                user_favorites = []
            
            scan_limit = min(limit * 5, 2000)
            all_token_stats = token_stats_repo.scan_items(self.token_stats_table, limit=scan_limit)
            
            active_token_stats = [ts for ts in all_token_stats if not ts.get('is_deleted', False)]
            approved_token_stats = self._filter_approved_tokens(active_token_stats)
            unique_token_stats = self._remove_duplicates_by_symbol(approved_token_stats)
            
            all_tokens = tokens_repo.scan_items(self.tokens_table, limit=2000)
            tokens_by_symbol = {}
            for token in all_tokens:
                if not token.get('is_deleted', False):
                    symbol = token.get('symbol', '').upper()
                    if symbol:
                        tokens_by_symbol[symbol] = token
            
            filtered_stats = self._apply_filters(
                unique_token_stats,
                tokens_by_symbol,
                category=category,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap,
                min_price=min_price,
                max_price=max_price,
                min_volume=min_volume,
                max_volume=max_volume,
                price_change_24h_min=price_change_24h_min,
                price_change_24h_max=price_change_24h_max,
                halal_only=halal_only,
                favorites_only=favorites_only,
                user_favorites=user_favorites
            )
            
            sorted_stats = self._apply_sorting_enhanced(
                filtered_stats, 
                sort_by, 
                sort_order, 
                user_favorites
            )
            
            total_items = len(sorted_stats)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_stats = sorted_stats[start_idx:end_idx]
            
            token_responses = []
            for stat in paginated_stats:
                try:
                    symbol = stat.get('symbol', '').upper()
                    token_data = tokens_by_symbol.get(symbol)
                    token_response = self._convert_token_stats_to_response(stat, token_data)
                    
                    token_response.is_favorite = token_response.id in user_favorites
                    
                    token_responses.append(token_response)
                except Exception as e:
                    print(f"[ERROR] Ошибка конвертации токена: {e}")
                    continue
            
            pagination = {
                "current_page": page,
                "total_pages": (total_items + limit - 1) // limit if total_items > 0 else 0,
                "total_items": total_items,
                "items_per_page": limit
            }
            
            return TokenListResponse(data=token_responses, pagination=pagination)
            
        except Exception as e:
            print(f"[ERROR] Критическая ошибка в get_tokens_list_enhanced: {e}")
            return TokenListResponse(
                data=[], 
                pagination={"current_page": 1, "total_pages": 0, "total_items": 0, "items_per_page": limit}
            )
     
    def search_tokens_enhanced(
        self,
        query: str,
        limit: int = 20,
        category: str = "all",
        sort_by: str = "market_cap", 
        halal_only: bool = False,
        user_favorites: List[str] = None
    ) -> TokenListResponse:
        try:
            if user_favorites is None:
                user_favorites = []
                
            token_stats_repo = self._get_repository(self.token_stats_table)
            tokens_repo = self._get_repository(self.tokens_table)
            
            all_token_stats = token_stats_repo.list_all(limit=1000)
            all_tokens = tokens_repo.list_all(limit=1000)
            
            approved_token_stats = self._filter_approved_tokens(all_token_stats)
            unique_stats = self._remove_duplicates_by_symbol(approved_token_stats)
            
            tokens_by_symbol = {}
            for token in all_tokens:
                if not token.get('is_deleted', False):
                    symbol = token.get('symbol', '').upper()
                    if symbol:
                        tokens_by_symbol[symbol] = token
            
            query_lower = query.lower().strip()
            matching_stats = []
            
            for stat in unique_stats:
                if stat.get('is_deleted', False):
                    continue
                    
                name = stat.get('coin_name', '').lower()
                symbol = stat.get('symbol', '').lower()
                coingecko_id = stat.get('coingecko_id', '').lower()
                
                if (query_lower in name or 
                    query_lower in symbol or 
                    query_lower in coingecko_id or
                    symbol == query_lower or
                    name.startswith(query_lower)):
                    matching_stats.append(stat)
            
            filtered_stats = self._apply_filters(
                matching_stats,
                tokens_by_symbol,
                category=category,
                halal_only=halal_only
            )
            
            sorted_stats = self._apply_sorting_enhanced(filtered_stats, sort_by, "desc", user_favorites)
            
            limited_stats = sorted_stats[:limit]
            
            results = []
            for stat in limited_stats:
                try:
                    symbol = stat.get('symbol', '').upper()
                    token_data = tokens_by_symbol.get(symbol)
                    token_response = self._convert_token_stats_to_response(stat, token_data)
                    token_response.is_favorite = token_response.id in user_favorites
                    results.append(token_response)
                except Exception as e:
                    print(f"[ERROR] Ошибка конвертации в поиске: {e}")
                    continue
            
            return TokenListResponse(
                data=results,
                pagination={
                    "current_page": 1,
                    "total_pages": 1,
                    "total_items": len(results),
                    "items_per_page": limit
                }
            )
            
        except Exception as e:
            print(f"[ERROR] Ошибка расширенного поиска токенов: {e}")
            return TokenListResponse(data=[], pagination={})
    
    def _apply_filters(
        self,
        token_stats: List[Dict[str, Any]], 
        tokens_by_symbol: Dict[str, Any],
        category: str = "all",
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_volume: Optional[float] = None,
        max_volume: Optional[float] = None,
        price_change_24h_min: Optional[float] = None,
        price_change_24h_max: Optional[float] = None,
        halal_only: bool = False,
        favorites_only: bool = False,
        user_favorites: List[str] = None
    ) -> List[Dict[str, Any]]:
        
        def safe_float(value, default=0.0):
            try:
                return float(str(value or 0).replace(',', ''))
            except:
                return default
        
        def safe_bool(value, default=False):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        
        def get_token_category(token_stat, token_data):
            if token_data and token_data.get('token_category'):
                return token_data['token_category']
            
            symbol = str(token_stat.get('symbol', '')).upper()
            name = str(token_stat.get('coin_name', '')).lower()
            
            if symbol in ['USDT', 'USDC', 'DAI', 'BUSD', 'FRAX', 'TUSD', 'FDUSD', 'LUSD', 'sUSD']:
                return "stablecoin"
            elif symbol in ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'AVAX', 'MATIC', 'DOT', 'ATOM', 'NEAR', 'FTM', 'ALGO', 'HBAR', 'XTZ']:
                return "layer1"
            elif symbol in ['ARB', 'OP', 'LRC', 'IMX', 'METIS'] or any(word in name for word in ['layer 2', 'l2', 'arbitrum', 'optimism', 'polygon']):
                return "layer2"
            elif any(word in name for word in ['defi', 'swap', 'finance', 'lending', 'protocol', 'yield', 'liquidity']):
                return "defi"
            elif any(word in name for word in ['meme', 'doge', 'shib', 'pepe', 'floki', 'wojak']):
                return "meme"
            elif any(word in name for word in ['game', 'gaming', 'play', 'metaverse', 'virtual']):
                return "gaming"
            elif any(word in name for word in ['nft', 'collectible', 'art', 'token']):
                return "nft"
            elif any(word in name for word in ['metaverse', 'virtual reality', 'vr', 'ar', 'augmented']):
                return "metaverse"
            elif any(word in name for word in ['web3', 'decentralized', 'infrastructure', 'protocol']):
                return "web3"
            elif any(word in name for word in ['dao', 'governance', 'voting']):
                return "dao"
            elif any(word in name for word in ['privacy', 'anonymous', 'private', 'confidential']):
                return "privacy"
            elif any(word in name for word in ['oracle', 'data', 'network', 'node', 'validator']):
                return "infrastructure"
            else:
                return "other"
        
        if user_favorites is None:
            user_favorites = []
        
        filtered = []
        
        for stat in token_stats:
            if category != "all" and category != "favorites":
                symbol = stat.get('symbol', '').upper()
                token_data = tokens_by_symbol.get(symbol)
                token_category = get_token_category(stat, token_data)
                if token_category != category:
                    continue
            
            if category == "favorites":
                token_id = stat.get('coingecko_id', stat.get('symbol', '')).lower()
                if token_id not in user_favorites:
                    continue
            
            market_cap = safe_float(stat.get('market_cap'))
            if min_market_cap is not None and market_cap < min_market_cap:
                continue
            if max_market_cap is not None and market_cap > max_market_cap:
                continue
            
            price = safe_float(stat.get('price'))
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            
            volume = safe_float(stat.get('trading_volume_24h'))
            if min_volume is not None and volume < min_volume:
                continue
            if max_volume is not None and volume > max_volume:
                continue
            
            price_change = safe_float(stat.get('volume_24h_change_24h'))
            if price_change_24h_min is not None and price_change < price_change_24h_min:
                continue
            if price_change_24h_max is not None and price_change > price_change_24h_max:
                continue
            
            if halal_only:
                is_halal = safe_bool(stat.get('is_halal'))
                if not is_halal:
                    continue

            if favorites_only:
                token_id = stat.get('coingecko_id', stat.get('symbol', '')).lower()
                if token_id not in user_favorites:
                    continue
            
            filtered.append(stat)
        
        return filtered
    
    def _apply_sorting_enhanced(
        self, 
        token_stats: List[Dict[str, Any]], 
        sort_by: str, 
        sort_order: str = "desc",
        user_favorites: List[str] = None
    ) -> List[Dict[str, Any]]:
        
        def safe_float(value, default=0.0):
            try:
                return float(str(value or 0).replace(',', ''))
            except:
                return default
        
        def safe_int(value, default=0):
            try:
                return int(float(str(value or 0).replace(',', '')))
            except:
                return default
        
        def safe_bool(value, default=False):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        
        def safe_date(value, default=""):
            try:
                return str(value or default)
            except:
                return default
        
        if user_favorites is None:
            user_favorites = []
        
        reverse_sort = sort_order == "desc"
        
        if sort_by == "market_cap":
            return sorted(token_stats, 
                         key=lambda x: safe_float(x.get('market_cap')), 
                         reverse=reverse_sort)
        
        elif sort_by == "volume":
            return sorted(token_stats, 
                         key=lambda x: safe_float(x.get('trading_volume_24h')), 
                         reverse=reverse_sort)
        
        elif sort_by == "price":
            return sorted(token_stats, 
                         key=lambda x: safe_float(x.get('price')), 
                         reverse=reverse_sort)
        
        elif sort_by == "price_change_24h":
            return sorted(token_stats, 
                         key=lambda x: safe_float(x.get('volume_24h_change_24h')), 
                         reverse=reverse_sort)
        
        elif sort_by == "price_change_7d":
            return sorted(token_stats, 
                         key=lambda x: safe_float(x.get('price_change_7d')), 
                         reverse=reverse_sort)
        
        elif sort_by == "market_cap_rank":
            return sorted(token_stats, 
                         key=lambda x: safe_int(x.get('market_cap_rank'), 999999), 
                         reverse=not reverse_sort) 
        
        elif sort_by == "alphabetical":
            return sorted(token_stats, 
                         key=lambda x: str(x.get('symbol', '')).upper(), 
                         reverse=reverse_sort)
        
        elif sort_by == "halal":
            return sorted(token_stats, 
                         key=lambda x: (safe_bool(x.get('is_halal'), False), safe_float(x.get('market_cap'))), 
                         reverse=reverse_sort)
        
        elif sort_by == "favorites":
            def favorite_sort_key(x):
                token_id = x.get('coingecko_id', x.get('symbol', '')).lower()
                is_favorite = token_id in user_favorites
                market_cap = safe_float(x.get('market_cap'))
                return (is_favorite, market_cap)
            
            return sorted(token_stats, key=favorite_sort_key, reverse=reverse_sort)
        
        elif sort_by == "newest":
            return sorted(token_stats, 
                         key=lambda x: safe_date(x.get('created_at')), 
                         reverse=reverse_sort)
        
        elif sort_by == "oldest":
            return sorted(token_stats, 
                         key=lambda x: safe_date(x.get('created_at')), 
                         reverse=not reverse_sort)
        
        else:
            return sorted(token_stats, 
                         key=lambda x: (safe_int(x.get('market_cap_rank'), 999999), -safe_float(x.get('market_cap'))),
                         reverse=reverse_sort)
    
    def get_token_full_stats(self, symbol_or_id: str) -> Optional[TokenFullStatsResponse]:
        try:
            token_stats_repo = self._get_repository(self.token_stats_table)
            
            token_stats_by_symbol = token_stats_repo.find_by_field('symbol', symbol_or_id.upper())
            
            if not token_stats_by_symbol:
                token_stats_by_coingecko = token_stats_repo.find_by_field('coingecko_id', symbol_or_id.lower())
                if not token_stats_by_coingecko:
                    return None
                token_stats = token_stats_by_coingecko
            else:
                token_stats = token_stats_by_symbol
            
            approved_stats = self._filter_approved_tokens(token_stats)
            unique_stats = self._remove_duplicates_by_symbol(approved_stats)
            if not unique_stats:
                return None
            
            latest_stats = unique_stats[0]
            
            def safe_float(value, default=None):
                try:
                    return float(str(value or 0).replace(',', '')) if value is not None else default
                except:
                    return default
            
            def safe_int(value, default=None):
                try:
                    return int(float(str(value or 0).replace(',', ''))) if value is not None else default
                except:
                    return default
            
            return TokenFullStatsResponse(
                id=latest_stats.get('id', ''),
                symbol=latest_stats.get('symbol', ''),
                coin_name=latest_stats.get('coin_name', ''),
                coingecko_id=latest_stats.get('coingecko_id', ''),
                market_cap=safe_float(latest_stats.get('market_cap')),
                trading_volume_24h=safe_float(latest_stats.get('trading_volume_24h')),
                token_max_supply=safe_int(latest_stats.get('token_max_supply')),
                token_total_supply=safe_int(latest_stats.get('token_total_supply')),
                transactions_count_30d=safe_int(latest_stats.get('transactions_count_30d')),
                volume_1m_change_1m=safe_float(latest_stats.get('volume_1m_change_1m')),
                volume_24h_change_24h=safe_float(latest_stats.get('volume_24h_change_24h')),
                price=safe_float(latest_stats.get('price')),
                ath=safe_float(latest_stats.get('ath')),
                atl=safe_float(latest_stats.get('atl')),
                liquidity_score=safe_float(latest_stats.get('liquidity_score')),
                tvl=safe_float(latest_stats.get('tvl')),
                price_change_24h=safe_float(latest_stats.get('price_change_24h')),
                price_change_7d=safe_float(latest_stats.get('price_change_7d')),
                price_change_30d=safe_float(latest_stats.get('price_change_30d')),
                market_cap_rank=safe_int(latest_stats.get('market_cap_rank')),
                volume_rank=safe_int(latest_stats.get('volume_rank')),
                created_at=latest_stats.get('created_at', ''),
                updated_at=latest_stats.get('updated_at', '')
            )
            
        except Exception as e:
            print(f"[ERROR][MarketService] - Ошибка получения полной статистики токена {symbol_or_id}: {e}")
            return None
    
    def _convert_token_stats_to_response(self, token_stats: Dict[str, Any], token_data: Dict[str, Any] = None) -> TokenResponse:
        def safe_float(value, default=0.0):
            try:
                return float(str(value or 0).replace(',', ''))
            except:
                return default
        
        def safe_int(value, default=0):
            try:
                return int(float(str(value or 0).replace(',', '')))
            except:
                return default
        
        def safe_bool(value, default=None):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        
        def get_token_category(token_stat, token):
            if token and token.get('token_category'):
                return token['token_category']
            
            symbol = str(token_stat.get('symbol', '')).upper()
            name = str(token_stat.get('coin_name', '')).lower()
            
            if symbol in ['USDT', 'USDC', 'DAI', 'BUSD', 'FRAX', 'TUSD', 'FDUSD']:
                return "stablecoin"
            elif symbol in ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'AVAX', 'MATIC', 'DOT', 'ATOM', 'NEAR', 'FTM']:
                return "layer1"
            elif 'layer' in name or 'l2' in name or symbol in ['ARB', 'OP', 'MATIC']:
                return "layer2"
            elif any(word in name for word in ['defi', 'swap', 'finance', 'lending', 'protocol']):
                return "defi"
            elif any(word in name for word in ['meme', 'doge', 'shib', 'pepe', 'floki']):
                return "meme"
            else:
                return "other"
        
        sparkline_data = token_stats.get('sparkline_7d', [])
        if not isinstance(sparkline_data, list):
            sparkline_data = []
        
        token_category = get_token_category(token_stats, token_data)
        
        return TokenResponse(
            id=str(token_stats.get('coingecko_id', token_stats.get('symbol', 'unknown'))).lower(),
            symbol=str(token_stats.get('symbol', 'UNKNOWN')).upper(),
            name=str(token_stats.get('coin_name', 'Unknown Token')),
            image=token_data.get('avatar_image', '') if token_data else '',
            current_price=safe_float(token_stats.get('price')),
            market_cap=safe_int(token_stats.get('market_cap')),
            price_change_percentage_24h=safe_float(token_stats.get('volume_24h_change_24h')),
            price_change_percentage_7d=safe_float(token_stats.get('price_change_percentage_7d')),
            sparkline_in_7d=TokenSparkline(price=sparkline_data),
            is_halal=safe_bool(token_stats.get('is_halal') or (token_data.get('is_halal') if token_data else None)),
            is_layer_one=token_category == "layer1",
            is_stablecoin=token_category == "stablecoin",
            token_category=token_category,
            market_cap_rank=safe_int(token_stats.get('market_cap_rank')),
            volume_24h=safe_float(token_stats.get('trading_volume_24h')),
            total_supply=safe_float(token_stats.get('token_total_supply')),
            max_supply=safe_float(token_stats.get('token_max_supply'))
        )

    def _get_localized_description(self, token: Dict[str, Any], language: str) -> str:
        if language == "ru":
            return token.get('description_ru') or token.get('description', '')
        elif language == "uz":
            return token.get('description_uz') or token.get('description', '')
        else:
            return token.get('description', '')
    def get_token_detail(self, token_id: str, language: str = "en") -> Optional[TokenDetailResponse]:
            try:
                token_stats_repo = self._get_repository(self.token_stats_table)
                tokens_repo = self._get_repository(self.tokens_table)
                
                token_stats_results = token_stats_repo.find_by_field('coingecko_id', token_id)
                if not token_stats_results:
                    token_stats_results = token_stats_repo.find_by_field('symbol', token_id.upper())
                
                if not token_stats_results:
                    return None
                
                approved_stats = self._filter_approved_tokens(token_stats_results)
                unique_stats = self._remove_duplicates_by_symbol(approved_stats)
                if not unique_stats:
                    return None
                
                token_stats = unique_stats[0]
                
                token = None
                if token_stats.get('symbol'):
                    token_results = tokens_repo.find_by_field('symbol', token_stats['symbol'])
                    if token_results:
                        for t in token_results:
                            if not t.get('is_deleted', False):
                                token = t
                                break
                            
                if not token and token_stats.get('coingecko_id'):
                    token_results = tokens_repo.find_by_field('coingecko_id', token_stats['coingecko_id'])
                    if token_results:
                        for t in token_results:
                            if not t.get('is_deleted', False):
                                token = t
                                break
                            
                def safe_float(value, default=0.0):
                    try:
                        return float(value or 0)
                    except:
                        return default
                
                def safe_int(value, default=0):
                    try:
                        return int(float(value or 0))
                    except:
                        return default
                
                def safe_str(value, default=""):
                    try:
                        return str(value or default)
                    except:
                        return default
                
                def safe_list(value, default=None):
                    if default is None:
                        default = []
                    try:
                        if isinstance(value, list):
                            return [str(item) for item in value]
                        return default
                    except:
                        return default
                
                social_links = TokenSocialLinks(
                    website=safe_str(token.get('website') if token else None),
                    twitter=safe_str(token.get('twitter') if token else None),
                    facebook=safe_str(token.get('facebook') if token else None),
                    reddit=safe_str(token.get('reddit') if token else None),
                    instagram=safe_str(token.get('instagram') if token else None),
                    discord=safe_str(token.get('discord') if token else None),
                    medium=safe_str(token.get('medium') if token else None),
                    youtube=safe_str(token.get('youtube') if token else None),
                    repo_link=safe_str(token.get('repo_link') if token else None),
                    whitelabel_link=safe_str(token.get('whitelabel_link') if token else None)
                )
                
                localized_description = ""
                if token:
                    localized_description = self._get_localized_description(token, language)
                
                additional_info = TokenAdditionalInfo(
                    description=localized_description,
                    exchanges=safe_list(token.get('exchanges') if token else []),
                    security_audits=safe_list(token.get('security_audits') if token else []),
                    related_people=safe_list(token.get('related_people') if token else []),
                    related_wallets=safe_list(token.get('related_wallets_data') if token else []),
                    related_conductors=safe_list(token.get('related_conductors_data') if token else []),
                    coingecko_id=safe_str(token.get('coingecko_id') if token else token_stats.get('coingecko_id')),
                    created_at=safe_str(token.get('created_at') if token else None),
                    updated_at=safe_str(token.get('updated_at') if token else None),
                    tvl=safe_float(token.get('tvl') if token else None),
                    import_source=safe_str(token.get('import_source') if token else None)
                )
                
                return TokenDetailResponse(
                    id=token_stats.get('coingecko_id', ''),
                    symbol=token_stats.get('symbol', '').upper(),
                    name=token_stats.get('coin_name', ''),
                    image=token.get('avatar_image', '') if token else '',
                    current_price=safe_float(token_stats.get('price')),
                    price_change_percentage_24h=safe_float(token_stats.get('volume_24h_change_24h')),
                    halal_status=HalalStatus(
                        is_halal=token_stats.get('is_halal', None),
                        verified=token_stats.get('halal_verified', None),
                        halal_score=token_stats.get('halal_score', None)
                    ),
                    market_data=MarketData(
                        market_cap_usd=safe_int(token_stats.get('market_cap')),
                        fully_diluted_valuation_usd=safe_int(token_stats.get('fully_diluted_valuation')),
                        total_volume_usd=safe_int(token_stats.get('trading_volume_24h')),
                        circulating_supply_value=safe_int(token_stats.get('circulating_supply')),
                        max_supply_value=safe_int(token_stats.get('token_max_supply')),
                        total_supply_value=safe_int(token_stats.get('token_total_supply'))
                    ),
                    statistics=Statistics(
                        all_time_high=AllTimeHigh(
                            price=safe_float(token_stats.get('ath')),
                            date=token_stats.get('ath_date', '')
                        ),
                        all_time_low=AllTimeLow(
                            price=safe_float(token_stats.get('atl')),
                            date=token_stats.get('atl_date', '')
                        ),
                        price_indicators_24h=PriceIndicators24h(
                            min=safe_float(token_stats.get('low_24h')),
                            max=safe_float(token_stats.get('high_24h'))
                        )
                    ),
                    social_links=social_links,
                    additional_info=additional_info
                )
                
            except Exception as e:
                print(f"[ERROR][MarketService] - Ошибка получения токена {token_id}: {e}")
                return None        
    def get_exchanges_list(self) -> ExchangeListResponse:
        try:
            exchange_stats_repo = self._get_repository(self.exchange_stats_table)
            all_exchange_stats = exchange_stats_repo.scan_items(self.exchange_stats_table, limit=50)
            
            exchange_responses = []
            for idx, stat in enumerate(all_exchange_stats, 1):
                if stat.get('is_deleted', False):
                    continue
                
                exchange_response = {
                    "rank": stat.get('rank', idx),
                    "id": str(stat.get('coingecko_id', stat.get('name', 'unknown'))).lower().replace(' ', '_'),
                    "name": str(stat.get('name', '')),
                    "image": stat.get('image', ''),
                    "halal_status": {
                        "is_halal": stat.get('is_halal', None),
                        "score": stat.get('halal_score', ''),
                        "rating": stat.get('halal_rating', 0)
                    },
                    "trust_score": stat.get('trust_score', 0),
                    "volume_24h_usd": stat.get('trading_volume_24h', 0),
                    "volume_24h_formatted": str(stat.get('trading_volume_24h', 0)),
                    "reserves_usd": stat.get('reserves', 0),
                    "reserves_formatted": str(stat.get('reserves', 0)),
                    "trading_pairs_count": stat.get('trading_pairs', 0),
                    "visitors_monthly": str(stat.get('visitors_monthly', 0)),
                    "supported_fiat": stat.get('supported_fiat', []),
                    "supported_fiat_display": str(stat.get('supported_fiat', [])),
                    "volume_chart_7d": stat.get('volume_chart_7d', []),
                    "exchange_type": stat.get('exchange_type', 'centralized')
                }
                exchange_responses.append(exchange_response)
            
            return ExchangeListResponse(data=exchange_responses)
            
        except Exception as e:
            print(f"[ERROR][MarketService] - Ошибка получения списка бирж: {e}")
            return ExchangeListResponse(data=[])

    def get_exchange_detail(self, exchange_id: str) -> Optional[Dict[str, Any]]:
        try:
            exchange_stats_repo = self._get_repository(self.exchange_stats_table)
            
            exchange_stats_results = exchange_stats_repo.find_by_field('coingecko_id', exchange_id)
            if not exchange_stats_results:
                exchange_name = exchange_id.replace('_', ' ').title()
                exchange_stats_results = exchange_stats_repo.find_by_field('name', exchange_name)
                
            if not exchange_stats_results:
                return None
            
            stats = exchange_stats_results[0]
            
            return {
                "id": stats.get('coingecko_id', exchange_id),
                "name": stats.get('name', ''),
                "image": stats.get('image', ''),
                "halal_status": {
                    "score": stats.get('halal_score', ''),
                    "rating": stats.get('halal_rating', 0),
                    "is_halal": stats.get('is_halal', None)
                },
                "trust_score": stats.get('trust_score', 0),
                "volume_24h_usd": stats.get('trading_volume_24h', 0),
                "total_assets_usd": stats.get('reserves', 0),
                "trading_pairs_count": stats.get('trading_pairs', 0),
                "visitors_monthly": str(stats.get('visitors_monthly', 0)),
                "website_url": stats.get('website_url', ''),
                "supported_fiat": stats.get('supported_fiat', [])
            }
            
        except Exception as e:
            print(f"[ERROR][MarketService] - Ошибка получения деталей биржи {exchange_id}: {e}")
            return None

market_service = MarketDataService()