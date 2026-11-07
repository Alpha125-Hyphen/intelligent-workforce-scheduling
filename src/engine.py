import csv
import json
import random
import sqlite3
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

from .config import (
    DB_PATH, DATA_DIR, OUTPUT_DIR, GROUND_TRUTH_DIR, SEED, START_DATE,
    DAYS, EMPLOYEE_COUNT, TEAM_COUNT, LEAVE_REQUEST_COUNT,
    WEEKLY_HOUR_CAP, MIN_REST_HOURS
)
from .schema import SCHEMA

fake = Faker("en_IN")


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def reset_database():
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = connect()
    con.executescript(SCHEMA)
    con.commit()
    con.close()


def iso_dt(d, t):
    return datetime.combine(d, t).isoformat(sep=" ")


def shift_bounds(day, start_str, end_str):
    start_t = time.fromisoformat(start_str)
    end_t = time.fromisoformat(end_str)
    start = datetime.combine(day, start_t)
    end = datetime.combine(day, end_t)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def generate_master_data(con):
    rng = random.Random(SEED)
    Faker.seed(SEED)
    fake.seed_instance(SEED)

    departments = ["Operations", "Customer Support", "IT Services", "Logistics", "Quality"]
    teams = []
    for i in range(1, TEAM_COUNT + 1):
        teams.append((f"TEAM-{i:03d}", f"Team {i:03d}", rng.choice(departments)))
    con.executemany("INSERT INTO team VALUES (?,?,?)", teams)

    skill_names = [
        "Operations", "Python", "SQL", "Cloud", "Networking",
        "Customer Support", "Quality Assurance", "Safety"
    ]
    con.executemany(
        "INSERT INTO skill VALUES (?,?,?)",
        [(f"SKL-{i:03d}", name, f"Synthetic skill: {name}") for i, name in enumerate(skill_names, 1)]
    )
    skill_ids = {name: f"SKL-{i:03d}" for i, name in enumerate(skill_names, 1)}

    templates = [
        ("TPL-M", "MORNING", "06:00", "14:00", 8.0),
        ("TPL-E", "EVENING", "14:00", "22:00", 8.0),
        ("TPL-N", "NIGHT", "22:00", "06:00", 8.0),
    ]
    con.executemany("INSERT INTO shift_template VALUES (?,?,?,?,?)", templates)

    employee_rows, membership_rows, employee_skill_rows = [], [], []
    team_specialty = {}
    specialties = skill_names[1:]
    for team_index in range(1, TEAM_COUNT + 1):
        team_specialty[f"TEAM-{team_index:03d}"] = specialties[(team_index - 1) % len(specialties)]

    for i in range(1, EMPLOYEE_COUNT + 1):
        employee_id = f"EMP-{i:06d}"
        team_num = ((i - 1) % TEAM_COUNT) + 1
        team_id = f"TEAM-{team_num:03d}"
        name = fake.name()
        email = f"employee{i:06d}@example.test"
        hire_date = date(2021, 1, 1) + timedelta(days=rng.randint(0, 1800))
        employee_rows.append((
            employee_id, name, email, hire_date.isoformat(), "ACTIVE", WEEKLY_HOUR_CAP
        ))
        membership_rows.append((
            f"MEM-{i:06d}", employee_id, team_id, START_DATE, None
        ))
        # Every employee has Operations; add two or three specialty skills.
        chosen = { "Operations", team_specialty[team_id] }
        available = [s for s in specialties if s not in chosen]
        chosen.update(rng.sample(available, k=min(rng.randint(1, 2), len(available))))
        for skill_index, skill_name in enumerate(sorted(chosen), 1):
            proficiency = rng.choice(["BEGINNER", "INTERMEDIATE", "ADVANCED"])
            employee_skill_rows.append((
                f"ES-{i:06d}-{skill_index:02d}", employee_id, skill_ids[skill_name], proficiency
            ))

    con.executemany("INSERT INTO employee VALUES (?,?,?,?,?,?)", employee_rows)
    con.executemany("INSERT INTO team_membership VALUES (?,?,?,?,?)", membership_rows)
    con.executemany("INSERT INTO employee_skill VALUES (?,?,?,?)", employee_skill_rows)

    holidays = [
        ("HOL-001", "2026-01-26", "Republic Day", "India"),
        ("HOL-002", "2026-08-15", "Independence Day", "India"),
        ("HOL-003", "2026-10-02", "Gandhi Jayanti", "India"),
    ]
    con.executemany("INSERT INTO holiday_calendar VALUES (?,?,?,?)", holidays)
    return skill_ids, team_specialty


