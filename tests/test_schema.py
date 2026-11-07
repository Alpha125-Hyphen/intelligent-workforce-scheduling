import sqlite3
from src.schema import SCHEMA


def test_schema_creates_core_tables():
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    tables = {
        row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    expected = {
        "employee", "team", "skill", "shift_template", "shift_assignment",
        "leave_request", "holiday_calendar", "attendance_event",
        "coverage_requirement", "swap_request", "employee_skill",
        "team_membership", "audit_event"
    }
    assert expected.issubset(tables)
