"""Асинхронный клиент API Vikunja с кэшированием на диск.

Особенности:
- страницы задач грузятся параллельно (до PAGE_CONCURRENCY одновременно);
- обновление кэша защищено блокировкой: параллельные запросы с refresh=1
  не приводят к повторной загрузке всех страниц из Vikunja;
- без токена работает офлайн-режим из кэша.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)

PAGE_CONCURRENCY = 6  # сколько страниц Vikunja грузим одновременно
RECENT_FETCH_WINDOW = 3.0  # сек: считаем только что сделанное обновление свежим


class VikunjaError(Exception):
    """Ошибка обращения к API Vikunja."""


class VikunjaClient:
    def __init__(self) -> None:
        self._api_prefix: str | None = None
        self._refresh_lock = asyncio.Lock()
        self._last_fetch_ts = 0.0

    # ------------------------------------------------------------------ #
    # низкоуровневые запросы
    # ------------------------------------------------------------------ #
    def _build_client(self) -> httpx.AsyncClient:
        """Общий клиент на серию запросов (переиспользует пул соединений)."""
        headers = {"Authorization": f"Bearer {settings.vikunja_token}"}
        return httpx.AsyncClient(
            base_url=settings.vikunja_base_url,
            timeout=settings.http_timeout,
            headers=headers,
        )

    async def _request(self, client: httpx.AsyncClient, path: str, params: dict | None = None) -> Any:
        """GET-запрос к Vikunja с автоподбором версии API."""
        if not settings.token_configured:
            raise VikunjaError(
                "Не задан VIKUNJA_TOKEN в .env. Создайте токен в настройках Vikunja "
                "(Настройки -> API токены) и впишите его в файл .env."
            )

        prefixes = (self._api_prefix,) if self._api_prefix else settings.vikunja_api_prefixes
        last_error: Exception | None = None
        for prefix in prefixes:
            url = f"{prefix}{path}"
            try:
                response = await client.get(url, params=params)
                if response.status_code == 404 and not self._api_prefix:
                    # возможно, другой префикс версии API
                    last_error = VikunjaError(f"404 на {url}")
                    continue
                response.raise_for_status()
                self._api_prefix = prefix
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                # 401/403 — токен неверен, пробовать другие префиксы смысла нет
                if exc.response.status_code in (401, 403):
                    raise VikunjaError(
                        f"Vikunja вернул {exc.response.status_code}: проверьте VIKUNJA_TOKEN."
                    ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
        raise VikunjaError(f"Не удалось обратиться к API Vikunja: {last_error}")

    @staticmethod
    def _extract_items(data: Any) -> list[dict]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            chunk = data.get("data") or data.get("items") or []
            return chunk if isinstance(chunk, list) else []
        return []

    @staticmethod
    def _total_pages(data: Any) -> int | None:
        if isinstance(data, dict):
            value = data.get("total_pages") or data.get("totalPages")
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return None

    async def fetch_project(self, project_id: int | None = None) -> dict:
        project_id = project_id or settings.project_id
        async with self._build_client() as client:
            return await self._request(client, f"/projects/{project_id}")

    async def fetch_tasks(self, project_id: int | None = None) -> list[dict]:
        """Все задачи проекта: первая страница + остальные параллельно."""
        project_id = project_id or settings.project_id
        per_page = 100

        async with self._build_client() as client:
            first = await self._request(
                client, f"/projects/{project_id}/tasks", {"page": 1, "per_page": per_page}
            )
            tasks = list(self._extract_items(first))
            total_pages = self._total_pages(first) or 1

            if total_pages > 1 and tasks:
                semaphore = asyncio.Semaphore(PAGE_CONCURRENCY)

                async def load_page(page: int) -> list[dict]:
                    async with semaphore:
                        try:
                            data = await self._request(
                                client,
                                f"/projects/{project_id}/tasks",
                                {"page": page, "per_page": per_page},
                            )
                            return self._extract_items(data)
                        except VikunjaError as exc:
                            logger.warning("Страница %s не загрузилась: %s", page, exc)
                            return []

                chunks = await asyncio.gather(
                    *(load_page(page) for page in range(2, total_pages + 1))
                )
                for chunk in chunks:
                    tasks.extend(chunk)

            return tasks

    # ------------------------------------------------------------------ #
    # кэширование
    # ------------------------------------------------------------------ #
    def _cache_file(self, project_id: int) -> Path:
        return settings.cache_dir / f"tasks_{project_id}.json"

    def _read_cache(self, project_id: int) -> list[dict] | None:
        cache_file = self._cache_file(project_id)
        if not cache_file.exists():
            return None
        try:
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Не удалось прочитать кэш %s", cache_file)
            return None
        fetched_at = payload.get("fetched_at", 0)
        tasks = payload.get("tasks")
        if not isinstance(tasks, list):
            return None
        if settings.cache_ttl <= 0:
            return tasks
        if time.time() - float(fetched_at) > settings.cache_ttl:
            return None
        return tasks

    def _write_cache(self, project_id: int, tasks: list[dict]) -> None:
        if settings.cache_ttl <= 0:
            return
        try:
            settings.cache_dir.mkdir(parents=True, exist_ok=True)
            payload = {"fetched_at": time.time(), "tasks": tasks}
            self._cache_file(project_id).write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("Не удалось записать кэш: %s", exc)

    async def get_tasks(self, project_id: int | None = None, force_refresh: bool = False) -> list[dict]:
        """Задачи с учётом кэша.

        Параллельные запросы на обновление схлопываются: загрузку из Vikunja
        выполняет один, остальные дожидаются и берут свежий кэш.
        """
        project_id = project_id or settings.project_id

        cached = self._read_cache(project_id)
        if cached is not None and not force_refresh:
            return cached

        async with self._refresh_lock:
            if force_refresh:
                # пока ждали блокировку, другой запрос мог уже всё обновить
                if time.time() - self._last_fetch_ts < RECENT_FETCH_WINDOW:
                    cached = self._read_cache(project_id)
                    if cached is not None:
                        return cached
            else:
                # под блокировкой кэш мог появиться/обновиться
                cached = self._read_cache(project_id)
                if cached is not None:
                    return cached

            if not settings.token_configured:
                raise VikunjaError(
                    "Нет токена VIKUNJA_TOKEN и нет кэша задач. "
                    "Впишите токен в .env и перезапустите сервис."
                )

            tasks = await self.fetch_tasks(project_id)
            self._last_fetch_ts = time.time()
            self._write_cache(project_id, tasks)
            logger.info("Загружено задач из Vikunja: %s шт.", len(tasks))
            return tasks


client = VikunjaClient()
