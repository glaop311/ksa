# app/services/market/global_data/global_data_cash.py
import os
import json
import threading
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Пытаемся импортировать проектный GenericRepository.
# Если он недоступен или неправильно инициализирован (например DB = None),
# переключимся на файл-репозиторий (fallback).
try:
    from app.core.database.repositories.generic import GenericRepository
except Exception:
    GenericRepository = None  # будем ловить это позже


class _FileCacheRepository:
    """
    Простой файловый репозиторий как fallback.
    Хранит словарь {cache_key: entry_dict} в JSON-файле.
    """
    def __init__(self, filepath: Optional[str] = None):
        if not filepath:
            filepath = os.path.join(tempfile.gettempdir(), "market_globals_cache.json")
        self.filepath = filepath
        self._lock = threading.Lock()
        # Ensure file exists and is a dict
        with self._lock:
            if not os.path.exists(self.filepath):
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump({}, f)

    def _read_all(self) -> Dict[str, Any]:
        with self._lock:
            with open(self.filepath, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except Exception:
                    return {}

    def _write_all(self, data: Dict[str, Any]) -> None:
        with self._lock:
            tmp_path = f"{self.filepath}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.filepath)

    # API совместимый с GenericRepository в минимальном объёме, который нужен сервису
    def get_by_id(self, key: str) -> Optional[Dict[str, Any]]:
        all_data = self._read_all()
        return all_data.get(key)

    def create(self, entry: Dict[str, Any], auto_id: bool = True) -> None:
        all_data = self._read_all()
        key = entry.get("id")
        if not key and auto_id:
            # простой авто-id
            key = str(int(datetime.utcnow().timestamp()))
            entry["id"] = key
        all_data[key] = entry
        self._write_all(all_data)

    def update_by_id(self, key: str, entry: Dict[str, Any]) -> None:
        all_data = self._read_all()
        all_data[key] = entry
        self._write_all(all_data)

    def delete_by_id(self, key: str) -> bool:
        all_data = self._read_all()
        if key in all_data:
            all_data.pop(key)
            self._write_all(all_data)
            return True
        return False


class MarketGlobalsCacheService:
    def __init__(self):
        self.cache_table = "market_globals_cache"
        self.cache_key = "coinmarketcap_global_data"
        self.ttl_hours = 1  # Кэш на 1 час
        # Путь для файлового фоллбека (можно изменить)
        self._fallback_path = os.path.join(tempfile.gettempdir(), "market_globals_cache.json")
        # Кешируем репозиторий
        self._repo_instance = None
        self._repo_is_file_fallback = False

    def _get_repository(self):
        """
        Возвращает рабочий репозиторий: либо GenericRepository (если доступен и рабочий),
        либо файловый репозиторий.
        """
        if self._repo_instance is not None:
            return self._repo_instance

        # Попробуем использовать GenericRepository (проектный)
        if GenericRepository is not None:
            try:
                repo = GenericRepository(self.cache_table)
                # Smoke test: вызов get_by_id для проверки корректной инициализации/подключения в репозитории.
                try:
                    # Неважно, что вернёт — главное, чтобы метод не упал с AttributeError('... Table')
                    _ = repo.get_by_id(self.cache_key)
                    self._repo_instance = repo
                    self._repo_is_file_fallback = False
                    return repo
                except Exception as e:
                    print(f"[WARNING] GenericRepository инициализирован, но test-операция упала: {e}")
                    # fallthrough -> используем файловый фоллбек
            except Exception as e:
                print(f"[WARNING] GenericRepository недоступен или не может быть создан: {e}")

        # Если мы здесь — GenericRepository либо отсутствует, либо внутренне сломан — используем файловый репозиторий.
        file_repo = _FileCacheRepository(filepath=self._fallback_path)
        self._repo_instance = file_repo
        self._repo_is_file_fallback = True
        print(f"[INFO] Используется файловый fallback для кэша: {self._fallback_path}")
        return self._repo_instance

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Проверяем валидность кэша (ttl_hours)"""
        try:
            cached_time = datetime.fromisoformat(cache_entry.get("cached_at", ""))
            expiry_time = cached_time + timedelta(hours=self.ttl_hours)
            current_time = datetime.utcnow()
            is_valid = current_time < expiry_time

            if is_valid:
                time_left = expiry_time - current_time
                minutes_left = int(time_left.total_seconds() / 60)
                print(f"[INFO] Кэш валиден, истекает через {minutes_left} минут")
            else:
                expired_ago = current_time - expiry_time
                minutes_ago = int(expired_ago.total_seconds() / 60)
                print(f"[INFO] Кэш истек {minutes_ago} минут назад")

            return is_valid
        except Exception as e:
            print(f"[ERROR] Ошибка проверки кэша: {e}")
            return False

    async def get_cached_data(self) -> Optional[Dict[str, Any]]:
        """Получить данные из кэша"""
        try:
            repo = self._get_repository()
            cache_entry = None
            try:
                cache_entry = repo.get_by_id(self.cache_key)
            except Exception as e:
                print(f"[ERROR] Ошибка при чтении из репозитория кэша: {e}")
                # если файл-фоллбек, repo уже корректен; иначе пробуем переключиться на файл-фоллбек
                if not self._repo_is_file_fallback:
                    # переключиться на файловый репозиторий и повторить
                    repo = _FileCacheRepository(filepath=self._fallback_path)
                    self._repo_instance = repo
                    self._repo_is_file_fallback = True
                    print("[INFO] Переключаемся на файловый фоллбек и повторяем чтение")
                    cache_entry = repo.get_by_id(self.cache_key)

            if cache_entry and self._is_cache_valid(cache_entry):
                print("[INFO] Используем кэшированные глобальные данные CoinMarketCap")
                cached_data = json.loads(cache_entry.get("data", "{}"))

                # Добавляем мета-информацию о кэше
                cached_data["from_cache"] = True
                cached_data["cache_created_at"] = cache_entry.get("cached_at")
                cached_data["cache_expires_at"] = cache_entry.get("expires_at")

                return cached_data

            if cache_entry:
                print("[INFO] Кэш существует, но истёк - получаем свежие данные")
            else:
                print("[INFO] Кэш не найден - получаем свежие данные")

            return None
        except Exception as e:
            print(f"[ERROR] Ошибка получения кэша: {e}")
            return None

    async def set_cache_data(self, data: Dict[str, Any]) -> bool:
        """Сохранить данные в кэш на ttl_hours"""
        try:
            repo = self._get_repository()

            current_time = datetime.utcnow()
            expiry_time = current_time + timedelta(hours=self.ttl_hours)

            # Подготовка данных к сохранению
            clean_data = data.copy()
            clean_data.pop("from_cache", None)
            clean_data.pop("cache_created_at", None)
            clean_data.pop("cache_expires_at", None)

            cache_entry = {
                "id": self.cache_key,
                "data": json.dumps(clean_data, ensure_ascii=False),
                "cached_at": current_time.isoformat(),
                "expires_at": expiry_time.isoformat(),
                "ttl_hours": self.ttl_hours,
                "data_source": clean_data.get("source", "unknown"),
                "api_credits_used": clean_data.get("total_api_credits_used", 0),
            }

            # Пытаемся обновить или создать запись
            try:
                existing = repo.get_by_id(self.cache_key)
                if existing:
                    repo.update_by_id(self.cache_key, cache_entry)
                    print(f"[INFO] Кэш обновлён, истекает в {expiry_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
                else:
                    repo.create(cache_entry, auto_id=False)
                    print(f"[INFO] Создан новый кэш, истекает в {expiry_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
                return True
            except Exception as e:
                # В случае ошибки записи в GenericRepository — переключаемся на файловый фоллбек и пробуем ещё раз
                print(f"[WARNING] Ошибка записи в репозиторий кэша: {e} — переключаемся на файловый fallback.")
                file_repo = _FileCacheRepository(filepath=self._fallback_path)
                self._repo_instance = file_repo
                self._repo_is_file_fallback = True
                # Попытка записи в файловый репозиторий
                try:
                    existing = file_repo.get_by_id(self.cache_key)
                    if existing:
                        file_repo.update_by_id(self.cache_key, cache_entry)
                    else:
                        file_repo.create(cache_entry, auto_id=False)
                    print(f"[INFO] Кэш сохранён во файловый fallback, истекает в {expiry_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
                    return True
                except Exception as e2:
                    print(f"[ERROR] Ошибка сохранения кэша во файловый fallback: {e2}")
                    return False

        except Exception as e:
            print(f"[ERROR] Ошибка сохранения кэша: {e}")
            return False

    async def clear_cache(self) -> bool:
        """Очистить кэш (для принудительного обновления)"""
        try:
            repo = self._get_repository()
            try:
                success = repo.delete_by_id(self.cache_key)
                if success:
                    print("[INFO] Кэш очищен")
                else:
                    print("[INFO] Кэш не найден при попытке очистки")
                return success
            except Exception as e:
                print(f"[ERROR] Ошибка при удалении записи из репозитория: {e}")
                # Попробуем файловый репозиторий
                file_repo = _FileCacheRepository(filepath=self._fallback_path)
                self._repo_instance = file_repo
                self._repo_is_file_fallback = True
                return file_repo.delete_by_id(self.cache_key)
        except Exception as e:
            print(f"[ERROR] Ошибка очистки кэша: {e}")
            return False

    async def get_cache_info(self) -> Dict[str, Any]:
        """Получить информацию о состоянии кэша"""
        try:
            repo = self._get_repository()
            cache_entry = None
            try:
                cache_entry = repo.get_by_id(self.cache_key)
            except Exception as e:
                print(f"[ERROR] Ошибка чтения информации о кэше из репозитория: {e}")
                # пробуем файловый фоллбек
                repo = _FileCacheRepository(filepath=self._fallback_path)
                self._repo_instance = repo
                self._repo_is_file_fallback = True
                cache_entry = repo.get_by_id(self.cache_key)

            if not cache_entry:
                return {"status": "no_cache", "message": "Кэш не существует"}

            cached_time = datetime.fromisoformat(cache_entry.get("cached_at", ""))
            expiry_time = datetime.fromisoformat(cache_entry.get("expires_at", ""))
            current_time = datetime.utcnow()

            is_valid = current_time < expiry_time

            if is_valid:
                time_left = expiry_time - current_time
                minutes_left = int(time_left.total_seconds() / 60)
                status = "valid"
                message = f"Кэш валиден, истекает через {minutes_left} минут"
            else:
                expired_ago = current_time - expiry_time
                minutes_ago = int(expired_ago.total_seconds() / 60)
                status = "expired"
                message = f"Кэш истёк {minutes_ago} минут назад"

            return {
                "status": status,
                "message": message,
                "cached_at": cache_entry.get("cached_at"),
                "expires_at": cache_entry.get("expires_at"),
                "ttl_hours": cache_entry.get("ttl_hours"),
                "data_source": cache_entry.get("data_source"),
                "api_credits_used": cache_entry.get("api_credits_used", 0),
                "is_valid": is_valid,
                "using_file_fallback": self._repo_is_file_fallback,
            }

        except Exception as e:
            return {"status": "error", "message": f"Ошибка получения информации о кэше: {e}"}


market_globals_cache = MarketGlobalsCacheService()
