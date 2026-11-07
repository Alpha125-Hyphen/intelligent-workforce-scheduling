# Data Dictionary – Intelligent Workforce Management & Shift Scheduling System

## 1. Overview

This document describes the database schema used by the Intelligent Workforce Management & Shift Scheduling System.

The database uses SQLite and contains 13 tables covering employees, teams, skills, shift templates, scheduling, leave management, attendance, shift swaps, and audit history.

## 2. Database Tables

### 2.1 team

Stores organizational team information.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| team_id | TEXT | Primary Key | Unique team identifier |
| team_name | TEXT | NOT NULL, UNIQUE | Name of the team |
| department | TEXT | NOT NULL | Department associated with the team |

### 2.2 skill

Stores the skills required for workforce scheduling.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| skill_id | TEXT | Primary Key | Unique skill identifier |
| skill_name | TEXT | NOT NULL, UNIQUE | Name of the skill |
| description | TEXT | Optional | Description of the skill |

### 2.3 employee

Stores employee master information.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| employee_id | TEXT | Primary Key | Unique employee identifier |
| full_name | TEXT | NOT NULL | Employee's full name |
| email | TEXT | NOT NULL, UNIQUE | Employee email address |
| hire_date | TEXT | NOT NULL | Employee joining date |
| employment_status | TEXT | NOT NULL, CHECK | ACTIVE or INACTIVE |
| weekly_hour_limit | INTEGER | NOT NULL, CHECK > 0 | Maximum weekly working hours |

### 2.4 team_membership

Tracks employee membership in teams, including effective dates.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| membership_id | TEXT | Primary Key | Unique membership identifier |
| employee_id | TEXT | Foreign Key, NOT NULL | References employee.employee_id |
| team_id | TEXT | Foreign Key, NOT NULL | References team.team_id |
| effective_from | TEXT | NOT NULL | Membership start date |
| effective_to | TEXT | Optional | Membership end date |

**Business rule:** The end date must be greater than or equal to the start date.

### 2.5 employee_skill

Connects employees with their skills. This is a many-to-many relationship between employees and skills.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| employee_skill_id | TEXT | Primary Key | Unique employee-skill identifier |
| employee_id | TEXT | Foreign Key, NOT NULL | References employee.employee_id |
| skill_id | TEXT | Foreign Key, NOT NULL | References skill.skill_id |
| proficiency | TEXT | NOT NULL, CHECK | BEGINNER, INTERMEDIATE, or ADVANCED |

**Business rule:** An employee cannot have duplicate entries for the same skill.

### 2.6 shift_template

Stores reusable shift definitions.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| template_id | TEXT | Primary Key | Unique shift template identifier |
| shift_name | TEXT | NOT NULL, UNIQUE | Shift name |
| start_time | TEXT | NOT NULL | Shift start time |
| end_time | TEXT | NOT NULL | Shift end time |
| duration_hours | REAL | NOT NULL, CHECK > 0 | Shift duration in hours |

### 2.7 holiday_calendar

Stores holidays applicable to different regions.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| holiday_id | TEXT | Primary Key | Unique holiday identifier |
| holiday_date | TEXT | NOT NULL | Holiday date |
| holiday_name | TEXT | NOT NULL | Holiday name |
| region | TEXT | NOT NULL | Applicable region |

### 2.8 leave_request

Stores employee leave requests and approval information.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| leave_id | TEXT | Primary Key | Unique leave identifier |
| employee_id | TEXT | Foreign Key, NOT NULL | References employee.employee_id |
| start_date | TEXT | NOT NULL | Leave start date |
| end_date | TEXT | NOT NULL | Leave end date |
| leave_type | TEXT | NOT NULL, CHECK | ANNUAL, SICK, PERSONAL, or UNPAID |
| status | TEXT | NOT NULL, CHECK | PENDING, APPROVED, or REJECTED |
| submitted_at | TEXT | NOT NULL | Submission timestamp |
| decided_at | TEXT | Optional | Decision timestamp |
| approved_by | TEXT | Optional | Approver identifier |

**Business rule:** The leave end date cannot be earlier than the start date.

### 2.9 coverage_requirement

Defines the minimum staffing required for a team, shift, date, and skill.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| requirement_id | TEXT | Primary Key | Unique requirement identifier |
| team_id | TEXT | Foreign Key, NOT NULL | References team.team_id |
| shift_date | TEXT | NOT NULL | Required shift date |
| template_id | TEXT | Foreign Key, NOT NULL | References shift_template.template_id |
| skill_id | TEXT | Foreign Key, NOT NULL | References skill.skill_id |
| minimum_staff | INTEGER | NOT NULL, CHECK >= 0 | Minimum required employees |

**Business rule:** A team cannot have duplicate coverage requirements for the same date, shift template, and skill.

### 2.10 shift_assignment

