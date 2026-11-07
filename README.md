# Intelligent Workforce Management & Shift Scheduling System

A reproducible synthetic workforce scheduling project that combines employee availability, leave requests, skills, shift coverage and working-hour constraints to generate workforce schedules.

The system generates master data, dependent transaction records, shift assignments, attendance events, swap requests, deliberate anomaly scenarios, ground-truth labels, validation reports and CSV/JSON/SQL exports.

## 1. Technology Stack

- Python 3.10+
- SQLite – local database
- Faker – synthetic employee data
- Pandas – data processing and exports
- pytest – automated testing

**Database choice:** The assignment does not mandate a particular database or framework. SQLite is used to make the project easy to set up and run locally. The generated SQL dump can serve as a starting point for migration to MySQL.

The current implementation focuses on the data generation and scheduling engine. A Django API and manager dashboard are not included in this version.

## 2. Project Setup

### Prerequisites

- Python 3.10 or later
- pip

### Step 1: Clone the repository

```bash
git clone <YOUR_PUBLIC_GITHUB_REPOSITORY_URL>
cd workforce_scheduling_project
```

### Step 2: Create a virtual environment

**Windows CMD:**

```cmd
python -m venv venv
venv\Scripts\activate
```

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Generate the complete dataset

```bash
python main.py
```

The generator creates the SQLite database, synthetic records, scheduling outputs, validation results and ground-truth labels.

### Step 5: Run automated tests

```bash
pytest -q
```

## 3. Dataset Configuration

The default configuration is maintained in `src/config.py`.

| Parameter | Value |
|---|---:|
| Random seed | 20261022 |
| Employees | 2,000 |
| Teams | 100 |
| Scheduling horizon | 90 days |
| Leave requests | 5,000 |
| Weekly working-hour cap | 48 hours |
| Overtime cap | 8 hours |
| Minimum rest period | 11 hours |

The generator is parameterized so smaller datasets can be generated for development and testing using the same generation logic.

For example, the employee count, team count, scheduling period and leave request count can be adjusted in `src/config.py`.

## 4. Project Output Structure

The project generates the following files and directories:

```text
workforce_scheduling_project/
│
├── main.py
├── reproducibility_check.py
├── requirements.txt
├── README.md
├── workforce.db
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── schema.py
│   └── engine.py
│
├── sql/
│   └── schema.sql
│
├── data/
│   ├── employee.csv
│   ├── team.csv
│   ├── skill.csv
│   ├── shift_template.csv
│   ├── shift_assignment.csv
│   ├── leave_request.csv
│   ├── holiday_calendar.csv
│   ├── attendance_event.csv
│   ├── coverage_requirement.csv
│   ├── swap_request.csv
│   ├── employee_skill.csv
│   ├── team_membership.csv
│   ├── audit_event.csv
│   └── corresponding JSON exports
│
├── ground_truth/
│   └── ground_truth.json
│
├── outputs/
│   ├── coverage_gaps.json
│   ├── evaluation_metrics.json
│   ├── validation_summary.json
│   ├── database_dump.sql
│   └── checksum_manifest.json
│
└── tests/
    └── test_schema.py
```

The exact generated filenames should be checked against the files produced by the generator.

### Output descriptions

- `workforce.db`: SQLite database containing generated records.
- `data/`: CSV and JSON exports of generated tables.
- `ground_truth/ground_truth.json`: Labels for deliberately injected anomaly scenarios. This file must not be used as an input feature when evaluating a model.
- `outputs/coverage_gaps.json`: Reports unmet staffing requirements.
- `outputs/evaluation_metrics.json`: Contains scheduling and evaluation metrics.
- `outputs/validation_summary.json`: Contains data-integrity and anomaly validation results.
- `outputs/database_dump.sql`: SQL data export.
- `outputs/checksum_manifest.json`: SHA256 checksums for reproducibility verification.

## 5. Core Entities and Relationships

The project contains the following ten core entities:

1. Employee
2. Team
3. Skill
4. ShiftTemplate
5. ShiftAssignment
6. LeaveRequest
7. HolidayCalendar
8. AttendanceEvent
9. CoverageRequirement
10. SwapRequest

Supporting tables include:

- `employee_skill`
- `team_membership`
- `audit_event`

### Entity relationships

| Relationship | Cardinality |
|---|---|
| Team to TeamMembership | 1:N |
| Employee to TeamMembership | 1:N |
| Employee to Skill through EmployeeSkill | M:N |
| Team to CoverageRequirement | 1:N |
| ShiftTemplate to CoverageRequirement | 1:N |
| Skill to CoverageRequirement | 1:N |
| Employee to LeaveRequest | 1:N |
| Employee to ShiftAssignment | 1:N |
| CoverageRequirement to ShiftAssignment | 1:N |
| ShiftAssignment to AttendanceEvent | 1:N |
| Employee to SwapRequest | 1:N as requester or target |

Primary keys identify records, and foreign keys maintain relationships between related records.

The `team_membership` table uses effective dates to represent employee-team membership periods.

The `audit_event` table supports recording historical system events rather than silently overwriting important changes.

## 6. Business Rules and Scheduling Logic

The scheduling engine implements the following rules:

- Employees are associated with teams through a membership bridge table.
- Employee skills are represented using a many-to-many relationship.
- Approved leave prevents normal shift allocation during the leave period.
- Each team has morning, evening and night shift templates.
- Staffing requirements are defined for each shift and required skill.
- Each shift requires two Operations-skilled employees and one employee with the team's specialty skill.
- Employee eligibility is checked against required skills and approved leave.
- The scheduler considers minimum rest periods and weekly working-hour limits.
- Assignment counts are used as a basic fairness tie-breaker.
- Attendance events are generated from shift assignments.
- Unmet staffing requirements are reported as coverage gaps.
- Swap requests and their approval status are represented in the generated data.
- Unauthorized applied swaps are detected during validation.

### Scheduling approach

The current scheduler uses a deterministic greedy allocation approach.

It prioritizes employee eligibility, skills, approved leave, rest periods and weekly working-hour limits. Assignment counts provide a basic fairness mechanism.

It is a scheduling demonstration and does not claim to find a globally optimal schedule.

## 7. Required Anomaly Scenarios

The project generates valid baseline records first and then injects five labelled exception scenarios.

| Anomaly | Description |
|---|---|
| Double booking | An employee is assigned overlapping shifts. |
| Approved leave conflict | An employee is assigned a shift during approved leave. |
| Missing required skill | An employee without the required skill is assigned to a requirement. |
| Overtime violation | An employee exceeds the configured working-hour limit. |
| Unauthorized swap | A swap is applied without the required manager approval. |

Each deliberate anomaly is labelled using `issue_type` and recorded in `ground_truth/ground_truth.json`.

These scenarios are intentional test cases used to verify the validation logic. They are not valid operational assignments.

Ground-truth labels are maintained separately from the ordinary generated input records.

## 8. Validation Results

The full dataset was generated successfully using the fixed seed `20261022`.

### Dataset summary

| Metric | Generated result |
|---|---:|
| Employees | 2,000 |
| Teams | 100 |
| Leave requests | 5,000 |
| Shift assignments | 81,003 |
| Attendance events | 158,710 |
| Coverage requirements | 54,000 |
| Coverage percentage | 100% |
| Coverage gap records | 0 |

### Data integrity checks

| Validation | Result |
|---|---:|
| Duplicate employee IDs | 0 |
| Orphan assignments | 0 |
| Invalid leave dates | 0 |

### Anomaly detection results

| Validation | Detected anomalies |
|---|---:|
| Double bookings | 1 |
| Approved leave conflicts | 1 |
| Missing required skills | 1 |
| Overtime violations | 1 |
| Unauthorized applied swaps | 1 |

The five detected anomalies are deliberately injected scenarios. The validation process identifies and reports them rather than treating them as normal scheduling records.

## 9. Reproducibility Verification

The project uses a fixed random seed of `20261022` for deterministic synthetic data generation.

The reproducibility checker calculates SHA256 checksums for generated files in the `data/`, `ground_truth/` and `outputs/` directories. It excludes its own checksum manifest from the calculation.

### Reproducibility test results

The project was generated twice using the same seed.

| Check | Result |
|---|---:|
| First generation files checked | 31 |
| Second generation files checked | 31 |
| Checksums identical | True |
| Changed files | 0 |

To generate a checksum manifest:

```bash
python reproducibility_check.py
```

For an independent comparison, preserve the first manifest before regenerating the project:

```cmd
copy outputs\checksum_manifest.json checksum_manifest_run1.json
```

After regenerating the dataset and creating the second manifest, compare them:

```bash
python -c "import json; a=json.load(open('checksum_manifest_run1.json')); b=json.load(open('outputs/checksum_manifest.json')); print('Identical:',a==b)"
```

The comparison verifies the generated files covered by the manifest. It does not establish byte-for-byte reproducibility of the SQLite database file itself.

For reproducibility, retain the same Python and dependency versions as well as the same configuration and seed.

## 10. Data Provenance

This project uses synthetically generated workforce data.

Faker and the project's deterministic generation logic are used to create synthetic records. No confidential employee records or private workforce datasets are required.

The generated dataset is intended for development, testing and demonstration purposes.

## 11. Limitations and Future Scope

This project is a synthetic workforce scheduling demonstration, not a production HR or payroll system.

Current limitations:

- The scheduling engine uses a greedy allocation strategy rather than a formal optimization solver.
- Fairness is represented by a basic assignment-count tie-breaker.
- The project does not include an interactive employee or manager dashboard.
- A complete Django REST API and role-based access system are not included.
- The current implementation uses SQLite rather than a production database.
- The generated anomaly scenarios are intended for validation and testing.

Possible future improvements:

1. Build a manager interface for leave and swap approvals.
2. Add employee-facing leave and shift swap request screens.
3. Introduce role-based access for employees, managers, HR and administrators.
4. Add REST API endpoints.
5. Improve fairness using measurable workload-balancing metrics.
6. Introduce an optimization solver for larger and more complex scheduling scenarios.

## 12. Run Tests

Execute the automated tests with:

```bash
python -m pytest -q
```

The tests validate the implemented schema and related checks.

## 13. Project Objective

The objective is to demonstrate a reproducible workforce scheduling workflow that combines employee skills, leave requests, shift coverage and working-hour constraints.

The project provides:

- Synthetic master and transaction data.
- A deterministic scheduling engine.
- Skill-specific staffing requirements.
- Leave and attendance records.
- Swap request data.
- Coverage and overtime evaluation.
- Deliberate anomaly scenarios.
- Separate ground-truth labels.
- Data validation and integrity checks.
- Reproducibility verification.
- CSV, JSON and SQL exports.

The result is a reproducible foundation for further development of an intelligent workforce management solution.
## Documentation

- [Data Dictionary](docs/data_dictionary.md)
- [Business Rules and Anomaly Definitions](docs/business_rules.md)