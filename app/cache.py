# app/cache.py
"""Модуль кэширования профиля пользователя"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

from .config import CACHE_TTL_SECONDS

class ProfileCache:
    def __init__(self, cache_file: str = "profile_cache.json"):
        self.cache_file = Path(cache_file)
        self._cache: Optional[Dict[str, Any]] = None

    def save(self, steam_id: str, player_summary: dict, games_data: list):
        """Сохраняет профиль в файл."""
        data = {
            "steam_id": steam_id,
            "timestamp": time.time(),
            "player_summary": player_summary,
            "games_data": games_data
        }
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Логируем ошибку, но не прерываем работу
            logging.getLogger(__name__).exception("Ошибка сохранения кэша")

    def load(self) -> Optional[Dict[str, Any]]:
        """Загружает профиль, если он не устарел."""
        if not self.cache_file.exists():
            return None
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            timestamp = data.get("timestamp", 0)
            if time.time() - timestamp > CACHE_TTL_SECONDS:
                # Кэш устарел
                self.cache_file.unlink(missing_ok=True)
                return None
            return data
        except Exception as e:
            logging.getLogger(__name__).exception("Ошибка загрузки кэша")
            return None

    def clear(self):
        """Удаляет файл кэша."""
        try:
            self.cache_file.unlink(missing_ok=True)
        except Exception:
            pass