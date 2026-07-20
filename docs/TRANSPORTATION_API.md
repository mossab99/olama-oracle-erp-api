# Olama Transportation read-only Oracle API

All endpoints require `X-API-Key`. They expose normalized master/reference data
only and never write to Oracle.

## Endpoints

- `GET /api/transportation/students?study_year=2026/2027&limit=500&offset=0`
- `GET /api/transportation/buses?include_inactive=1`
- `GET /api/transportation/regions?study_year=2026/2027`
- `GET /api/transportation/employees`
- `GET /api/transportation/summary?study_year=2026/2027`
- `GET /api/families/{family_id}/transportation?study_year=2026/2027`

Student bus IDs and sequence values are prefixed with `legacy_`. They are
reference values only. Olama Transportation owns new enrollment, allocation,
route, version, and approval records.

## Confirmed Oracle sources

- `SCH_STUDENT_TOT_TRANS`: Forms-backed transportation student projection.
- `SCH_BUS_IDS`: fleet master table.

The API uses bound parameters, Oracle 11g-compatible pagination, a maximum page
size of 1,000, and generic server errors so database details are not disclosed.

The confirmed Forms schema provides `EMP_ID` and `COMPANION_EMP_ID`, so the
employees endpoint returns those IDs and their fleet roles. It intentionally
does not guess an employee-name table. Add the authoritative employee name join
after the Forms block query or employee table is confirmed.
