from fastapi import APIRouter, HTTPException, status, Path, Query
from typing import Dict, Any
from enum import Enum

from app.services.market.halal.halal_analysis_service import halal_analysis_service

router = APIRouter()

class Language(str, Enum):
    en = "en"
    ru = "ru"
    uz = "uz"

@router.get("/halal-analysis/{symbol}")
async def get_halal_analysis(
    symbol: str = Path(..., description="Символ криптовалюты (например: BTC, ETH)", min_length=1, max_length=10),
    lang: Language = Query(default=Language.en, description="Язык отображения")
) -> Dict[str, Any]:
    try:
        symbol = symbol.upper().strip()
        
        result = await halal_analysis_service.get_halal_analysis(symbol, lang.value)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Halal analysis not found for symbol: {symbol}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR][HalalAnalysis] - Unexpected error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching halal analysis"
        )