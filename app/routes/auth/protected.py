from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database.crud.user import *
from app.schemas.user import UserResponse, UserUpdate
from app.core.security.security import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserResponse, summary="Get Current User", description="Get current authenticated user information")
async def get_current_user_info(current_user = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse, summary="Update Profile", description="Update current user profile information")
async def update_current_user(user_update: UserUpdate, current_user = Depends(get_current_user)):
    updates = {}
    if user_update.first_name is not None:
        updates['first_name'] = user_update.first_name
    if user_update.last_name is not None:
        updates['last_name'] = user_update.last_name
    
    if updates:
        new_first = user_update.first_name if user_update.first_name is not None else current_user.get('first_name', '')
        new_last = user_update.last_name if user_update.last_name is not None else current_user.get('last_name', '')
        display_name = f"{new_first} {new_last}".strip()
        if not display_name:
            display_name = current_user['email'].split('@')[0]
        updates['name'] = display_name
    
    if not updates:
        return current_user
    
    updated_user = update_user(current_user['id'], **updates)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка обновления профиля")
    
    return updated_user

@router.post("/logout", summary="Logout User", description="Logout current user and clear tokens")
async def logout(current_user = Depends(get_current_user)):
    success = logout_user(current_user['id'])
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при выходе из системы")
    
    return {"message": "Успешный выход из системы", "email": current_user['email']}