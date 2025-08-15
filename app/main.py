from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn

app = FastAPI(
    title="Liberandun API",
    description="API for liberandum",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://dev.liberandum",
        "https://dev.liberandum.ai",
        "https://accounts.google.com/",
        "*"
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from app.routes.auth import router as auth_router
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    print("[INFO][APP] - Auth роуты подключены")

    from app.routes.data.tokens import router as tokens_router
    app.include_router(tokens_router, prefix="/market/tokens", tags=["Tokens"])
    print("[INFO][APP] - Tokens роуты подключены")

    from app.routes.data.exchanges import router as exchanges_router  
    app.include_router(exchanges_router, prefix="/market/exchanges", tags=["Exchanges"])
    print("[INFO][APP] - Exchanges роуты подключены")

    from app.routes.data.market_global import router as global_router
    app.include_router(global_router, prefix="/market", tags=["Global Market"])
    print("[INFO][APP] - Global market роуты подключены")

    from app.routes.data.websocket import router as websocket_router
    app.include_router(websocket_router, prefix="/market", tags=["WebSocket"])
    print("[INFO][APP] - WebSocket роуты подключены")

    from app.routes.data.token.halal import router as halal_router
    app.include_router(halal_router, prefix="/market/tokens", tags=["Halal Analysis"])
    print("[INFO][APP] - Halal analysis роуты подключены")

    try:
        from app.routes.admin.main_admin import router as admin_router
        app.include_router(admin_router, prefix="/admin")
        print("[INFO][APP] - Admin роуты подключены")
    except ImportError as e:
        print(f"[WARNING][APP] - Admin роуты не найдены: {e}")
    
    try:
        from app.routes.auth.password_change import password_router
        app.include_router(password_router, prefix="/auth", tags=["Password Management"])
        print("[INFO][APP] - Password change роуты подключены")
    except ImportError as e:
        print(f"[WARNING][APP] - Password change роуты не найдены: {e}")

    try:
        from app.routes.data.favorites_tokens import router as favorites_router
        app.include_router(favorites_router, prefix="/tokens", tags=["Favorites"])
        print("[INFO][APP] - Favorites роуты подключены")
    except ImportError as e:
        print(f"[WARNING][APP] - Favorites роуты не найдены: {e}")

except Exception as e:
    print(f"[ERROR][APP] - Ошибка подключения роутов: {e}")
    import traceback
    traceback.print_exc()

@app.on_event("startup")
async def startup_event():
    try:
        from app.core.database.connector import get_db_connector
        connector = get_db_connector()
        
        if connector:
            system_info = connector.get_system_info()
            print(f"[INFO][APP] - Статус БД: {system_info.get('status')}")
            print(f"[INFO][APP] - Таблиц: {system_info.get('total_tables')}")
        else:
            print("[ERROR][APP] - Не удалось инициализировать базу данных")
            
    except Exception as e:
        print(f"[ERROR][APP] - Ошибка инициализации: {e}")

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )