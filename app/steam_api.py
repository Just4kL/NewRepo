# app/steam_api.py
"""Модуль для работы со Steam Web API"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:  # только для подсказок типов, в рантайме не грузится
    import aiohttp

from .config import (
    STEAM_API_BASE,
    INTERFACE_PLAYER,
    INTERFACE_USER,
    INTERFACE_USER_STATS,
    MAX_CONCURRENT_REQUESTS,
    CONNECT_TIMEOUT,
    REQUEST_TIMEOUT,
    REQUEST_RETRIES,
    RETRY_BASE_DELAY
)

logger = logging.getLogger(__name__)

_aiohttp = None


def _aio():
    """Ленивый импорт aiohttp.

    Импорт всего стека (client, resolver, ssl, email, …) коммитит десятки
    мегабайт приватной памяти под нативные DLL. Сеть нужна только по клику
    «Проверить» / «Посчитать время», поэтому грузим её при первом запросе,
    а не при старте приложения.
    """
    global _aiohttp
    if _aiohttp is None:
        import aiohttp as _mod
        _aiohttp = _mod
    return _aiohttp


class SteamApiError(Exception):
    """Ошибка Steam API, готовая к показу пользователю.

    Хранит ключ перевода, а не технический текст aiohttp, поэтому
    интерфейс показывает понятное сообщение на языке приложения.
    """

    def __init__(self, message_key: str, detail: str = ""):
        self.message_key = message_key
        self.detail = detail
        super().__init__(message_key)

    def __str__(self) -> str:
        from .i18n import tr
        text = tr(self.message_key)
        if self.detail:
            return "%s (%s)" % (text, self.detail)
        return text


def _get_semaphore() -> asyncio.Semaphore:
    """Создаёт semaphore в текущем event loop."""
    return asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


def _is_retryable(exc: BaseException) -> bool:
    """Сетевые ошибки, при которых есть смысл повторить запрос.

    Ошибки 4xx (неверный ключ, не найден) повторять бессмысленно —
    они воспроизводятся гарантированно.
    """
    aiohttp = _aio()
    if isinstance(exc, (aiohttp.ClientConnectorDNSError,
                        aiohttp.ClientConnectorError,
                        aiohttp.ServerDisconnectedError,
                        aiohttp.ClientPayloadError,
                        aiohttp.ClientOSError,
                        asyncio.TimeoutError,
                        ConnectionError,      # ConnectionReset/Aborted/Refused
                        OSError)):            # прочие сетевые сбои ОС
        return True
    # aiohttp.ClientError без более узкой ветки выше (напр. 5xx-обёртки)
    return isinstance(exc, aiohttp.ClientError) and not isinstance(
        exc, (aiohttp.ClientResponseError, aiohttp.ClientHttpProxyError)
    )


def _describe_network_error(exc: BaseException) -> str:
    """Короткое техническое описание для лога, без мусора трейсбека."""
    aiohttp = _aio()
    if isinstance(exc, aiohttp.ClientConnectorDNSError):
        return "DNS не отвечает"
    if isinstance(exc, asyncio.TimeoutError):
        return "превышено время ожидания"
    if isinstance(exc, aiohttp.ServerDisconnectedError):
        return "сервер разорвал соединение"
    if isinstance(exc, aiohttp.ClientPayloadError):
        return "обрыв ответа"
    return type(exc).__name__


def _make_session() -> aiohttp.ClientSession:
    """Создаёт сессию с явным системным DNS-резолвером.

    aiohttp по умолчанию берёт aiodns/AsyncResolver, если тот установлен.
    На Windows pycares периодически отдаёт «DNS server returned answer with
    no data», поэтому используем ThreadedResolver (системный getaddrinfo).
    Это ещё и убирает зависимость поведения от того, попал ли aiodns в сборку.
    """
    aiohttp = _aio()
    connector = aiohttp.TCPConnector(
        resolver=aiohttp.ThreadedResolver(),
        limit=MAX_CONCURRENT_REQUESTS,
    )
    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT,
        connect=CONNECT_TIMEOUT,
    )
    return aiohttp.ClientSession(connector=connector, timeout=timeout)


async def _get_json(session: aiohttp.ClientSession, url: str, params: dict):
    """GET с повторами при сетевых сбоях.

    Возвращает распарсенный JSON. При неустранимой сетевой ошибке или
    4xx/5xx поднимает SteamApiError с ключом перевода.
    """
    last_exc: BaseException | None = None

    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)

                if resp.status == 403:
                    raise SteamApiError("error_api_key_invalid")

                if resp.status == 429:
                    raise SteamApiError("error_api_rate_limited")

                # 5xx — состояние сервера временное, пробуем ещё раз
                if 500 <= resp.status < 600:
                    last_exc = SteamApiError(
                        "error_steam_server", "HTTP %d" % resp.status
                    )
                    if attempt < REQUEST_RETRIES:
                        await _sleep_before_retry(attempt, "HTTP %d" % resp.status)
                        continue
                    raise last_exc

                raise SteamApiError("error_steam_server", "HTTP %d" % resp.status)

        except SteamApiError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not _is_retryable(exc) or attempt >= REQUEST_RETRIES:
                if _is_retryable(exc):
                    raise SteamApiError(
                        "error_network", _describe_network_error(exc)
                    ) from exc
                raise SteamApiError("error_network", type(exc).__name__) from exc

            last_exc = exc
            await _sleep_before_retry(attempt, _describe_network_error(exc))

    # сюда попадаем только если цикл исчерпан
    raise SteamApiError("error_network", _describe_network_error(last_exc))


async def _sleep_before_retry(attempt: int, reason: str):
    """Экспоненциальная задержка перед повтором."""
    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
    logger.warning(
        "Повтор запроса через %.1fс (%d/%d): %s",
        delay, attempt, REQUEST_RETRIES, reason
    )
    await asyncio.sleep(delay)


def _safe_progress(progress_cb, done: int, total: int):
    """Вызывает колбэк прогресса, не давая ему уронить загрузку."""
    try:
        progress_cb(done, total)
    except Exception:
        pass


async def _one_result(idx: int, awaitable):
    """Пара (idx, результат, ошибка) для as_completed.

    Ошибки возвращаются значением, как раньше делал
    gather(return_exceptions=True): одна упавшая игра не роняет весь список.
    """
    try:
        return idx, await awaitable, None
    except BaseException as exc:
        return idx, None, exc


class SteamAPIClient:
    """Клиент для взаимодействия со Steam Web API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        # НЕ создаём semaphore здесь — он будет создаваться в каждом методе

    async def verify_api_key(self) -> bool:
        """Проверяет валидность API ключа.

        False — только когда Steam ответил и ключ не подошёл.
        Сетевые сбои поднимают SteamApiError, чтобы не выдавать их за
        «недействительный ключ».
        """
        test_steam_id = "76561197960434622"
        semaphore = _get_semaphore()

        async with _make_session() as session:
            url = f"{STEAM_API_BASE}/{INTERFACE_USER}/GetPlayerSummaries/v2/"
            params = {
                "key": self.api_key,
                "steamids": test_steam_id
            }

            async with semaphore:
                data = await _get_json(session, url, params)
                return bool(data) and "response" in data

    async def get_player_summaries(self, steam_id: str) -> Dict[str, Any]:
        """Получает публичную информацию о пользователе Steam."""
        semaphore = _get_semaphore()

        async with _make_session() as session:
            url = f"{STEAM_API_BASE}/{INTERFACE_USER}/GetPlayerSummaries/v2/"
            params = {
                "key": self.api_key,
                "steamids": steam_id
            }

            async with semaphore:
                data = await _get_json(session, url, params)
                players = data.get("response", {}).get("players", [])
                if not players:
                    raise SteamApiError("error_profile_not_found")
                return players[0]

    async def get_owned_games(self, steam_id: str) -> List[Dict[str, Any]]:
        """Получает список игр пользователя."""
        semaphore = _get_semaphore()

        async with _make_session() as session:
            url = f"{STEAM_API_BASE}/{INTERFACE_PLAYER}/GetOwnedGames/v1/"
            params = {
                "key": self.api_key,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1,
                "format": "json"
            }

            async with semaphore:
                data = await _get_json(session, url, params)
                games = data.get("response", {}).get("games", [])
                if not games:
                    raise SteamApiError("error_games_empty")
                return games

    async def get_player_achievements(self, steam_id: str, appid: int) -> Dict[str, int]:
        """Получает информацию о достижениях игрока."""
        semaphore = _get_semaphore()

        try:
            async with _make_session() as session:
                url = f"{STEAM_API_BASE}/{INTERFACE_USER_STATS}/GetPlayerAchievements/v1/"
                params = {
                    "key": self.api_key,
                    "steamid": steam_id,
                    "appid": appid
                }

                async with semaphore:
                    data = await _get_json(session, url, params)
                    player_stats = data.get("playerstats", {})
                    if not player_stats.get("success", False):
                        return {"unlocked": 0, "total": 0}
                    achievements = player_stats.get("achievements", [])
                    unlocked = sum(1 for a in achievements if a.get("achieved", 0) == 1)
                    return {"unlocked": unlocked, "total": len(achievements)}
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Достижения — необязательные данные: одна ошибка не должна
            # обнулять весь список игр.
            logger.warning("Ошибка получения достижений для appid %s: %s", appid, e)
            return {"unlocked": 0, "total": 0}

    async def get_all_games(self, steam_id: str, progress_cb=None) -> List[Dict[str, Any]]:
        """Получает полную информацию обо всех играх.

        progress_cb(done, total) вызывается по мере готовности достижений
        по каждой игре; progress_cb(0, 0) — фаза без известного объёма
        (загрузка списка игр). Ошибки колбэка игнорируются: прогресс
        не должен ронять загрузку.
        """
        from datetime import datetime

        if progress_cb is not None:
            _safe_progress(progress_cb, 0, 0)

        games = await self.get_owned_games(steam_id)
        total = len(games)
        if progress_cb is not None:
            _safe_progress(progress_cb, 0, total)

        wrapped = [
            _one_result(idx, self.get_player_achievements(steam_id, game.get("appid")))
            for idx, game in enumerate(games)
        ]
        achievements_list: List[Any] = [None] * len(games)
        done = 0
        for coro in asyncio.as_completed(wrapped):
            # as_completed отдаёт awaitables, а не исходные таски —
            # индекс везёт обёртка _one_result
            idx, res, err = await coro
            achievements_list[idx] = err if err is not None else res
            done += 1
            if progress_cb is not None:
                _safe_progress(progress_cb, done, total)

        processed_games = []
        for game, achievements in zip(games, achievements_list):
            if isinstance(achievements, BaseException):
                achievements = {"unlocked": 0, "total": 0}

            playtime_forever = game.get("playtime_forever") or 0
            try:
                playtime_forever = int(playtime_forever)
            except (TypeError, ValueError):
                logger.warning("Некорректное playtime_forever=%r у appid %s",
                               game.get("playtime_forever"), game.get("appid"))
                playtime_forever = 0
            hours_decimal = round(playtime_forever / 60, 2)
            minutes_total = round(playtime_forever, 2)

            rtime_acquired = game.get("rtime_acquired", 0)
            if rtime_acquired:
                try:
                    acquired = datetime.fromtimestamp(rtime_acquired).strftime("%Y-%m-%d")
                except (ValueError, OverflowError, OSError, TypeError):
                    acquired = "?"
            else:
                acquired = "?"

            rtime_last_played = game.get("rtime_last_played", 0)
            if rtime_last_played:
                try:
                    last_played = datetime.fromtimestamp(rtime_last_played).strftime("%Y-%m-%d %H:%M")
                except (ValueError, OverflowError, OSError, TypeError):
                    last_played = "?"
            else:
                last_played = "?"

            # Примечание: Steam GetOwnedGames не возвращает поле is_free
            acquire_method = "?"

            processed_games.append({
                "appid": game.get("appid"),
                "name": game.get("name") or "?",
                "hours": hours_decimal,
                "minutes": minutes_total,
                "acquired": acquired,
                "achievements": achievements,
                "last_played": last_played,
                "acquire_method": acquire_method,
                "playtime_forever": playtime_forever,
            })

        processed_games.sort(key=lambda x: x["name"].lower())

        return processed_games
