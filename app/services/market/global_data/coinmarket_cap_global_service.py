from typing import Dict, Any, Optional
from datetime import datetime
from app.services.market.global_data.coinmarket_cap_service import coinmarketcap_service
from app.services.market.global_data.global_data_chache import market_globals_cache
from app.schemas.market_global import GlobalMarketResponse, MarketCapData, FearGreedIndex, AltSeasonData


class CoinMarketCapGlobalService:

    async def get_global_market_data(self) -> Optional[GlobalMarketResponse]:
        cached_data = await market_globals_cache.get_cached_data()
        if cached_data:
            print("[INFO] Возвращаем данные из кэша")
            return self._parse_cached_response(cached_data)

        print("[INFO] Получаем свежие данные из CoinMarketCap API...")
        fresh_data = await coinmarketcap_service.get_comprehensive_market_data()

        if fresh_data:
            await market_globals_cache.set_cache_data(fresh_data)
            return self._parse_fresh_response(fresh_data)

        print("[WARNING] Не удалось получить данные из API, используем fallback")
        return self._get_fallback_response()

    def _parse_fresh_response(self, data: Dict[str, Any]) -> GlobalMarketResponse:
        global_metrics = data.get("global_metrics", {})
        alt_season = data.get("alt_season", {})
        fear_greed = data.get("fear_greed", {}) or {
            "value": 50,
            "value_classification": "Нейтрально",
            "timestamp": datetime.utcnow().isoformat(),
            "time_until_update": "Недоступно",
            "source": "fallback"
        }

        return GlobalMarketResponse(
            market_cap=MarketCapData(
                total_market_cap_usd=global_metrics.get("total_market_cap", 0),
                total_volume_usd=global_metrics.get("total_volume_24h", 0),
                market_cap_change_24h_percent=global_metrics.get("market_cap_change_24h", 0),
                btc_dominance=global_metrics.get("btc_dominance", 0),
                eth_dominance=global_metrics.get("eth_dominance", 0),
                active_cryptocurrencies=global_metrics.get("active_cryptocurrencies"),
                markets=global_metrics.get("active_market_pairs"),
                defi_dominance=self._calculate_defi_dominance(global_metrics),
                stablecoin_dominance=self._calculate_stablecoin_dominance(global_metrics)
            ),
            fear_greed_index=FearGreedIndex(
                value=fear_greed.get("value", 50),
                value_classification=fear_greed.get("value_classification", "Нейтрально"),
                timestamp=fear_greed.get("timestamp", ""),
                time_until_update=fear_greed.get("time_until_update"),
                trend_7d=None,
                previous_value=None
            ),
            alt_season=AltSeasonData(
                alt_season_index=alt_season.get("alt_season_index", 50),
                status=alt_season.get("status", "neutral"),
                description=alt_season.get("description", ""),
                source=alt_season.get("source", "coinmarketcap"),
                btc_dominance=alt_season.get("btc_dominance"),
                eth_dominance=alt_season.get("eth_dominance"),
                alt_dominance=alt_season.get("alt_dominance"),
                alts_outperforming=alt_season.get("alts_outperforming"),
                total_alts_analyzed=alt_season.get("total_alts_analyzed"),
                btc_performance_24h=alt_season.get("btc_performance_24h")
            ),
            dominance_changes=self._calculate_dominance_changes(global_metrics),
            last_updated=data.get("fetched_at", datetime.utcnow().isoformat()),
            data_source="coinmarketcap_complete",
            api_calls_remaining=self._calculate_remaining_calls(global_metrics),
            next_update_in="1 час (кэш)"
        )

    def _parse_cached_response(self, data: Dict[str, Any]) -> GlobalMarketResponse:
        response = self._parse_fresh_response(data)
        response.data_source = "coinmarketcap_cached"
        return response

    def _calculate_defi_dominance(self, global_metrics: Dict[str, Any]) -> Optional[float]:
        try:
            defi_market_cap = global_metrics.get("defi_market_cap", 0)
            total_market_cap = global_metrics.get("total_market_cap", 0)
            if total_market_cap > 0 and defi_market_cap > 0:
                return round((defi_market_cap / total_market_cap) * 100, 2)
        except:
            pass
        return None

    def _calculate_stablecoin_dominance(self, global_metrics: Dict[str, Any]) -> Optional[float]:
        try:
            stablecoin_market_cap = global_metrics.get("stablecoin_market_cap", 0)
            total_market_cap = global_metrics.get("total_market_cap", 0)
            if total_market_cap > 0 and stablecoin_market_cap > 0:
                return round((stablecoin_market_cap / total_market_cap) * 100, 2)
        except:
            pass
        return None

    def _calculate_remaining_calls(self, global_metrics: Dict[str, Any]) -> Optional[int]:
        try:
            credits_used = global_metrics.get("api_credits_used", 0)
            return max(0, 10000 - (credits_used * 30))
        except:
            pass
        return None

    def _calculate_dominance_changes(self, global_metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            btc_dominance = global_metrics.get("btc_dominance", 0)
            eth_dominance = global_metrics.get("eth_dominance", 0)
            others_dominance = 100 - btc_dominance - eth_dominance
            return {
                "btc_dominance": btc_dominance,
                "btc_change_24h": 0.0,
                "eth_dominance": eth_dominance,
                "eth_change_24h": 0.0,
                "others_dominance": others_dominance,
                "others_change_24h": 0.0
            }
        except:
            return None

    def _get_fallback_response(self) -> GlobalMarketResponse:
        current_time = datetime.utcnow().isoformat()
        return GlobalMarketResponse(
            market_cap=MarketCapData(
                total_market_cap_usd=4050000000000,
                total_volume_usd=150000000000,
                market_cap_change_24h_percent=0.50,
                btc_dominance=50.0,
                eth_dominance=15.0,
                active_cryptocurrencies=18000,
                markets=500,
                defi_dominance=3.5,
                stablecoin_dominance=6.8
            ),
            fear_greed_index=FearGreedIndex(
                value=50,
                value_classification="Нейтрально",
                timestamp=current_time,
                time_until_update="Обновление через 24 часа",
                trend_7d="Fallback данные",
                previous_value=None
            ),
            alt_season=AltSeasonData(
                alt_season_index=50,
                status="neutral",
                description="Нейтральный рынок - данные временно недоступны",
                source="fallback",
                btc_dominance=50.0,
                eth_dominance=15.0,
                alt_dominance=35.0,
                alts_outperforming=None,
                total_alts_analyzed=None,
                btc_performance_24h=None
            ),
            dominance_changes=None,
            last_updated=current_time,
            data_source="fallback",
            api_calls_remaining=None,
            next_update_in="При восстановлении API"
        )


coinmarketcap_global_service = CoinMarketCapGlobalService()
