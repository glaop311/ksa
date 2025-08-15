# simple_test_coinmarketcap.py

import asyncio
import httpx
from datetime import datetime

async def test_coinmarketcap_direct():
    """Прямой тест CoinMarketCap API без базы данных"""
    
    API_KEY = "YOUR_API_KEY_HERE"  # Замените на ваш API ключ
    BASE_URL = "https://pro-api.coinmarketcap.com/v1"
    
    headers = {
        "Accept": "application/json",
        "X-CMC_PRO_API_KEY": API_KEY
    }
    
    print("🧪 Прямой тест CoinMarketCap API")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Тест 1: Глобальные метрики
        print("📊 Тестируем глобальные метрики...")
        try:
            response = await client.get(
                f"{BASE_URL}/global-metrics/quotes/latest",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status", {}).get("error_code") == 0:
                    global_data = data.get("data", {})
                    quote = global_data.get("quote", {}).get("USD", {})
                    
                    print("✅ Глобальные метрики получены:")
                    print(f"   💰 Общая капитализация: ${quote.get('total_market_cap', 0):,.0f}")
                    print(f"   📈 Объем 24ч: ${quote.get('total_volume_24h', 0):,.0f}")
                    print(f"   ₿ BTC доминирование: {global_data.get('btc_dominance', 0):.1f}%")
                    print(f"   ⟠ ETH доминирование: {global_data.get('eth_dominance', 0):.1f}%")
                    print(f"   🔗 Активных криптовалют: {global_data.get('active_cryptocurrencies', 0)}")
                else:
                    print(f"❌ API ошибка: {data.get('status', {}).get('error_message')}")
            else:
                print(f"❌ HTTP ошибка: {response.status_code}")
                print(f"   Ответ: {response.text}")
                
        except Exception as e:
            print(f"❌ Исключение: {e}")
        
        print()
        
        # Тест 2: Fear & Greed Index (пробуем разные эндпоинты)
        print("😰 Тестируем Fear & Greed Index...")
        
        fear_greed_endpoints = [
            "/v3/fear-and-greed/latest",
            "/v1/fear-and-greed/latest",
            "/fear-and-greed/latest"
        ]
        
        fear_greed_found = False
        
        for endpoint in fear_greed_endpoints:
            try:
                print(f"   Пробуем: {endpoint}")
                response = await client.get(
                    f"https://pro-api.coinmarketcap.com{endpoint}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status", {}).get("error_code") == 0:
                        print(f"✅ Fear & Greed найден в {endpoint}")
                        fg_data = data.get("data", {})
                        print(f"   😱 Значение: {fg_data.get('value', 'N/A')}")
                        print(f"   📊 Статус: {fg_data.get('value_classification', 'N/A')}")
                        fear_greed_found = True
                        break
                else:
                    print(f"   ⚠️  HTTP {response.status_code}: {response.text[:100]}")
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        if not fear_greed_found:
            print("❌ Fear & Greed Index не найден в CMC API")
            print("   Будем использовать Alternative.me как fallback")
            
            # Тестируем Alternative.me
            try:
                response = await client.get("https://api.alternative.me/fng/")
                if response.status_code == 200:
                    data = response.json()
                    fng_data = data.get("data", [])
                    if fng_data:
                        latest = fng_data[0]
                        print(f"✅ Alternative.me Fear & Greed:")
                        print(f"   😱 Значение: {latest.get('value')}")
                        print(f"   📊 Статус: {latest.get('value_classification')}")
            except Exception as e:
                print(f"❌ Alternative.me тоже недоступен: {e}")
        
        print()
        
        # Тест 3: Топ криптовалют для альтсезона
        print("🚀 Тестируем топ криптовалют...")
        try:
            response = await client.get(
                f"{BASE_URL}/cryptocurrency/listings/latest",
                headers=headers,
                params={"limit": 10, "convert": "USD"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status", {}).get("error_code") == 0:
                    cryptos = data.get("data", [])
                    print(f"✅ Получено {len(cryptos)} криптовалют:")
                    
                    btc_change = None
                    positive_alts = 0
                    total_alts = 0
                    
                    for crypto in cryptos[:5]:  # Показываем топ 5
                        symbol = crypto.get("symbol", "")
                        name = crypto.get("name", "")
                        quote = crypto.get("quote", {}).get("USD", {})
                        price = quote.get("price", 0)
                        change_24h = quote.get("percent_change_24h", 0)
                        
                        print(f"   {symbol:4} ({name[:15]:15}): ${price:8.2f} ({change_24h:+.2f}%)")
                        
                        if symbol == "BTC":
                            btc_change = change_24h
                        elif symbol not in ["USDT", "USDC", "DAI"]:
                            total_alts += 1
                            if change_24h > 0:
                                positive_alts += 1
                    
                    if total_alts > 0:
                        alt_performance = (positive_alts / total_alts) * 100
                        print(f"   📈 Альткоинов растет: {positive_alts}/{total_alts} ({alt_performance:.1f}%)")
                    
                else:
                    print(f"❌ API ошибка: {data.get('status', {}).get('error_message')}")
            else:
                print(f"❌ HTTP ошибка: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Исключение: {e}")
        
        print("\n" + "=" * 50)
        print("✨ Тест завершен!")
        print("\n💡 Если тесты прошли успешно, добавьте ваш API ключ в .secrets.toml:")
        print("   coinmarketcap_api_key = \"ваш_ключ_здесь\"")

if __name__ == "__main__":
    asyncio.run(test_coinmarketcap_direct())