def generate_leave_requests(con):
    rng = random.Random(SEED + 1)
    employees = [r["employee_id"] for r in con.execute("SELECT employee_id FROM employee")]
    start = date.fromisoformat(START_DATE)
    rows = []
    for i in range(1, LEAVE_REQUEST_COUNT):
        employee_id = rng.choice(employees)
        leave_start = start + timedelta(days=rng.randrange(DAYS))
        duration = rng.randint(1, 4)
        leave_end = min(leave_start + timedelta(days=duration - 1), start + timedelta(days=DAYS - 1))
        status = rng.choices(["APPROVED", "REJECTED", "PENDING"], weights=[60, 20, 20])[0]
        submitted = datetime.combine(leave_start - timedelta(days=rng.randint(1, 20)), time(10, 0))
        decided = submitted + timedelta(days=rng.randint(1, 4)) if status != "PENDING" else None
        rows.append((
            f"LVE-{start.year}-{i:06d}", employee_id, leave_start.isoformat(),
            leave_end.isoformat(), rng.choice(["ANNUAL", "SICK", "PERSONAL", "UNPAID"]),
            status, submitted.isoformat(sep=" "),
            decided.isoformat(sep=" ") if decided else None,
            "MGR-SYNTHETIC" if decided else None
        ))
    con.executemany(
        """INSERT INTO leave_request
        (leave_id,employee_id,start_date,end_date,leave_type,status,submitted_at,decided_at,approved_by)
        VALUES (?,?,?,?,?,?,?,?,?)""", rows
    )


