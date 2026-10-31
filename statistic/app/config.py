"""Конфигурация сервиса статистики Vikunja.

Все параметры читаются из переменных окружения (файл .env в корне проекта).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    # Адрес Vikunja и учётные данные
    vikunja_base_url: str = field(
        default_factory=lambda: os.getenv("VIKUNJA_BASE_URL", "https://vikunja.ru").rstrip("/")
    )
    # Публичный адрес веб-интерфейса Vikunja (для ссылок на задачи в браузере).
    # Если не задан — используется vikunja_base_url.
    vikunja_public_url: str = field(
        default_factory=lambda: os.getenv("VIKUNJA_PUBLIC_URL", "").rstrip("/")
    )
    vikunja_token: str = field(default_factory=lambda: os.getenv("VIKUNJA_TOKEN", ""))
    # Префиксы API в порядке предпочтения (v2 -> v1), выбирается автоматически
    vikunja_api_prefixes: tuple[str, ...] = ("/api/v2", "/api/v1")
    # Проект «Разработка УП»
    project_id: int = field(default_factory=lambda: int(os.getenv("PROJECT_ID", "1")))

    # Часовой пояс, в котором считаются интервалы день/неделя/месяц
    timezone: str = field(default_factory=lambda: os.getenv("TZ", "UTC"))

    # Базовая HTTP-аутентификация дашборда (пусто — аутентификация отключена)
    auth_user: str = field(default_factory=lambda: os.getenv("AUTH_USER", ""))
    auth_pass: str = field(default_factory=lambda: os.getenv("AUTH_PASS", ""))

    # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    # Кэш задач (секунды); 0 — не кэшировать
    cache_ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL", "300")))
    cache_dir: Path = field(
        default_factory=lambda: Path(os.getenv("CACHE_DIR", str(BASE_DIR / "cache")))
    )

    # HTTP-клиент Vikunja
    http_timeout: float = field(default_factory=lambda: float(os.getenv("HTTP_TIMEOUT", "30")))

    @property
    def token_configured(self) -> bool:
        return bool(self.vikunja_token) and self.vikunja_token != "YOUR_API_TOKEN_HERE"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.auth_user) and bool(self.auth_pass)

    @property
    def vikunja_web_url(self) -> str:
        """URL веб-интерфейса Vikunja для ссылок на задачи из браузера."""
        return self.vikunja_public_url or self.vikunja_base_url


settings = Settings()
