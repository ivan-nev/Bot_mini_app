"""Расчёт статистики по задачам Vikunja.

Основные понятия:
- «выполнено» (done) — задачи, закрытые в выбранном периоде (по done_at);
- «создано» (created) — задачи, созданные в выбранном периоде;
- интервал разбивки: день / неделя (с понедельника) / месяц;
- если у задачи несколько исполнителей, она засчитывается каждому.
"""
from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from zoneinfo import ZoneInfo

INTERVALS = ("day", "week", "month")
MONTH_NAMES = [
    "", "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]
UNASSIGNED = "Без исполнителя"


# --------------------------------------------------------------------- #
# вспомогательные функции работы с датами
# --------------------------------------------------------------------- #
def parse_dt(value) -> dt.datetime | None:
    """Разбор даты Vikunja в aware datetime (UTC).

    Пустые даты Vikunja вида 0001-01-01T00:00:00Z считаются отсутствующими.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.year <= 1:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def local_datetime(value, tz_name: str) -> dt.datetime | None:
    """UTC-дата в указанный часовой пояс."""
    parsed = parse_dt(value)
    if parsed is None:
        return None
    return parsed.astimezone(ZoneInfo(tz_name))


def interval_start(day: dt.date, interval: str) -> dt.date:
    """Начало интервала, содержащего day."""
    if interval == "day":
        return day
    if interval == "week":
        return day - dt.timedelta(days=day.weekday())
    if interval == "month":
        return day.replace(day=1)
    raise ValueError(f"Неизвестный интервал: {interval}")


def build_buckets(start: dt.date, end: dt.date, interval: str) -> list[dt.date]:
    """Все начала интервалов, покрывающие [start, end]."""
    buckets: list[dt.date] = []
    current = interval_start(start, interval)
    while current <= end:
        buckets.append(current)
        if interval == "day":
            current += dt.timedelta(days=1)
        elif interval == "week":
            current += dt.timedelta(days=7)
        else:
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    return buckets


def bucket_end(start: dt.date, interval: str) -> dt.date:
    """Последний день интервала с началом start."""
    if interval == "day":
        return start
    if interval == "week":
        return start + dt.timedelta(days=6)
    if current := dt.date(start.year + (1 if start.month == 12 else 0), (start.month % 12) + 1, 1):
        return current - dt.timedelta(days=1)
    raise ValueError(interval)


def label_for(start: dt.date, interval: str) -> str:
    """Короткая подпись интервала для осей графиков."""
    if interval == "day":
        return start.strftime("%d.%m")
    if interval == "week":
        return start.strftime("%d.%m")
    return f"{start.month:02d}.{start.year}"


def full_label_for(start: dt.date, interval: str) -> str:
    """Полная подпись интервала для подсказок."""
    if interval == "day":
        return start.strftime("%d.%m.%Y")
    if interval == "week":
        return f"нед. с {start.strftime('%d.%m.%Y')} по {bucket_end(start, interval).strftime('%d.%m.%Y')}"
    return f"{MONTH_NAMES[start.month]} {start.year}"


def bucket_index(day: dt.date, buckets: list[dt.date], interval: str) -> int | None:
    """Индекс интервала, в который попадает day, либо None."""
    start = interval_start(day, interval)
    try:
        idx = buckets.index(start)
    except ValueError:
        return None
    return idx


# --------------------------------------------------------------------- #
# работа с задачами
# --------------------------------------------------------------------- #
def task_assignees(task: dict) -> list[str]:
    """Список исполнителей задачи; пусто -> [Без исполнителя]."""
    names = [
        item.get("username", "")
        for item in (task.get("assignees") or [])
        if item.get("username")
    ]
    return names or [UNASSIGNED]


def canonical_machine(title: str) -> str:
    """Нормализация названия станка (метки): объединяем похожие написания.

    Примеры: 'пума'/'puma'/'Пума 1'/'пума4' -> 'Пума'; 'са3м' -> 'Саста 3м';
    'mynx' -> 'Фрезер ЧПУ Минкс'; 'solex' -> 'Солекс'.
    """
    if not title:
        return ""
    raw = title.strip()
    low = raw.lower().replace("ё", "е")
    key = re.sub(r"[\s\-]+", "", low)

    if "пума" in low or "puma" in low:
        return "Пума"
    if "фокус" in low or "focus" in low:
        return "Фокус"
    if "саста" in low:
        return "Саста 2" if ("саста2" in key or "саста 2" in low) else "Саста 3м"
    if key in ("са3м", "са 3м", "саста3м"):
        return "Саста 3м"
    if key in ("са2", "са 2", "саста2"):
        return "Саста 2"
    if "минкс" in low or "mynx" in low or "миникс" in low:
        return "Фрезер ЧПУ Минкс"
    if key in ("т500", "т 500"):
        return "Т-500"
    if key in ("т630", "т 630"):
        return "Т630"
    if "солекс" in low or "solex" in low:
        return "Солекс"
    if "протон" in low:
        return "Протон 500"
    if key in ("фрезерsmv", "фрезерсмв"):
        return "Фрезер SMV"
    if low == "вфл":
        return "ВФЛ"
    if low == "рск":
        return "РСК"
    if low == "эрозионный":
        return "Эрозионный"
    if low == "бурсервис":
        return "Бурсервис"
    return raw


def task_machines(task: dict) -> list[str]:
    """Канонические названия станков (меток) задачи без дублей."""
    names = {
        canonical_machine(lab.get("title", ""))
        for lab in (task.get("labels") or [])
        if lab.get("title")
    }
    return sorted(name for name in names if name)


def task_done_at(task: dict, tz_name: str) -> dt.datetime | None:
    """Локальная дата закрытия задачи.

    Если задача закрыта, но done_at не заполнен — используем updated.
    """
    if task.get("done") and (value := task.get("done_at")):
        parsed = local_datetime(value, tz_name)
        if parsed is not None:
            return parsed
    if task.get("done"):
        return local_datetime(task.get("updated"), tz_name)
    return None


def task_created_at(task: dict, tz_name: str) -> dt.datetime | None:
    return local_datetime(task.get("created"), tz_name)


def in_period(value: dt.datetime | None, start: dt.date, end: dt.date) -> bool:
    return value is not None and start <= value.date() <= end


def data_bounds(tasks: list[dict], tz_name: str) -> tuple[dt.date | None, dt.date | None]:
    """Минимальная и максимальная даты активности в проекте."""
    dates: list[dt.date] = []
    for task in tasks:
        for value in (task.get("created"), task.get("updated"), task.get("done_at")):
            parsed = local_datetime(value, tz_name)
            if parsed is not None:
                dates.append(parsed.date())
    if not dates:
        return None, None
    return min(dates), max(dates)


def compute_stats(
    tasks: list[dict],
    start: dt.date,
    end: dt.date,
    interval: str,
    tz_name: str,
) -> dict:
    """Основная статистика: сводные ряды + разрезы по исполнителям."""
    if interval not in INTERVALS:
        raise ValueError(f"interval должен быть одним из {INTERVALS}")

    buckets = build_buckets(start, end, interval)
    labels = [label_for(b, interval) for b in buckets]
    full_labels = [full_label_for(b, interval) for b in buckets]
    size = len(buckets)

    # сводные ряды (каждая задача считается один раз)
    done_total = [0] * size
    created_total = [0] * size

    # ряды по исполнителям
    person_done: dict[str, list[int]] = defaultdict(lambda: [0] * size)
    person_created: dict[str, list[int]] = defaultdict(lambda: [0] * size)

    person_done_sum: dict[str, int] = defaultdict(int)
    person_created_sum: dict[str, int] = defaultdict(int)
    person_open_now: dict[str, int] = defaultdict(int)
    person_duration_hours: dict[str, list[float]] = defaultdict(list)

    # ряды по станкам (меткам задач)
    machine_done: dict[str, list[int]] = defaultdict(lambda: [0] * size)
    machine_created: dict[str, list[int]] = defaultdict(lambda: [0] * size)
    machine_done_sum: dict[str, int] = defaultdict(int)
    machine_created_sum: dict[str, int] = defaultdict(int)

    total_done = 0
    total_created = 0
    open_tasks = 0  # уникальные открытые задачи (независимо от числа исполнителей)
    durations_hours: list[float] = []

    for task in tasks:
        assignees = task_assignees(task)
        machines = task_machines(task)

        created = task_created_at(task, tz_name)
        if in_period(created, start, end):
            idx = bucket_index(created.date(), buckets, interval)
            if idx is not None:
                created_total[idx] += 1
                total_created += 1
                for name in assignees:
                    person_created[name][idx] += 1
                    person_created_sum[name] += 1
                for machine in machines:
                    machine_created[machine][idx] += 1
                    machine_created_sum[machine] += 1

        done = task_done_at(task, tz_name)
        if in_period(done, start, end):
            idx = bucket_index(done.date(), buckets, interval)
            if idx is not None:
                done_total[idx] += 1
                total_done += 1
                for name in assignees:
                    person_done[name][idx] += 1
                    person_done_sum[name] += 1
                for machine in machines:
                    machine_done[machine][idx] += 1
                    machine_done_sum[machine] += 1

                if created is not None and (done - created).total_seconds() >= 0:
                    hours = (done - created).total_seconds() / 3600.0
                    durations_hours.append(hours)
                    for name in assignees:
                        person_duration_hours[name].append(hours)

        # открытые сейчас — независимо от периода
        if not task.get("done"):
            open_tasks += 1
            for name in assignees:
                person_open_now[name] += 1

    # накопительные итоги внутри периода
    cumulative_done = []
    cumulative_created = []
    acc_d = acc_c = 0
    for d, c in zip(done_total, created_total):
        acc_d += d
        acc_c += c
        cumulative_done.append(acc_d)
        cumulative_created.append(acc_c)

    people = {}
    all_names = set(person_done_sum) | set(person_created_sum) | set(person_open_now)
    for name in sorted(all_names, key=lambda n: (-person_done_sum.get(n, 0), n)):
        durations = person_duration_hours.get(name, [])
        people[name] = {
            "done": person_done.get(name, [0] * size),
            "created": person_created.get(name, [0] * size),
            "total_done": person_done_sum.get(name, 0),
            "total_created": person_created_sum.get(name, 0),
            "open_now": person_open_now.get(name, 0),
            "share_done_pct": round(person_done_sum.get(name, 0) / total_done * 100, 1)
            if total_done
            else 0.0,
            "avg_completion_hours": round(sum(durations) / len(durations), 1)
            if durations
            else None,
        }

    machines = {}
    for name in sorted(set(machine_done_sum) | set(machine_created_sum),
                       key=lambda n: (-machine_done_sum.get(n, 0), n)):
        machines[name] = {
            "done": machine_done.get(name, [0] * size),
            "created": machine_created.get(name, [0] * size),
            "total_done": machine_done_sum.get(name, 0),
            "total_created": machine_created_sum.get(name, 0),
        }

    return {
        "interval": interval,
        "labels": labels,
        "full_labels": full_labels,
        "totals": {
            "done": done_total,
            "created": created_total,
            "cumulative_done": cumulative_done,
            "cumulative_created": cumulative_created,
        },
        "people": people,
        "machines": machines,
        "summary": {
            "total_done": total_done,
            "total_created": total_created,
            "open_now": open_tasks,
            "avg_completion_hours": round(sum(durations_hours) / len(durations_hours), 1)
            if durations_hours
            else None,
        },
    }


def tasks_in_period(tasks: list[dict], start: dt.date, end: dt.date, tz_name: str) -> list[dict]:
    """Задачи, активные в периоде (созданы или закрыты в нём)."""
    result = []
    for task in tasks:
        created = task_created_at(task, tz_name)
        done = task_done_at(task, tz_name)
        if in_period(created, start, end) or in_period(done, start, end):
            result.append(task)
    result.sort(
        key=lambda t: max(
            (parse_dt(t.get("created")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)),
            (parse_dt(t.get("done_at")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)),
        )
    )
    return result
