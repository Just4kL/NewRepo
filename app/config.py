# app/config.py
"""Конфигурация приложения"""
# Поддерживаемые языки (порядок = порядок переключения глобусом 🌐)
LANGUAGES = [
    {"code": "ru", "name": "Русский", "flag": "🇷🇺", "native": "Русский", "description": "Интерфейс на русском языке"},
    {"code": "en", "name": "English", "flag": "🇬🇧", "native": "English", "description": "Interface in English"},
    {"code": "la", "name": "Latina", "flag": "🏛️", "native": "Latina", "description": "Interfacies Latina"},
    {"code": "es", "name": "Español", "flag": "🇪🇸", "native": "Español", "description": "Interfaz en español"},
    {"code": "de", "name": "Deutsch", "flag": "🇩🇪", "native": "Deutsch", "description": "Oberfläche auf Deutsch"},
    {"code": "ja", "name": "日本語", "flag": "🇯🇵", "native": "日本語", "description": "日本語インターフェース"},
    {"code": "zh", "name": "简体中文", "flag": "🇨🇳", "native": "简体中文", "description": "简体中文界面"},
    {"code": "pt", "name": "Português", "flag": "🇵🇹", "native": "Português", "description": "Interface em português"},
    {"code": "cs", "name": "Čeština", "flag": "🇨🇿", "native": "Čeština", "description": "Rozhraní v češtině"},
    {"code": "pl", "name": "Polski", "flag": "🇵🇱", "native": "Polski", "description": "Interfejs w języku polskim"},
    {"code": "uk", "name": "Українська", "flag": "🇺🇦", "native": "Українська", "description": "Інтерфейс українською мовою"},
    {"code": "hi", "name": "हिन्दी", "flag": "🇮🇳", "native": "हिन्दी", "description": "हिन्दी में इंटरफ़ेस"},
    {"code": "fr", "name": "Français", "flag": "🇫🇷", "native": "Français", "description": "Interface en français"},
    {"code": "ar", "name": "العربية", "flag": "🇸🇦", "native": "العربية", "description": "واجهة باللغة العربية"},
    {"code": "id", "name": "Bahasa Indonesia", "flag": "🇮🇩", "native": "Bahasa Indonesia", "description": "Antarmuka Bahasa Indonesia"},
]

STEAM_API_BASE = "https://api.steampowered.com"
INTERFACE_PLAYER = "IPlayerService"
INTERFACE_USER = "ISteamUser"
INTERFACE_USER_STATS = "ISteamUserStats"

VERSION = "0.5.19 alpha"
BUILD_VERSION = "0.5.19.39"  # Build +1
AUTHOR = "Kenig Theodor"
BUILD_DATE = "2026-08-17"

# URL для получения API ключа
STEAM_API_KEY_URL = "https://steamcommunity.com/dev/apikey"
# URL для получения Steam ID
STEAM_ID_URL = "https://store.steampowered.com/account/"

# Ограничение одновременных HTTP-запросов
MAX_CONCURRENT_REQUESTS = 10

# Сетевые настройки
CONNECT_TIMEOUT = 10          # секунд на установку соединения
REQUEST_TIMEOUT = 30          # секунд на весь запрос
REQUEST_RETRIES = 3           # сколько раз повторять при сетевой ошибке
RETRY_BASE_DELAY = 0.8        # базовая задержка между попытками (секунды)

# Настройки кэша
CACHE_TTL_SECONDS = 24 * 60 * 60  # 1 сутки

# Цвета для подсветки
COLOR_VALID = "#ccffcc"
COLOR_INVALID = "#ffffcc"
COLOR_ERROR = "#ffcccc"
COLOR_ACHIEVEMENT_COMPLETE = "#ccffcc"
COLOR_FIRST_10 = "#e0ffe0"
COLOR_NEXT_10 = "#ffffe0"