def load_employee_state(con):
    team_members = defaultdict(list)
    for row in con.execute("""
        SELECT tm.team_id, e.employee_id
        FROM team_membership tm JOIN employee e USING(employee_id)
        WHERE e.employment_status='ACTIVE'
    """):
        team_members[row["team_id"]].append(row["employee_id"])

    employee_skills = defaultdict(set)
    for row in con.execute("SELECT employee_id, skill_id FROM employee_skill"):
        employee_skills[row["employee_id"]].add(row["skill_id"])

    approved_leave = defaultdict(list)
    for row in con.execute("""
        SELECT employee_id,start_date,end_date FROM leave_request WHERE status='APPROVED'
    """):
        approved_leave[row["employee_id"]].append(
            (date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"]))
        )
    return team_members, employee_skills, approved_leave


def on_approved_leave(employee_id, shift_start_day, shift_end_day, leave_map):
    # A shift conflicts with leave if any calendar day touched by the shift overlaps leave.
    return any(a <= shift_end_day and b >= shift_start_day
               for a, b in leave_map.get(employee_id, []))


def generate_schedule(con, skill_ids, team_specialty):
    rng = random.Random(SEED + 2)
    team_members, employee_skills, approved_leave = load_employee_state(con)
    templates = [
        ("TPL-M", "06:00", "14:00"),
        ("TPL-E", "14:00", "22:00"),
        ("TPL-N", "22:00", "06:00"),
    ]
    start_day = date.fromisoformat(START_DATE)

    # Per-employee state used by the deterministic allocation algorithm.
    last_end = {}
    weekly_hours = defaultdict(float)
    total_assignments = defaultdict(int)
    assignments = []
    requirements = []
    gaps = []
    assignment_counter = 0
    req_counter = 0

    for day_offset in range(DAYS):
        shift_day = start_day + timedelta(days=day_offset)
        for team_num in range(1, TEAM_COUNT + 1):
            team_id = f"TEAM-{team_num:03d}"
            specialty_id = skill_ids[team_specialty[team_id]]
            for shift_code, start_time, end_time in templates:
                shift_start, shift_end = shift_bounds(shift_day, start_time, end_time)
                shift_id = f"SHIFT-{shift_day.isoformat()}-{shift_code[-1]}"
                req_specs = [(skill_ids["Operations"], 2), (specialty_id, 1)]

                for skill_id, minimum_staff in req_specs:
                    req_counter += 1
                    requirement_id = f"REQ-{req_counter:07d}"
                    requirements.append((
                        requirement_id, team_id, shift_day.isoformat(),
                        shift_code, skill_id, minimum_staff
                    ))
                    eligible = [
                        emp for emp in team_members[team_id]
                        if skill_id in employee_skills[emp]
                        and not on_approved_leave(emp, shift_start.date(), shift_end.date(), approved_leave)
                    ]

                    # Lowest assignment count first gives a basic fairness mechanism.
                    eligible.sort(key=lambda emp: (total_assignments[emp], emp))
                    filled = 0
                    for employee_id in eligible:
                        if filled >= minimum_staff:
                            break
                        previous_end = last_end.get(employee_id)
                        if previous_end and (shift_start - previous_end).total_seconds() / 3600 < MIN_REST_HOURS:
                            continue
                        week_key = (employee_id, shift_day.isocalendar().year, shift_day.isocalendar().week)
                        if weekly_hours[week_key] + 8 > WEEKLY_HOUR_CAP:
                            continue

                        assignment_counter += 1
                        assignment_id = f"ASG-{assignment_counter:08d}"
                        assignments.append((
                            assignment_id, shift_id, employee_id, requirement_id,
                            shift_start.isoformat(sep=" "), shift_end.isoformat(sep=" "),
                            "SCHEDULED", 8.0, None, "2026-01-01 00:00:00"
                        ))
                        last_end[employee_id] = shift_end
                        weekly_hours[week_key] += 8
                        total_assignments[employee_id] += 1
                        filled += 1
                    if filled < minimum_staff:
                        gaps.append({
                            "requirement_id": requirement_id,
                            "team_id": team_id,
                            "date": shift_day.isoformat(),
                            "shift_template": shift_code,
                            "skill_id": skill_id,
                            "required": minimum_staff,
                            "filled": filled,
                            "gap": minimum_staff - filled
                        })

    con.executemany("""
        INSERT INTO coverage_requirement
        (requirement_id,team_id,shift_date,template_id,skill_id,minimum_staff)
        VALUES (?,?,?,?,?,?)
    """, requirements)
    con.executemany("""
        INSERT INTO shift_assignment
        (assignment_id,shift_id,employee_id,requirement_id,shift_start,shift_end,
         assignment_status,hours_worked,issue_type,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, assignments)

    # Attendance is derived from the scheduled assignment, not independently sampled.
    attendance_rows = []
    attendance_rng = random.Random(SEED + 3)
    for row in assignments:
        assignment_id, shift_id, employee_id, req_id, start_s, end_s, *_ = row
        start_dt = datetime.fromisoformat(start_s)
        end_dt = datetime.fromisoformat(end_s)
        status = attendance_rng.choices(["PRESENT", "LATE", "ABSENT"], [88, 8, 4])[0]
        if status == "ABSENT":
            attendance_rows.append((
                f"ATT-{employee_id}-{start_dt.strftime('%Y%m%d%H%M')}",
                employee_id, assignment_id, "ABSENT", start_dt.isoformat(sep=" "), "SYNTHETIC"
            ))
        else:
            check_in = start_dt + (timedelta(minutes=attendance_rng.randint(5, 25)) if status == "LATE" else timedelta(minutes=attendance_rng.randint(-5, 5)))
            check_out = end_dt + timedelta(minutes=attendance_rng.randint(-5, 15))
            attendance_rows.append((
                f"ATT-{employee_id}-{start_dt.strftime('%Y%m%d%H%M')}-IN",
                employee_id, assignment_id, "CHECK_IN", check_in.isoformat(sep=" "), "SYNTHETIC"
            ))
            attendance_rows.append((
                f"ATT-{employee_id}-{start_dt.strftime('%Y%m%d%H%M')}-OUT",
                employee_id, assignment_id, "CHECK_OUT", check_out.isoformat(sep=" "), "SYNTHETIC"
            ))
    con.executemany("""
        INSERT INTO attendance_event
        (attendance_id,employee_id,assignment_id,event_type,event_timestamp,source)
        VALUES (?,?,?,?,?,?)
    """, attendance_rows)

    return assignments, gaps


def inject_edge_cases(con, assignments, skill_ids):
    """Inject five independent, deliberate scheduling anomalies."""
    truth = []

    if not assignments:
        return truth

    excluded_employees = set()

    # -------------------------------------------------
    # 1. DOUBLE BOOKING
    # -------------------------------------------------
    base = con.execute("""
        SELECT a.assignment_id, a.shift_id, a.employee_id,
               a.requirement_id, a.shift_start, a.shift_end,
               r.team_id, r.shift_date, r.template_id
        FROM shift_assignment a
        JOIN coverage_requirement r
          ON a.requirement_id = r.requirement_id
        WHERE a.issue_type IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM shift_assignment b
              WHERE b.employee_id = a.employee_id
                AND b.assignment_id != a.assignment_id
                AND b.shift_start < a.shift_end
                AND b.shift_end > a.shift_start
          )
          AND NOT EXISTS (
              SELECT 1 FROM leave_request l
              WHERE l.employee_id = a.employee_id
                AND l.status = 'APPROVED'
                AND l.start_date <= date(a.shift_end)
                AND l.end_date >= date(a.shift_start)
          )
        ORDER BY a.assignment_id
        LIMIT 1
    """).fetchone()

    if base:
        other_req = con.execute("""
            SELECT cr.requirement_id
            FROM coverage_requirement cr
            WHERE cr.team_id != ?
              AND cr.shift_date = ?
              AND cr.template_id = ?
              AND EXISTS (
                  SELECT 1 FROM employee_skill es
                  WHERE es.employee_id = ?
                    AND es.skill_id = cr.skill_id
              )
            ORDER BY cr.requirement_id
            LIMIT 1
        """, (
            base["team_id"], base["shift_date"],
            base["template_id"], base["employee_id"]
        )).fetchone()

        if other_req:
            anomaly_id = "ANOM-DOUBLE-BOOK-001"

            con.execute("""
                INSERT INTO shift_assignment VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                anomaly_id, base["shift_id"], base["employee_id"],
                other_req["requirement_id"],
                base["shift_start"], base["shift_end"],
                "SCHEDULED", 8.0, "DOUBLE_BOOKING",
                "2026-01-01 00:00:00"
            ))

            excluded_employees.add(base["employee_id"])

            truth.append({
                "issue_id": "GT-001",
                "issue_type": "DOUBLE_BOOKING",
                "record_id": anomaly_id,
                "employee_id": base["employee_id"],
                "expected_result": "FLAGGED"
            })

    # -------------------------------------------------
    # 2. APPROVED LEAVE OVERLAP
    # -------------------------------------------------
    leave_base = con.execute("""
        SELECT a.assignment_id, a.employee_id,
               a.shift_start, a.shift_end
        FROM shift_assignment a
        WHERE a.issue_type IS NULL
          AND a.employee_id NOT IN (
              SELECT employee_id FROM shift_assignment
              WHERE issue_type = 'DOUBLE_BOOKING'
          )
          AND NOT EXISTS (
              SELECT 1 FROM shift_assignment b
              WHERE b.employee_id = a.employee_id
                AND b.assignment_id != a.assignment_id
                AND date(b.shift_start) <= date(a.shift_end)
                AND date(b.shift_end) >= date(a.shift_start)
          )
          AND NOT EXISTS (
              SELECT 1 FROM leave_request l
              WHERE l.employee_id = a.employee_id
                AND l.status = 'APPROVED'
                AND l.start_date <= date(a.shift_end)
                AND l.end_date >= date(a.shift_start)
          )
        ORDER BY a.assignment_id
        LIMIT 1
    """).fetchone()

    if leave_base:
        leave_id = "LVE-2026-ANOM-000001"
        shift_day = datetime.fromisoformat(
            leave_base["shift_start"]
        ).date()

        con.execute("""
            INSERT INTO leave_request
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            leave_id,
            leave_base["employee_id"],
            shift_day.isoformat(),
            shift_day.isoformat(),
            "ANNUAL",
            "APPROVED",
            "2025-12-01 09:00:00",
            "2025-12-02 09:00:00",
            "MGR-SYNTHETIC"
        ))

        excluded_employees.add(leave_base["employee_id"])

        truth.append({
            "issue_id": "GT-002",
            "issue_type": "APPROVED_LEAVE_OVERLAP",
            "record_id": leave_id,
            "employee_id": leave_base["employee_id"],
            "assignment_id": leave_base["assignment_id"],
            "expected_result": "FLAGGED"
        })

    # -------------------------------------------------
    # 3. MISSING REQUIRED SKILL
    # -------------------------------------------------
    
    skillless = con.execute("""
        SELECT e.employee_id, cr.requirement_id,
               cr.skill_id, cr.shift_date, cr.template_id
        FROM employee e
        CROSS JOIN coverage_requirement cr
        WHERE e.employment_status = 'ACTIVE'
          AND NOT EXISTS (
              SELECT 1 FROM employee_skill es
              WHERE es.employee_id = e.employee_id
                AND es.skill_id = cr.skill_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM shift_assignment a
              WHERE a.employee_id = e.employee_id
                AND a.shift_start < cr.shift_date || ' 14:00:00'
                AND a.shift_end > cr.shift_date || ' 06:00:00'
          )
          AND NOT EXISTS (
              SELECT 1 FROM leave_request l
              WHERE l.employee_id = e.employee_id
                AND l.status = 'APPROVED'
                AND l.start_date <= cr.shift_date
                AND l.end_date >= cr.shift_date
          )
        ORDER BY e.employee_id, cr.shift_date
        LIMIT 1
    """).fetchone()
   

    if skillless:
        day = date.fromisoformat(skillless["shift_date"])
        st = datetime.combine(day, time(6, 0))
        en = datetime.combine(day, time(14, 0))

        anomaly_id = "ANOM-MISSING-SKILL-001"

        con.execute("""
            INSERT INTO shift_assignment VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            anomaly_id,
            f"SHIFT-{day.isoformat()}-M",
            skillless["employee_id"],
            skillless["requirement_id"],
            st.isoformat(sep=" "),
            en.isoformat(sep=" "),
            "SCHEDULED",
            8.0,
            "MISSING_REQUIRED_SKILL",
            "2026-01-01 00:00:00"
        ))

        truth.append({
            "issue_id": "GT-003",
            "issue_type": "MISSING_REQUIRED_SKILL",
            "record_id": anomaly_id,
            "employee_id": skillless["employee_id"],
            "expected_result": "FLAGGED"
        })

    # -------------------------------------------------
    # 4. REALISTIC WEEKLY OVERTIME: 7 x 8 HOURS
    # -------------------------------------------------
    
    # -------------------------------------------------
    # 4. OVERTIME: 48 + 8 = 56 HOURS
    # -------------------------------------------------
    overtime_candidates = con.execute("""
        WITH weekly AS (
            SELECT employee_id,
                   strftime('%Y-%W', shift_start) AS work_week,
                   SUM(hours_worked) AS weekly_hours
            FROM shift_assignment
            WHERE issue_type IS NULL
            GROUP BY employee_id, work_week
            HAVING SUM(hours_worked) = ?
        )
        SELECT w.employee_id,
               cr.requirement_id,
               cr.shift_date
        FROM weekly w
        JOIN team_membership tm
          ON tm.employee_id = w.employee_id
        JOIN coverage_requirement cr
          ON cr.team_id = tm.team_id
         AND strftime('%Y-%W', cr.shift_date) = w.work_week
        JOIN employee_skill es
          ON es.employee_id = w.employee_id
         AND es.skill_id = cr.skill_id
        WHERE cr.template_id = 'TPL-M'
          AND tm.effective_from <= cr.shift_date
          AND (tm.effective_to IS NULL
               OR tm.effective_to >= cr.shift_date)
          AND NOT EXISTS (
              SELECT 1
              FROM shift_assignment a
              WHERE a.employee_id = w.employee_id
                AND a.shift_start < cr.shift_date || ' 14:00:00'
                AND a.shift_end > cr.shift_date || ' 06:00:00'
          )
          AND NOT EXISTS (
              SELECT 1
              FROM leave_request l
              WHERE l.employee_id = w.employee_id
                AND l.status = 'APPROVED'
                AND l.start_date <= cr.shift_date
                AND l.end_date >= cr.shift_date
          )
        ORDER BY w.employee_id, cr.shift_date
    """, (WEEKLY_HOUR_CAP,)).fetchall()

    overtime_candidate = next(
        (
            row for row in overtime_candidates
            if row["employee_id"] not in excluded_employees
        ),
        None
    )

    if overtime_candidate:
        emp_id = overtime_candidate["employee_id"]
        day = date.fromisoformat(overtime_candidate["shift_date"])

        st = datetime.combine(day, time(6, 0))
        en = datetime.combine(day, time(14, 0))

        anomaly_id = "ANOM-OVERTIME-001"

        con.execute("""
            INSERT INTO shift_assignment VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            anomaly_id,
            f"SHIFT-{day.isoformat()}-M",
            emp_id,
            overtime_candidate["requirement_id"],
            st.isoformat(sep=" "),
            en.isoformat(sep=" "),
            "SCHEDULED",
            8.0,
            "OVERTIME_CAP_EXCEEDED",
            "2026-01-01 00:00:00"
        ))

        truth.append({
            "issue_id": "GT-004",
            "issue_type": "OVERTIME_CAP_EXCEEDED",
            "record_id": anomaly_id,
            "employee_id": emp_id,
            "weekly_hours_recorded": 56,
            "weekly_hour_cap": WEEKLY_HOUR_CAP,
            "expected_result": "FLAGGED"
        })

    # -------------------------------------------------
    # 5. SWAP APPLIED WITHOUT MANAGER APPROVAL
    # -------------------------------------------------
    other = assignments[1] if len(assignments) > 1 else assignments[0]

    swap_id = "SWP-2026-000001"

    con.execute("""
        INSERT INTO swap_request VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        swap_id,
        assignments[0][2],
        other[2],
        assignments[0][0],
        other[0],
        "APPLIED",
        0,
        "2026-01-01 10:00:00",
        "2026-01-01 11:00:00",
        "SWAP_WITHOUT_APPROVAL"
    ))

    truth.append({
        "issue_id": "GT-005",
        "issue_type": "SWAP_WITHOUT_APPROVAL",
        "record_id": swap_id,
        "expected_result": "FLAGGED"
    })

    # -------------------------------------------------
    # AUDIT TRAIL
    # -------------------------------------------------
    audit = []

    for idx, item in enumerate(truth, 1):
        audit.append((
            f"AUD-{idx:06d}",
            item["issue_type"],
            item["record_id"],
            "ANOMALY_INJECTED",
            None,
            json.dumps(item),
            "SYSTEM",
            "2026-01-01 00:00:00"
        ))

    con.executemany("""
        INSERT INTO audit_event VALUES (?,?,?,?,?,?,?,?)
    """, audit)

    return truth


