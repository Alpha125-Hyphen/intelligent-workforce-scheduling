SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS team (
    team_id TEXT PRIMARY KEY,
    team_name TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill (
    skill_id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS employee (
    employee_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    hire_date TEXT NOT NULL,
    employment_status TEXT NOT NULL CHECK (employment_status IN ('ACTIVE','INACTIVE')),
    weekly_hour_limit INTEGER NOT NULL CHECK (weekly_hour_limit > 0)
);

CREATE TABLE IF NOT EXISTS team_membership (
    membership_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employee(employee_id),
    team_id TEXT NOT NULL REFERENCES team(team_id),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE IF NOT EXISTS employee_skill (
    employee_skill_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employee(employee_id),
    skill_id TEXT NOT NULL REFERENCES skill(skill_id),
    proficiency TEXT NOT NULL CHECK (proficiency IN ('BEGINNER','INTERMEDIATE','ADVANCED')),
    UNIQUE(employee_id, skill_id)
);

CREATE TABLE IF NOT EXISTS shift_template (
    template_id TEXT PRIMARY KEY,
    shift_name TEXT NOT NULL UNIQUE,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_hours REAL NOT NULL CHECK (duration_hours > 0)
);

CREATE TABLE IF NOT EXISTS holiday_calendar (
    holiday_id TEXT PRIMARY KEY,
    holiday_date TEXT NOT NULL,
    holiday_name TEXT NOT NULL,
    region TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leave_request (
    leave_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employee(employee_id),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    leave_type TEXT NOT NULL CHECK (leave_type IN ('ANNUAL','SICK','PERSONAL','UNPAID')),
    status TEXT NOT NULL CHECK (status IN ('PENDING','APPROVED','REJECTED')),
    submitted_at TEXT NOT NULL,
    decided_at TEXT,
    approved_by TEXT,
    CHECK (end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS coverage_requirement (
    requirement_id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES team(team_id),
    shift_date TEXT NOT NULL,
    template_id TEXT NOT NULL REFERENCES shift_template(template_id),
    skill_id TEXT NOT NULL REFERENCES skill(skill_id),
    minimum_staff INTEGER NOT NULL CHECK (minimum_staff >= 0),
    UNIQUE(team_id, shift_date, template_id, skill_id)
);

CREATE TABLE IF NOT EXISTS shift_assignment (
    assignment_id TEXT PRIMARY KEY,
    shift_id TEXT NOT NULL,
    employee_id TEXT NOT NULL REFERENCES employee(employee_id),
    requirement_id TEXT NOT NULL REFERENCES coverage_requirement(requirement_id),
    shift_start TEXT NOT NULL,
    shift_end TEXT NOT NULL,
    assignment_status TEXT NOT NULL CHECK (assignment_status IN ('SCHEDULED','CANCELLED','COMPLETED')),
    hours_worked REAL NOT NULL,
    issue_type TEXT,
    created_at TEXT NOT NULL,
    CHECK (shift_end > shift_start)
);

CREATE TABLE IF NOT EXISTS attendance_event (
    attendance_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employee(employee_id),
    assignment_id TEXT NOT NULL REFERENCES shift_assignment(assignment_id),
    event_type TEXT NOT NULL CHECK (event_type IN ('CHECK_IN','CHECK_OUT','ABSENT')),
    event_timestamp TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS swap_request (
    swap_id TEXT PRIMARY KEY,
    requester_employee_id TEXT NOT NULL REFERENCES employee(employee_id),
    target_employee_id TEXT NOT NULL REFERENCES employee(employee_id),
    requester_assignment_id TEXT NOT NULL REFERENCES shift_assignment(assignment_id),
    target_assignment_id TEXT NOT NULL REFERENCES shift_assignment(assignment_id),
    status TEXT NOT NULL CHECK (status IN ('PENDING','APPROVED','REJECTED','APPLIED')),
    manager_approved INTEGER NOT NULL CHECK (manager_approved IN (0,1)),
    requested_at TEXT NOT NULL,
    decided_at TEXT,
    issue_type TEXT
);

CREATE TABLE IF NOT EXISTS audit_event (
    event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    actor TEXT NOT NULL,
    event_timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assignment_employee_start
ON shift_assignment(employee_id, shift_start);

CREATE INDEX IF NOT EXISTS idx_leave_employee_dates
ON leave_request(employee_id, start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_requirement_date
ON coverage_requirement(shift_date, team_id, template_id);
"""
