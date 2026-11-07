# Business Rules and Anomaly Definitions

## 1. Overview

The Intelligent Workforce Management & Shift Scheduling System generates employee shift schedules by considering employee availability, skills, leave requests, working-hour limits, rest periods, and staffing requirements.

## 2. Scheduling Business Rules

### Rule 1: Employee Eligibility
- Only active employees should be considered for scheduling.
- Employees must have the required skill for the shift.
- Employees must have an applicable team membership.

### Rule 2: Leave Management
- Employees with approved leave must not be assigned shifts during their leave period.
- Pending and rejected leave requests are not treated as approved leave.

### Rule 3: Shift Conflict Prevention
- An employee should not be assigned overlapping shifts.
- Shift start and end timestamps must be valid.

### Rule 4: Rest Period
- Employees should have at least 11 hours of rest between consecutive shifts.

### Rule 5: Weekly Working Hours
- Employee weekly working hours must respect the configured limit.
- The configured weekly hour cap is 48 hours.
- Overtime violations are identified when the applicable limit is exceeded.

### Rule 6: Coverage Requirements
- Each team, date, shift template, and skill combination has a minimum staffing requirement.
- The scheduler attempts to satisfy all coverage requirements.

### Rule 7: Fairness
- The scheduling engine uses assignment counts as a basic fairness consideration when selecting employees.

### Rule 8: Shift Swap Approval
- A shift swap must have manager approval before it can be applied.
- Applied swaps without approval are considered invalid.

## 3. Anomaly Definitions

The dataset contains five deliberately injected anomaly types.

| Anomaly | Description | Expected validation |
|---|---|---|
| Double booking | An employee is assigned overlapping shifts | Detect overlapping assignments |
| Approved leave conflict | An employee is assigned a shift during approved leave | Detect leave and assignment overlap |
| Missing skill | An employee is assigned to a requirement without the required skill | Detect missing employee skill |
| Overtime violation | An employee exceeds the configured weekly working-hour limit | Detect weekly hours above the limit |
| Unauthorized swap | A shift swap is applied without manager approval | Detect applied swap without approval |

## 4. Dataset Validation

The generated dataset is validated using application-level checks.

The validation process checks:
- Duplicate employee identifiers.
- Orphan shift assignments.
- Invalid leave date ranges.
- Double-booked employees.
- Approved leave conflicts.
- Missing required skills.
- Weekly overtime violations.
- Unauthorized applied shift swaps.

## 5. Expected Validation Results

The generated dataset should contain the following results:

| Validation | Expected count |
|---|---:|
| Duplicate employee IDs | 0 |
| Orphan assignments | 0 |
| Invalid leave dates | 0 |
| Double bookings | 1 |
| Approved leave conflicts | 1 |
| Missing skill assignments | 1 |
| Overtime violations | 1 |
| Unauthorized applied swaps | 1 |

## 6. Scheduling Engine

The current scheduling engine uses a deterministic greedy assignment approach.

It considers employee eligibility and scheduling constraints when selecting employees for coverage requirements.

It is a baseline scheduling implementation, not a global optimization algorithm.

## 7. Reproducibility

The synthetic dataset uses the fixed random seed:

`20261022`

Using the same configuration and seed should produce identical generated outputs.

The reproducibility checker compares file checksums between consecutive runs.