def validate_database(con):
    checks = {}
    checks["duplicate_employee_ids"] = con.execute("""
        SELECT COUNT(*) FROM (SELECT employee_id FROM employee GROUP BY employee_id HAVING COUNT(*)>1)
    """).fetchone()[0]
    checks["orphan_assignments"] = con.execute("""
        SELECT COUNT(*) FROM shift_assignment a
        LEFT JOIN employee e ON a.employee_id=e.employee_id
        LEFT JOIN coverage_requirement r ON a.requirement_id=r.requirement_id
        WHERE e.employee_id IS NULL OR r.requirement_id IS NULL
    """).fetchone()[0]
    checks["invalid_leave_dates"] = con.execute("""
        SELECT COUNT(*) FROM leave_request WHERE end_date < start_date
    """).fetchone()[0]
    checks["double_bookings"] = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT a.assignment_id
            FROM shift_assignment a JOIN shift_assignment b
              ON a.employee_id=b.employee_id
             AND a.assignment_id < b.assignment_id
             AND a.shift_start < b.shift_end
             AND b.shift_start < a.shift_end
        )
    """).fetchone()[0]
    checks["approved_leave_conflicts"] = con.execute("""
        SELECT COUNT(*) FROM shift_assignment a
        JOIN leave_request l ON a.employee_id=l.employee_id
        WHERE l.status='APPROVED'
          AND date(a.shift_start) <= l.end_date
          AND date(a.shift_end) >= l.start_date
    """).fetchone()[0]
    checks["missing_skill_assignments"] = con.execute("""
        SELECT COUNT(*) FROM shift_assignment a
        JOIN coverage_requirement r ON a.requirement_id=r.requirement_id
        WHERE NOT EXISTS (
            SELECT 1 FROM employee_skill es
            WHERE es.employee_id=a.employee_id AND es.skill_id=r.skill_id
        )
    """).fetchone()[0]
    checks["overtime_cap_violations"] = con.execute("""
    SELECT COUNT(*) FROM (
        SELECT employee_id,
               strftime('%Y-%W', shift_start) AS work_week,
               SUM(hours_worked) AS weekly_hours
        FROM shift_assignment
        WHERE assignment_status = 'SCHEDULED'
        GROUP BY employee_id, work_week
        HAVING SUM(hours_worked) > ?
    )
