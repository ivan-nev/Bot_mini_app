"""Проверка модуля расчёта статистики на синтетических данных.

Запуск:  python tests/test_stats.py
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import stats  # noqa: E402


def make_task(task_id, title, assignees, done, created, done_at=None, updated=None, labels=None):
    return {
        "id": task_id,
        "title": title,
        "done": done,
        "created": created,
        "done_at": done_at,
        "updated": updated or done_at or created,
        "assignees": [{"username": a} for a in assignees],
        "labels": [{"title": lab} for lab in (labels or [])],
    }


def test_interval_buckets():
    start = dt.date(2025, 11, 14)
    end = dt.date(2025, 12, 4)

    days = stats.build_buckets(start, end, "day")
    assert len(days) == 21, len(days)
    assert days[0] == dt.date(2025, 11, 14)
    assert days[-1] == dt.date(2025, 12, 4)

    weeks = stats.build_buckets(start, end, "week")
    assert weeks == [dt.date(2025, 11, 10), dt.date(2025, 11, 17),
                     dt.date(2025, 11, 24), dt.date(2025, 12, 1)], weeks

    months = stats.build_buckets(start, end, "month")
    assert months == [dt.date(2025, 11, 1), dt.date(2025, 12, 1)], months

    print("OK: интервалы день/неделя/месяц")


def test_parse_and_empty_dates():
    assert stats.parse_dt("2025-11-18T05:01:33Z").year == 2025
    assert stats.parse_dt("0001-01-01T00:00:00Z") is None
    assert stats.parse_dt(None) is None
    assert stats.parse_dt("2025-11-18T05:01:33+05:00").hour == 0  # приведено к UTC
    print("OK: разбор дат, пустые даты Vikunja игнорируются")


def test_person_stats():
    tasks = [
        # Аюпов: 3 выполненные в периоде, одна вне периода
        make_task(1, "t1", ["Аюпов"], True, "2025-11-14T04:00:00Z", "2025-11-18T05:00:00Z"),
        make_task(2, "t2", ["Аюпов"], True, "2025-11-19T04:00:00Z", "2025-11-21T05:00:00Z"),
        make_task(3, "t3", ["Аюпов"], True, "2025-11-24T04:00:00Z", "2025-11-25T05:00:00Z"),
        make_task(4, "t4", ["Аюпов"], True, "2025-10-01T04:00:00Z", "2025-10-02T05:00:00Z"),
        # Коротаев: 2 выполненные
        make_task(5, "t5", ["Коротаев"], True, "2025-11-17T04:00:00Z", "2025-11-18T05:00:00Z"),
        make_task(6, "t6", ["Коротаев"], True, "2025-11-20T04:00:00Z", "2025-11-22T05:00:00Z"),
        # совместная задача — засчитывается обоим
        make_task(7, "t7", ["Аюпов", "Коротаев"], True, "2025-11-26T04:00:00Z", "2025-11-28T05:00:00Z"),
        # без исполнителя
        make_task(8, "t8", [], True, "2025-11-27T04:00:00Z", "2025-11-29T05:00:00Z"),
        # открытые сейчас
        make_task(9, "t9", ["Поносов"], False, "2025-11-20T04:00:00Z"),
        make_task(10, "t10", [], False, "2025-11-21T04:00:00Z"),
    ]

    result = stats.compute_stats(tasks, dt.date(2025, 11, 14), dt.date(2025, 11, 30), "week", "UTC")

    # сводные итоги: 7 выполнено в периоде (t1,t2,t3,t5,t6,t7,t8), t4 — вне
    assert result["summary"]["total_done"] == 7, result["summary"]
    assert result["summary"]["total_created"] == 9, result["summary"]  # все, кроме t4
    assert result["summary"]["open_now"] == 2

    people = result["people"]
    # Аюпов: t1,t2,t3 + совместная t7 = 4
    assert people["Аюпов"]["total_done"] == 4, people
    # Коротаев: t5,t6 + совместная t7 = 3
    assert people["Коротаев"]["total_done"] == 3, people
    assert people[stats.UNASSIGNED]["total_done"] == 1
    assert people["Поносов"]["total_done"] == 0
    assert people["Поносов"]["open_now"] == 1

    # доли
    assert people["Аюпов"]["share_done_pct"] == round(4 / 7 * 100, 1)

    # раскладка по неделям: недели с 10.11, 17.11, 24.11
    assert result["labels"] == ["10.11", "17.11", "24.11"], result["labels"]
    # 17.11: t1,t2,t5,t6; 24.11: t3,t7,t8
    assert result["totals"]["done"] == [0, 4, 3], result["totals"]["done"]
    assert result["totals"]["cumulative_done"] == [0, 4, 7]

    # среднее время выполнения для Аюпова: t1 97ч, t2 49ч, t3 25ч, t7 49ч
    avg = people["Аюпов"]["avg_completion_hours"]
    assert abs(avg - (97 + 49 + 25 + 49) / 4) < 0.01, avg

    print("OK: статистика по людям, совместные задачи, без исполнителя, открытые")


def test_week_and_month_labels():
    start = dt.date(2025, 11, 14)
    end = dt.date(2025, 11, 30)
    weeks = stats.build_buckets(start, end, "week")
    assert stats.full_label_for(weeks[0], "week").startswith("нед. с 10.11.2025")

    months = stats.build_buckets(dt.date(2025, 11, 1), dt.date(2026, 2, 1), "month")
    assert months == [dt.date(2025, 11, 1), dt.date(2025, 12, 1),
                      dt.date(2026, 1, 1), dt.date(2026, 2, 1)]
    assert stats.label_for(months[1], "month") == "12.2025"
    assert stats.full_label_for(months[1], "month") == "дек 2025"

    print("OK: подписи недель/месяцев, переход года")


def test_tz_grouping():
    # задача закрыта в 02:00 UTC 19.11 = 07:00 +05 — попадает в 19.11 по локальному времени
    tasks = [make_task(1, "tz", ["Аюпов"], True, "2025-11-18T10:00:00Z", "2025-11-18T21:00:00Z")]
    utc = stats.compute_stats(tasks, dt.date(2025, 11, 18), dt.date(2025, 11, 19), "day", "UTC")
    yek = stats.compute_stats(tasks, dt.date(2025, 11, 18), dt.date(2025, 11, 19), "day", "Asia/Yekaterinburg")

    assert utc["totals"]["done"] == [1, 0], utc["totals"]["done"]
    assert yek["totals"]["done"] == [0, 1], yek["totals"]["done"]

    print("OK: учёт часового пояса при разбивке")


def test_done_at_fallback_to_updated():
    # done без done_at -> используем updated
    tasks = [make_task(1, "f", ["Аюпов"], True, "2025-11-14T04:00:00Z", None, "2025-11-20T05:00:00Z")]
    result = stats.compute_stats(tasks, dt.date(2025, 11, 14), dt.date(2025, 11, 30), "week", "UTC")
    assert result["summary"]["total_done"] == 1
    print("OK: fallback done_at -> updated")


def test_tasks_in_period():
    tasks = [
        make_task(1, "в периоде", ["Аюпов"], True, "2025-11-14T04:00:00Z", "2025-11-18T05:00:00Z"),
        make_task(2, "вне периода", ["Аюпов"], True, "2025-10-01T04:00:00Z", "2025-10-02T05:00:00Z"),
        make_task(3, "создана в периоде, открыта", [], False, "2025-11-20T04:00:00Z"),
    ]
    result = stats.tasks_in_period(tasks, dt.date(2025, 11, 14), dt.date(2025, 11, 30), "UTC")
    assert [t["id"] for t in result] == [1, 3]
    print("OK: отбор задач за период")


def test_canonical_machine():
    cases = {
        "Пума": "Пума", "пума": "Пума", "puma": "Пума", "Пума 1": "Пума",
        "puma1": "Пума", "пума4": "Пума",
        "Фокус": "Фокус", "фокус": "Фокус", "Focus2": "Фокус",
        "Саста 3м": "Саста 3м", "са3м": "Саста 3м",
        "са 2": "Саста 2", "са2": "Саста 2",
        "Фрезер ЧПУ Минкс": "Фрезер ЧПУ Минкс", "mynx": "Фрезер ЧПУ Минкс",
        "Т-500": "Т-500", "т-500": "Т-500", "т500": "Т-500",
        "т630": "Т630",
        "Солекс": "Солекс", "solex": "Солекс",
        "протон500": "Протон 500",
        "фрезер SMV": "Фрезер SMV",
        "ВФЛ": "ВФЛ", "РСК": "РСК", "бурсервис": "Бурсервис",
    }
    for src, expected in cases.items():
        got = stats.canonical_machine(src)
        assert got == expected, f"{src!r} -> {got!r}, ожидалось {expected!r}"
    print("OK: нормализация названий станков")


def test_machine_stats():
    tasks = [
        make_task(1, "t1", ["Аюпов"], True, "2025-11-14T04:00:00Z", "2025-11-18T05:00:00Z",
                  labels=["Пума", "пума"]),  # дубли объединяются в одну Пума
        make_task(2, "t2", ["Аюпов"], True, "2025-11-19T04:00:00Z", "2025-11-21T05:00:00Z",
                  labels=["solex"]),
        make_task(3, "t3", ["Коротаев"], True, "2025-11-24T04:00:00Z", "2025-11-25T05:00:00Z",
                  labels=["mynx"]),
        make_task(4, "t4", ["Поносов"], True, "2025-11-26T04:00:00Z", "2025-11-28T05:00:00Z"),
        make_task(5, "t5", ["Аюпов"], False, "2025-11-20T04:00:00Z", labels=["Пума", "solex"]),
    ]
    result = stats.compute_stats(tasks, dt.date(2025, 11, 14), dt.date(2025, 11, 30), "week", "UTC")
    machines = result["machines"]

    assert set(machines) == {"Пума", "Солекс", "Фрезер ЧПУ Минкс"}, machines
    # недели: 10.11, 17.11, 24.11
    assert machines["Пума"]["done"] == [0, 1, 0], machines["Пума"]
    assert machines["Солекс"]["done"] == [0, 1, 0], machines["Солекс"]
    assert machines["Фрезер ЧПУ Минкс"]["done"] == [0, 0, 1], machines["Фрезер ЧПУ Минкс"]
    assert machines["Пума"]["total_done"] == 1  # дубль пума/Пума не задваивается
    print("OK: статистика по станкам с объединением меток")


if __name__ == "__main__":
    test_interval_buckets()
    test_parse_and_empty_dates()
    test_person_stats()
    test_week_and_month_labels()
    test_tz_grouping()
    test_done_at_fallback_to_updated()
    test_tasks_in_period()
    test_canonical_machine()
    test_machine_stats()
    print("\nВсе тесты пройдены.")