Stores employee shift assignments.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| assignment_id | TEXT | Primary Key | Unique assignment identifier |
| shift_id | TEXT | NOT NULL | Shift identifier |
| employee_id | TEXT | Foreign Key, NOT NULL | References employee.employee_id |
| requirement_id | TEXT | Foreign Key, NOT NULL | References coverage_requirement.requirement_id |
| shift_start | TEXT | NOT NULL | Shift start timestamp |
| shift_end | TEXT | NOT NULL | Shift end timestamp |
| assignment_status | TEXT | NOT NULL, CHECK | SCHEDULED, CANCELLED, or COMPLETED |
| hours_worked | REAL | NOT NULL | Recorded working hours |
| issue_type | TEXT | Optional | Associated anomaly or issue type |
| created_at | TEXT | NOT NULL | Assignment creation timestamp |

**Business rule:** The shift end timestamp must be later than the shift start timestamp.

### 2.11 attendance_event

Records employee attendance events for shift assignments.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| attendance_id | TEXT | Primary Key | Unique attendance event identifier |
| employee_id | TEXT | Foreign Key, NOT NULL | References employee.employee_id |
| assignment_id | TEXT | Foreign Key, NOT NULL | References shift_assignment.assignment_id |
| event_type | TEXT | NOT NULL, CHECK | CHECK_IN, CHECK_OUT, or ABSENT |
| event_timestamp | TEXT | NOT NULL | Attendance event timestamp |
| source | TEXT | NOT NULL | Source of attendance information |

### 2.12 swap_request

Stores employee shift swap requests and approval status.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| swap_id | TEXT | Primary Key | Unique swap identifier |
| requester_employee_id | TEXT | Foreign Key, NOT NULL | Employee requesting the swap |
| target_employee_id | TEXT | Foreign Key, NOT NULL | Employee receiving the swap |
| requester_assignment_id | TEXT | Foreign Key, NOT NULL | Requester's shift assignment |
| target_assignment_id | TEXT | Foreign Key, NOT NULL | Target employee's shift assignment |
| status | TEXT | NOT NULL, CHECK | PENDING, APPROVED, REJECTED, or APPLIED |
| manager_approved | INTEGER | NOT NULL, CHECK | 0 = No, 1 = Yes |
| requested_at | TEXT | NOT NULL | Request timestamp |
| decided_at | TEXT | Optional | Decision timestamp |
| issue_type | TEXT | Optional | Associated swap issue |

### 2.13 audit_event

Maintains a record of changes and actions performed on system entities.

| Column | Data type | Constraints | Description |
|---|---|---|---|
| event_id | TEXT | Primary Key | Unique audit event identifier |
| entity_type | TEXT | NOT NULL | Type of entity affected |
| entity_id | TEXT | NOT NULL | Identifier of the affected entity |
| action | TEXT | NOT NULL | Action performed |
| old_value | TEXT | Optional | Previous value |
| new_value | TEXT | Optional | Updated value |
| actor | TEXT | NOT NULL | Person or process performing the action |
| event_timestamp | TEXT | NOT NULL | Time of the action |

## 3. Relationships

| Parent table | Child table | Relationship |
|---|---|---|
| employee | team_membership | One-to-many |
| team | team_membership | One-to-many |
| employee | employee_skill | One-to-many |
| skill | employee_skill | One-to-many |
| employee | leave_request | One-to-many |
| team | coverage_requirement | One-to-many |
| shift_template | coverage_requirement | One-to-many |
| skill | coverage_requirement | One-to-many |
| employee | shift_assignment | One-to-many |
| coverage_requirement | shift_assignment | One-to-many |
| shift_assignment | attendance_event | One-to-many |
| employee | swap_request | One-to-many |
| shift_assignment | swap_request | One-to-many |

**Many-to-many relationships:**
- Employees and teams are connected through `team_membership`.
- Employees and skills are connected through `employee_skill`.

## 4. Database Indexes

The schema defines the following indexes to improve query performance:

| Index | Table | Indexed columns | Purpose |
|---|---|---|---|
| idx_assignment_employee_start | shift_assignment | employee_id, shift_start | Find employee assignments by start time |
| idx_leave_employee_dates | leave_request | employee_id, start_date, end_date | Find employee leave records by date |
| idx_requirement_date | coverage_requirement | shift_date, team_id, template_id | Retrieve coverage requirements by date and team |

## 5. Integrity Constraints

The database enforces:
- Primary key uniqueness.
- Foreign key references between related tables.
- NOT NULL constraints for mandatory fields.
- UNIQUE constraints for selected business identifiers and relationships.
- CHECK constraints for status values, proficiency levels, positive hour limits, and valid date/time ranges.
- Foreign key enforcement through `PRAGMA foreign_keys = ON`.

## 6. Notes

- Dates and timestamps are stored as TEXT values.
- Employee and other business identifiers use TEXT primary keys.
- Optional fields are nullable unless otherwise specified.
- Some scheduling rules, such as double-booking detection, approved-leave conflicts, missing skills, overtime, and swap approval validation, are handled by application-level validation rather than database CHECK constraints.
