import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.security.config import settings


class CoinMarketCapService:
    def __init__(self):
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.timeout = 30.0
        self.api_key = "151b6ed3-d785-4e49-8e33-2b8e53ecf117"

        if not self.api_key:
            print("[WARNING] CoinMarketCap API key not found in settings")

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "deflate, gzip",
            "User-Agent": "Liberandum-API/1.0"
        }
        if self.api_key:
            headers["X-CMC_PRO_API_KEY"] = self.api_key
        return headers

    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        try:
            if not self.api_key:
                print("[ERROR] CoinMarketCap API key not available")
                return None

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}{endpoint}", params=params, headers=self._get_headers())

            if response.status_code == 200:
                data = response.json()
                if data.get("status", {}).get("error_code") == 0:
                    return data
                else:
                    print(f"[ERROR] CoinMarketCap API error: {data['status'].get('error_message')}")
                    return None
            elif response.status_code == 401:
                print(f"[ERROR] CoinMarketCap unauthorized - check API key")
            elif response.status_code == 429:
                print(f"[WARNING] CoinMarketCap rate limited")
            else:
                print(f"[ERROR] CoinMarketCap HTTP {response.status_code}: {response.text}")
            return None

        except httpx.TimeoutException:
            print(f"[ERROR] CoinMarketCap request timeout for {endpoint}")
            return None
        except Exception as e:
            print(f"[ERROR] CoinMarketCap request failed: {e}")
            return None

    async def get_global_metrics(self, convert: str = "USD") -> Optional[Dict[str, Any]]:
        params = {"convert": convert}
        response = await self._make_request("/global-metrics/quotes/latest", params)
        if not response:
            return None

        data = response.get("data", {})
        quote_data = data.get("quote", {}).get(convert.upper(), {})

        return {
            "total_market_cap": quote_data.get("total_market_cap", 0),
            "total_volume_24h": quote_data.get("total_volume_24h", 0),
            "market_cap_change_24h": quote_data.get("total_market_cap_yesterday_percentage_change", 0),
            "volume_change_24h": quote_data.get("total_volume_24h_yesterday_percentage_change", 0),
            "btc_dominance": data.get("btc_dominance", 0),
            "eth_dominance": data.get("eth_dominance", 0),
            "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
            "active_exchanges": data.get("active_exchanges", 0),
            "active_market_pairs": data.get("active_market_pairs", 0),
            "defi_volume_24h": quote_data.get("defi_volume_24h", 0),
            "defi_market_cap": quote_data.get("defi_market_cap", 0),
            "stablecoin_volume_24h": quote_data.get("stablecoin_volume_24h", 0),
            "stablecoin_market_cap": quote_data.get("stablecoin_market_cap", 0),
            "last_updated": data.get("last_updated", ""),
            "api_credits_used": response.get("status", {}).get("credit_count", 0)
        }

    async def get_top_cryptocurrencies(self, limit: int = 100, convert: str = "USD") -> Optional[Dict[str, Any]]:
        params = {"limit": limit, "convert": convert}
        response = await self._make_request("/cryptocurrency/listings/latest", params)
        if not response:
            return None
        return {
            "cryptocurrencies": response.get("data", []),
            "api_credits_used": response.get("status", {}).get("credit_count", 0)
        }

    def calculate_alt_season_index(self, global_data: Dict[str, Any], top_coins: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            btc_dominance = global_data.get("btc_dominance", 50.0)
            eth_dominance = global_data.get("eth_dominance", 15.0)

            if btc_dominance >= 70:
                alt_season_index = max(0, int((100 - btc_dominance) * 2))
                status = "btc_season"
                description = f"Bitcoin сезон! Доминирование BTC: {btc_dominance:.1f}%"
            elif btc_dominance <= 40:
                alt_season_index = min(100, int(100 - btc_dominance + 10))
                status = "alt_season"
                description = f"Альтсезон! Доминирование BTC снизилось до {btc_dominance:.1f}%"
            else:
                normalized_dominance = (btc_dominance - 40) / 30
                alt_season_index = int(75 - (normalized_dominance * 50))
                status = "neutral"
                description = f"Смешанный рынок. BTC: {btc_dominance:.1f}%, ETH: {eth_dominance:.1f}%"

            return {
                "alt_season_index": alt_season_index,
                "status": status,
                "description": description,
                "source": "coinmarketcap_calculation",
                "btc_dominance": round(btc_dominance, 2),
                "eth_dominance": round(eth_dominance, 2),
                "alt_dominance": round(100 - btc_dominance - eth_dominance, 2),
                "updated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"[ERROR] Alt season calculation failed: {e}")
            return {
                "alt_season_index": 50,
                "status": "neutral",
                "description": "Ошибка расчета альтсезона",
                "source": "fallback",
                "btc_dominance": 58.0,
                "updated_at": datetime.utcnow().isoformat()
            }

    async def get_fear_greed_index(self) -> Optional[Dict[str, Any]]:
        """Берем напрямую из Alternative.me"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get("https://api.alternative.me/fng/")
            if response.status_code == 200:
                fng_data = response.json().get("data", [])
                if fng_data:
                    latest = fng_data[0]
                    value = int(latest.get("value", 0))
                    classification = self._classify_fng(value)
                    return {
                        "value": value,
                        "value_classification": classification,
                        "timestamp": latest.get("timestamp", ""),
                        "time_until_update": latest.get("time_until_update", ""),
                        "source": "alternative_me",
                        "api_credits_used": 0
                    }
        except Exception as e:
            print(f"[ERROR] Fear & Greed API failed: {e}")
        return None

    def _classify_fng(self, value: int) -> str:
        if value >= 75:
            return "Экстремальная жадность"
        elif value >= 55:
            return "Жадность"
        elif value >= 45:
            return "Нейтрально"
        elif value >= 25:
            return "Страх"
        else:
            return "Экстремальный страх"

    async def get_comprehensive_market_data(self) -> Optional[Dict[str, Any]]:
        try:
            tasks = [
                self.get_global_metrics(),
                self.get_top_cryptocurrencies(limit=20),
                self.get_fear_greed_index()
            ]
            global_data, top_coins, fear_greed_data = await asyncio.gather(*tasks, return_exceptions=True)

            if not global_data:
                return None
            alt_season_data = self.calculate_alt_season_index(global_data, top_coins if not isinstance(top_coins, Exception) else None)
            return {
                "global_metrics": global_data,
                "alt_season": alt_season_data,
                "fear_greed": fear_greed_data if not isinstance(fear_greed_data, Exception) else None,
                "fetched_at": datetime.utcnow().isoformat(),
                "source": "coinmarketcap_api_complete",
                "total_api_credits_used": (
                    global_data.get("api_credits_used", 0) +
                    (top_coins.get("api_credits_used", 0) if top_coins and not isinstance(top_coins, Exception) else 0)
                )
            }
        except Exception as e:
            print(f"[ERROR] Comprehensive market data failed: {e}")
            return None


coinmarketcap_service = CoinMarketCapService()
