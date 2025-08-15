
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Dict, Any, Optional, List

from app.core.security.security import get_admin_user
from app.routes.admin.admin_controller import BaseAdminController
from app.schemas.wallte_conductors import WalletCreate, WalletUpdate, WalletResponse
from app.core.database.connector import get_generic_repository

router = APIRouter()
controller = BaseAdminController("LiberandumApiWallets", "wallet")

@router.post("/", response_model=WalletResponse)
async def create_wallet(wallet_data: WalletCreate, current_user = Depends(get_admin_user)):
    result = await controller.create_entity(wallet_data.dict(), current_user)
    return WalletResponse(**result["entity"])

@router.get("/", response_model=List[WalletResponse])
async def list_wallets(current_user = Depends(get_admin_user)):
    result = await controller.get_entities_list(None, current_user)
    return [WalletResponse(**wallet) for wallet in result["wallets"]]

@router.get("/search", response_model=List[WalletResponse])
async def search_wallets(
    q: str = Query(..., min_length=1, description="Поиск по названию"),
    limit: int = Query(default=50, ge=1, le=200, description="Количество результатов"),
    current_user = Depends(get_admin_user)
):
    try:
        wallets_repo = get_generic_repository("LiberandumApiWallets")
        all_wallets = wallets_repo.list_all(limit=1000)
        
        query_lower = q.lower().strip()
        results = []
        
        for wallet in all_wallets:
            if wallet.get('is_deleted', False):
                continue
                
            title = wallet.get('title', '').lower()
            url = wallet.get('url', '').lower()
            
            if (query_lower in title or 
                query_lower in url or
                title.startswith(query_lower)):
                
                results.append(WalletResponse(**wallet))
            
            if len(results) >= limit:
                break
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска кошельков: {str(e)}"
        )

@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(wallet_id: str, current_user = Depends(get_admin_user)):
    result = await controller.get_entity_by_id(wallet_id, current_user)
    return WalletResponse(**result["wallet"])

@router.put("/{wallet_id}", response_model=WalletResponse)
async def update_wallet(wallet_id: str, updates: WalletUpdate, current_user = Depends(get_admin_user)):
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    result = await controller.update_entity(wallet_id, update_data, current_user)
    return WalletResponse(**result["wallet"])

@router.delete("/{wallet_id}")
async def delete_wallet(wallet_id: str, current_user = Depends(get_admin_user)):

    return await controller.delete_entity(wallet_id, current_user)