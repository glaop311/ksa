
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.core.database.crud.user import (
    add_token_to_favorites, remove_token_from_favorites, 
    get_user_favorite_tokens, clear_user_favorites, is_token_favorite
)
from app.core.security.security import get_current_user
from app.schemas.user import FavoriteTokenRequest, FavoriteTokensResponse
from app.services.market.market_service import market_service

router = APIRouter()

@router.get("/favorites", response_model=FavoriteTokensResponse)
async def get_user_favorites(current_user = Depends(get_current_user)):

    try:
        favorite_tokens = get_user_favorite_tokens(current_user['id'])
        
        return FavoriteTokensResponse(
            favorite_tokens=favorite_tokens,
            total_count=len(favorite_tokens)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения избранного: {str(e)}"
        )

@router.post("/favorites")
async def add_to_favorites(
    request: FavoriteTokenRequest, 
    current_user = Depends(get_current_user)
):

    try:
        token_detail = market_service.get_token_detail(request.token_id)
        if not token_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Токен не найден"
            )
        
        updated_user = add_token_to_favorites(current_user['id'], request.token_id)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка добавления в избранное"
            )
        
        return {
            "message": "Токен добавлен в избранное",
            "token_id": request.token_id,
            "favorite_tokens": updated_user.get('favorite_tokens', [])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка добавления в избранное: {str(e)}"
        )

@router.delete("/favorites/{token_id}")
async def remove_from_favorites(
    token_id: str, 
    current_user = Depends(get_current_user)
):

    try:
        updated_user = remove_token_from_favorites(current_user['id'], token_id)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка удаления из избранного"
            )
        
        return {
            "message": "Токен удален из избранного",
            "token_id": token_id,
            "favorite_tokens": updated_user.get('favorite_tokens', [])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления из избранного: {str(e)}"
        )

@router.delete("/favorites")
async def clear_favorites(current_user = Depends(get_current_user)):

    try:
        updated_user = clear_user_favorites(current_user['id'])
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка очистки избранного"
            )
        
        return {
            "message": "Избранное очищено",
            "favorite_tokens": []
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки избранного: {str(e)}"
        )

@router.get("/favorites/{token_id}/check")
async def check_favorite_status(
    token_id: str, 
    current_user = Depends(get_current_user)
):

    try:
        is_favorite = is_token_favorite(current_user['id'], token_id)
        
        return {
            "token_id": token_id,
            "is_favorite": is_favorite
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка проверки статуса: {str(e)}"
        )

@router.get("/favorites/tokens/details")
async def get_favorite_tokens_details(current_user = Depends(get_current_user)):

    try:
        favorite_token_ids = get_user_favorite_tokens(current_user['id'])
        
        if not favorite_token_ids:
            return {
                "favorite_tokens": [],
                "total_count": 0
            }
        
        token_details = []
        for token_id in favorite_token_ids:
            token_detail = market_service.get_token_detail(token_id)
            if token_detail:
                token_details.append(token_detail)
        
        return {
            "favorite_tokens": token_details,
            "total_count": len(token_details)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения деталей избранных токенов: {str(e)}"
        )