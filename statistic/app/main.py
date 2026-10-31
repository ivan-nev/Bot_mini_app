"""FastAPI-сервис статистики проекта «Разработка УП» (Vikunja).

Эндпоинты:
- GET /            — дашборд с графиками;
- GET /api/meta    — информация о проекте и доступном диапазоне дат;
- GET /api/stats   — статистика: период, интервал (day/week/month), разрезы по людям;
- GET /api/tasks   — задачи, попавшие в период;
- GET /health      — проверка работоспособности.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import stats as stats_mod
from .config import settings
from .vikunja_client import VikunjaError, client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("statistic")


async def _cache_refresher() -> None:
    """Фоновое обновление кэша задач: пользователи почти не ждут Vikunja."""
    interval = settings.cache_ttl if settings.cache_ttl > 0 else 300
    while True:
        if settings.token_configured:
            try:
                await client.get_tasks(force_refresh=True)
                logger.info("Фоновое обновление кэша задач завершено")
            except VikunjaError as exc:
                logger.warning("Фоновое обновление кэша не удалось: %s", exc)
            except Exception:
                logger.exception("Непредвиденная ошибка фонового обновления кэша")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    refresher = asyncio.create_task(_cache_refresher())
    yield
    refresher.cancel()
    with suppress(asyncio.CancelledError):
        await refresher


app = FastAPI(title="Статистика Разработка УП", version="1.0.0", lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_projects_cache: dict = {"id": None, "data": None, "ts": 0.0}


def _parse_date(value: str | None, default: dt.date | None = None) -> dt.date | None:
    if value is None or value == "":
        return default
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Неверная дата: {value!r}, ожидается YYYY-MM-DD") from exc


async def _get_project() -> dict:
    """Проект с кэшем на 10 минут."""
    now = time.time()
    if _projects_cache["id"] == settings.project_id and _projects_cache["data"] and now - _projects_cache["ts"] < 600:
        return _projects_cache["data"]
    try:
        data = await client.fetch_project(settings.project_id)
    except VikunjaError:
        data = {
            "id": settings.project_id,
            "title": f"Проект {settings.project_id}",
            "identifier": "",
        }
    _projects_cache.update({"id": settings.project_id, "data": data, "ts": now})
    return data


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "token_configured": settings.token_configured}


@app.get("/api/meta")
async def api_meta() -> dict:
    try:
        tasks = await client.get_tasks()
    except VikunjaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    min_date, max_date = stats_mod.data_bounds(tasks, settings.timezone)
    project = await _get_project()
    today = dt.date.today()

    return {
        "project": {
            "id": settings.project_id,
            "title": project.get("title", "?"),
            "identifier": project.get("identifier", ""),
        },
        "tasks_total": len(tasks),
        "min_date": min_date.isoformat() if min_date else None,
        "max_date": max_date.isoformat() if max_date else None,
        "default_start": (min_date or today).isoformat(),
        "default_end": (max_date or today).isoformat(),
        "timezone": settings.timezone,
        "token_configured": settings.token_configured,
    }


@app.get("/api/stats")
async def api_stats(
    start: str | None = Query(default=None, description="Начало периода, YYYY-MM-DD"),
    end: str | None = Query(default=None, description="Конец периода, YYYY-MM-DD"),
    interval: str = Query(default="day", pattern="^(day|week|month)$"),
    refresh: bool = Query(default=False, description="Принудительно перечитать данные из Vikunja"),
) -> dict:
    if interval not in stats_mod.INTERVALS:
        raise HTTPException(status_code=422, detail=f"interval должен быть одним из {stats_mod.INTERVALS}")

    try:
        tasks = await client.get_tasks(force_refresh=refresh)
    except VikunjaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    min_date, max_date = stats_mod.data_bounds(tasks, settings.timezone)
    today = dt.date.today()

    start_date = _parse_date(start, min_date or today)
    end_date = _parse_date(end, max_date or today)
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start не может быть позже end")

    try:
        result = stats_mod.compute_stats(tasks, start_date, end_date, interval, settings.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    project = await _get_project()
    result.update(
        {
            "project": {
                "id": settings.project_id,
                "title": project.get("title", "?"),
            },
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "timezone": settings.timezone,
            "meta": {
                "tasks_total": len(tasks),
                "source": "cache" if not refresh else "vikunja",
            },
        }
    )
    return result


@app.get("/api/tasks")
async def api_tasks(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    refresh: bool = Query(default=False, description="Принудительно перечитать данные из Vikunja"),
) -> dict:
    try:
        tasks = await client.get_tasks(force_refresh=refresh)
    except VikunjaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    min_date, max_date = stats_mod.data_bounds(tasks, settings.timezone)
    today = dt.date.today()
    start_date = _parse_date(start, min_date or today)
    end_date = _parse_date(end, max_date or today)
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start не может быть позже end")

    period_tasks = stats_mod.tasks_in_period(tasks, start_date, end_date, settings.timezone)
    items = [
        {
            "id": task.get("id"),
            "identifier": task.get("identifier", ""),
            "title": task.get("title", ""),
            "done": bool(task.get("done")),
            "created": task.get("created"),
            "done_at": task.get("done_at"),
            "assignees": [a.get("username") for a in (task.get("assignees") or [])],
            "labels": [lab.get("title") for lab in (task.get("labels") or [])],
            "priority": task.get("priority", 0),
        }
        for task in period_tasks
    ]
    return {"period": {"start": start_date.isoformat(), "end": end_date.isoformat()}, "tasks": items}
