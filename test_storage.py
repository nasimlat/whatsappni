#coding=utf-8
"""Unit tests for the pure analytics storage layer (storage.py).

storage.py currently ships as an empty stub (see storage.py) so these
imports succeed; every test below is expected to FAIL on an assertion
(comparing the stub's None/False return against the spec-defined value),
not on ModuleNotFoundError. Real logic lands in the GREEN phase.

Priority order: AC (happy path) first, then EC (edge cases), then ERR
(error cases) — see docstrings for the spec criterion each test covers.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from storage import (
    get_db_path,
    get_stats,
    get_user,
    init_db,
    is_admin,
    record_activity,
)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    init_db(connection)
    yield connection
    connection.close()


def test_ac1_first_seen_creates_row_with_count_one(conn):
    """AC-1: первое обращение user_id создаёт запись с first_seen == last_seen == now, messages_count == 1."""
    now = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)

    record_activity(conn, 111, now)

    assert get_user(conn, 111) == {
        "user_id": 111,
        "first_seen": now.isoformat(),
        "last_seen": now.isoformat(),
        "messages_count": 1,
    }


def test_ac2_repeat_visit_updates_last_seen_and_increments_count_without_changing_first_seen(conn):
    """AC-2: повторное обращение обновляет last_seen и messages_count += 1; first_seen не меняется."""
    first_seen = datetime(2026, 7, 20, 9, 0, 0, tzinfo=timezone.utc)
    second_seen = datetime(2026, 7, 22, 15, 30, 0, tzinfo=timezone.utc)

    record_activity(conn, 222, first_seen)
    record_activity(conn, 222, second_seen)

    assert get_user(conn, 222) == {
        "user_id": 222,
        "first_seen": first_seen.isoformat(),
        "last_seen": second_seen.isoformat(),
        "messages_count": 2,
    }


def test_ac4_get_stats_returns_total_and_active_counts(conn):
    """AC-4: get_stats возвращает total (все строки users) и active (last_seen >= now - 7 дней)."""
    now = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)
    recent = now - timedelta(days=1)
    stale = now - timedelta(days=30)

    record_activity(conn, 1, recent)
    record_activity(conn, 2, stale)
    record_activity(conn, 3, recent)

    assert get_stats(conn, now, days=7) == {"total": 3, "active": 2}


def test_ac4_is_admin_true_when_user_id_matches_admin_id_env():
    """AC-4: is_admin возвращает True, когда user_id совпадает со значением ADMIN_ID."""
    assert is_admin(777, "777") is True


def test_ac6_get_db_path_reads_env_or_falls_back_to_default(monkeypatch):
    """AC-6: путь к БД берётся из DB_PATH, либо дефолт "users.db", если переменная не задана."""
    monkeypatch.setenv("DB_PATH", "/tmp/custom_users.db")
    assert get_db_path() == "/tmp/custom_users.db"

    monkeypatch.delenv("DB_PATH", raising=False)
    assert get_db_path() == "users.db"


def test_ec2_user_active_exactly_seven_days_ago_counts_as_active_inclusive_boundary(conn):
    """EC-2: last_seen == now - 7 дней (ровно) считается активным (граница включительная)."""
    now = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)
    exactly_seven_days_ago = now - timedelta(days=7)

    record_activity(conn, 555, exactly_seven_days_ago)

    assert get_stats(conn, now, days=7) == {"total": 1, "active": 1}


@pytest.mark.parametrize(
    "admin_id_env",
    [
        pytest.param(None, id="EC-1-admin-id-unset"),
        pytest.param("", id="EC-1-admin-id-empty"),
        pytest.param("not-a-number", id="ERR-1-admin-id-not-integer"),
    ],
)
def test_is_admin_returns_false_when_admin_id_invalid_or_missing(admin_id_env):
    """EC-1/ERR-1: ADMIN_ID не задан, пуст, либо не парсится как int -> никто не считается админом."""
    assert is_admin(111, admin_id_env) is False