""", (WEEKLY_HOUR_CAP,)).fetchone()[0]
    checks["unauthorized_applied_swaps"] = con.execute("""
        SELECT COUNT(*) FROM swap_request
        WHERE status='APPLIED' AND manager_approved=0
    """).fetchone()[0]
    checks["employees"] = con.execute("SELECT COUNT(*) FROM employee").fetchone()[0]
    checks["teams"] = con.execute("SELECT COUNT(*) FROM team").fetchone()[0]
    checks["leave_requests"] = con.execute("SELECT COUNT(*) FROM leave_request").fetchone()[0]
    checks["assignments"] = con.execute("SELECT COUNT(*) FROM shift_assignment").fetchone()[0]
    checks["coverage_requirements"] = con.execute("SELECT COUNT(*) FROM coverage_requirement").fetchone()[0]
    checks["attendance_events"] = con.execute("SELECT COUNT(*) FROM attendance_event").fetchone()[0]
    return checks


def export_all(con, ground_truth, gaps, validation):
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(exist_ok=True)

    tables = [
        "team", "skill", "employee", "team_membership", "employee_skill",
        "shift_template", "holiday_calendar", "leave_request",
        "coverage_requirement", "shift_assignment", "attendance_event",
        "swap_request", "audit_event"
    ]
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table}", con)
        df.to_csv(DATA_DIR / f"{table}.csv", index=False)
        df.to_json(DATA_DIR / f"{table}.json", orient="records", indent=2)

    with open(GROUND_TRUTH_DIR / "ground_truth.json", "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
    with open(OUTPUT_DIR / "coverage_gaps.json", "w", encoding="utf-8") as f:
        json.dump(gaps, f, indent=2)

    total_required = con.execute("SELECT COALESCE(SUM(minimum_staff),0) FROM coverage_requirement").fetchone()[0]
    total_filled = con.execute("SELECT COUNT(*) FROM shift_assignment WHERE issue_type IS NULL").fetchone()[0]
    coverage_pct = round((total_filled / total_required) * 100, 2) if total_required else 100.0

    metrics = {
        "coverage_percentage": min(100.0, coverage_pct),
        "coverage_gap_records": len(gaps),
        "employees": validation["employees"],
        "teams": validation["teams"],
        "leave_requests_including_injected_case": validation["leave_requests"],
        "shift_assignments_including_anomalies": validation["assignments"],
        "attendance_events": validation["attendance_events"],
        "detected_double_bookings": validation["double_bookings"],
        "detected_approved_leave_conflicts": validation["approved_leave_conflicts"],
        "detected_missing_skills": validation["missing_skill_assignments"],
        "detected_overtime_violations": validation["overtime_cap_violations"],
        "detected_unauthorized_swaps": validation["unauthorized_applied_swaps"]
    }
    with open(OUTPUT_DIR / "evaluation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with open(OUTPUT_DIR / "validation_summary.json", "w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2)

    # Reproducible SQL seed/export file.
    with open(OUTPUT_DIR / "database_dump.sql", "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(line + "\n")

    return metrics


def run_project():
    reset_database()
    con = connect()
    try:
        skill_ids, team_specialty = generate_master_data(con)
        generate_leave_requests(con)
        assignments, gaps = generate_schedule(con, skill_ids, team_specialty)
        ground_truth = inject_edge_cases(con, assignments, skill_ids)
        con.commit()
        validation = validate_database(con)
        metrics = export_all(con, ground_truth, gaps, validation)
        print("\nPROJECT GENERATION COMPLETED")
        print(json.dumps(metrics, indent=2))
        print("\nValidation summary:")
        print(json.dumps(validation, indent=2))
    finally:
        con.close()
