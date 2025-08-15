import httpx
from typing import Dict, Any, Optional
from datetime import datetime

class HalalAnalysisService:
    def __init__(self):
        self.base_url = "http://16.171.39.239:50002/api/v1/result"
        self.timeout = 30.0
    
    async def get_halal_analysis(self, symbol: str, language: str = "en") -> Optional[Dict[str, Any]]:
        try:
            params = {"lang": language}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/{symbol.upper()}", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    return data
                elif response.status_code == 404:
                    print(f"[INFO][HalalAnalysis] - Analysis not found for {symbol}")
                    return None
                else:
                    print(f"[ERROR][HalalAnalysis] - HTTP {response.status_code} for {symbol}")
                    return None
                    
        except httpx.TimeoutException:
            print(f"[ERROR][HalalAnalysis] - Timeout for {symbol}")
            return None
        except Exception as e:
            print(f"[ERROR][HalalAnalysis] - Request failed for {symbol}: {e}")
            return None

halal_analysis_service = HalalAnalysisService()