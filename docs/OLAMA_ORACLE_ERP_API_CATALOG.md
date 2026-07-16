# Olama Oracle ERP Bridge — API Catalog

**Reviewed:** 2026-07-15  
**Source reviewed:** `D:\api`  
**Purpose:** A simple inventory of the Oracle bridge APIs available to the Olama ecosystem.

## 1. Bridge overview

The bridge is a read-only Flask service that connects to Oracle ERP and returns JSON to Olama plugins. All business endpoints use HTTP `GET`.

- **Authentication:** Send `X-API-Key: <key>` on every `/api/...` request except `/api/health`.
- **Public routes:** `/` and `/api/health`.
- **Successful responses:** JSON, normally with `status: "success"` plus data or counts.
- **Errors:** JSON with `status: "error"`; missing key returns HTTP 401, invalid key returns 403, missing records usually return 404, and server/Oracle errors return 500.
- **Study year:** Several endpoints accept `study_year`. When optional, it normally defaults to the server's configured current year.
- **Route inventory:** 27 distinct operations exposed through 31 URL patterns; four extra patterns are aliases for the same finance operations.

## 2. Connection and health

| Method | Endpoint | Parameters | Purpose | Authentication | Confirmed Olama consumer |
|---|---|---|---|---|---|
| GET | `/` | None | Service identity and a partial endpoint index | Public | None |
| GET | `/api/health` | None | Tests whether the bridge can connect to Oracle | Public | Olama Oracle Sync |

## 3. Families and students

| Method | Endpoint | Parameters | Main response content | Main Oracle sources | Confirmed Olama consumer |
|---|---|---|---|---|---|
| GET | `/api/families` | None | Active families and count | `SCH_FAMILY_CARD`, `SCH_FAMILY_CLASS`, `SCH_STUDENT_CARD_YEAR` | Olama Oracle Sync |
| GET | `/api/families/{family_id}` | Path: `family_id` | One family plus its students | `SCH_FAMILY_CARD`, `SCH_FAMILY_CLASS`, student tables | Olama Oracle Sync |
| GET | `/api/families/{family_id}/students` | Path: `family_id` | Active students for the configured current year | `SCH_STUDENT_CARD`, `SCH_STUDENT_CARD_YEAR`, school/class/branch/section tables | Olama Oracle Sync |
| GET | `/api/students` | None | All active students for the configured current year | Student, family, school, class, branch and section tables | Olama Oracle Sync |
| GET | `/api/students/{family_id}/{student_id}` | Path: family and student IDs | One current-year student | Student, family and academic tables | Not found in current plugin calls |
| GET | `/api/students/search` | Required query: `q` | Students matching the search text | Student, family, class and section tables | Olama Oracle Sync client |

### Detailed cards

| Method | Endpoint | Parameters | Main response content | Main Oracle sources | Confirmed Olama consumer |
|---|---|---|---|---|---|
| GET | `/api/families/{family_id}/card` | Optional: `study_year` | Detailed family profile and children | Family, student, academic, school, class, section and transportation-region tables | Olama Oracle Sync; Olama Core |
| GET | `/api/families/{family_id}/students/{student_id}/card` | Optional: `study_year` | Student profile, family summary, current academics, academic history and current transportation | Student, family, academic and transportation tables | Olama Core |

## 4. Transportation

| Method | Endpoint | Parameters | Main response content | Main Oracle sources | Confirmed Olama consumer |
|---|---|---|---|---|---|
| GET | `/api/families/{family_id}/transportation` | Optional: `study_year` | Transportation records for a family's students | `SCH_STUDENT_TRANS`, student/year, school/class/section, transport groups and buses | Olama Core; Olama Messages |
| GET | `/api/messaging/transportation/recipients` | Required: `study_year`; optional: `route_mode`, `class_id`, `section_id`, `departure_bus`, `arrival_bus`, `trans_route`, `family_id`, `active_only`, `limit`, `offset` | Filtered message recipients with bus and route data | Transportation, family, student, academic, class and section tables | Olama Messages |
| GET | `/api/messaging/transportation/options` | Required: `study_year`; optional: `active_only` | Available buses, routes, classes and sections for filters | Transportation, family, academic, class and section tables | Olama Messages |

`route_mode` accepts `either`, `both`, `departure`, or `arrival`. Recipient pagination is capped at 200 records per call.

## 5. Financial data

| Method | Endpoint | Parameters | Main response content | Main Oracle sources | Confirmed Olama consumer |
|---|---|---|---|---|---|
| GET | `/api/families/{family_id}/financial-card` | Optional: `study_year` | Family financial summary, students, due allocations and student transactions | `SCH_FIN_FAMILY_CARD`, `SCH_FIN_STUDENT_CARD`, `SCH_FAMILY_DUE_ALLOC`, student/year and fee-title tables | Olama Core |
| GET | `/api/families/{family_id}/financial-summary` | Optional: `study_year` | Compact family balance/payment summary for messaging | Financial family/student and due-allocation tables | Olama Messages |
| GET | `/api/families/{family_id}/payment-report` | Optional: `study_year` | Message-ready family payment report | Financial family/student and due-allocation tables | Olama Messages |
| GET | `/api/messaging/recipients` | Optional: `study_year`, `min_balance`, family/class/section IDs or names, `limit`, `offset` | Families and students filtered for financial messaging | Family, student/year, class, section, financial family and due-allocation tables | Olama Messages |

### Normalized financial contract

The following newer endpoints expose stable, integration-oriented financial response contracts.

| Method | Endpoint(s) | Parameters | Purpose | Current use |
|---|---|---|---|---|
| GET | `/api/families/{family_id}/financial`  · `/api/families/{family_id}/balance`  · `/api/financial/families/{family_id}` | Optional: `study_year` | Same family financial summary through three aliases | No current plugin call found |
| GET | `/api/families/{family_id}/financial-transactions`  · `/api/families/{family_id}/transactions` | Optional: `study_year`, `limit`, `offset` | Normalized family transactions | No current plugin call found |
| GET | `/api/families/{family_id}/dues` | Optional: `study_year`, `limit`, `offset` | Due allocations | No current plugin call found |
| GET | `/api/families/{family_id}/receipts` | Optional: `study_year`, `limit`, `offset` | Receipt-like credit records | No current plugin call found |
| GET | `/api/families/{family_id}/payments` | Optional: `study_year`, `limit`, `offset` | Reserved payment collection | No current plugin call found; currently returns an unavailable/empty result |
| GET | `/api/students/{family_id}:{student_id}/financial-summary`  · `/api/students/{family_id}:{student_id}/financial` | Optional: `study_year` | Same per-student financial summary through two aliases | No current plugin call found |
| GET | `/api/financial/diagnostics` | Optional: `study_year` | Finance source/readiness diagnostics | No current plugin call found |

Financial list pagination defaults to 500 records and is capped at 2,000 records per request.

## 6. Student identity crosswalk

| Method | Endpoint | Parameters | Purpose | Main Oracle sources | Current use |
|---|---|---|---|---|---|
| GET | `/api/students/crosswalk` | Optional: `study_year`, `include_inactive`, `family_id`, `student_id`, `limit`, `offset` | Canonical mapping of Oracle family/student identity to academic context | Student/year, class, section, school and branch tables | No current plugin call found |
| GET | `/api/students/crosswalk/diagnostics` | Optional: `study_year` | Crosswalk completeness and duplicate diagnostics | Student and student-year tables | No current plugin call found |
| GET | `/api/students/crosswalk/schema-candidates` | None | Finds candidate Oracle columns that could improve identity mapping | Oracle `USER_TAB_COLUMNS` metadata | No current plugin call found |

Crosswalk pagination defaults to 500 records and is capped at 2,000 records per request.

## 7. Confirmed use by the Olama ecosystem

### Olama Oracle Sync

Uses the health endpoint and the main family/student endpoints to import data into Olama Core. Confirmed routes are:

- `/api/health`
- `/api/families`
- `/api/families/{family_id}`
- `/api/families/{family_id}/card`
- `/api/families/{family_id}/students`
- `/api/students`
- `/api/students/search`

### Olama Core

Uses Oracle as a detailed read source in its administration screens:

- `/api/families/{family_id}/card`
- `/api/families/{family_id}/financial-card`
- `/api/families/{family_id}/transportation`
- `/api/families/{family_id}/students/{student_id}/card`

### Olama Messages

Uses the message-recipient and report endpoints:

- `/api/messaging/recipients`
- `/api/families/{family_id}/financial-summary`
- `/api/families/{family_id}/payment-report`
- `/api/messaging/transportation/recipients`
- `/api/messaging/transportation/options`
- `/api/families/{family_id}/transportation`

## 8. Important findings before ecosystem evaluation

1. **No incremental-sync contract exists.** There is no `changed_since`, `updated_after`, version token, cursor, ETag, or deletion feed. Olama Oracle Sync must currently fetch records again and compare/upsert them locally.
2. **The two main bulk import routes are not paginated.** `/api/families` and `/api/students` can become expensive as Oracle data grows.
3. **Study-year behavior is inconsistent.** Some routes require it, some default it, and the older family/student list routes silently use the server's configured year.
4. **The root endpoint and original README are incomplete.** They do not list all registered APIs, and the documented single-student path does not match the implemented two-ID route.
5. **Several finance aliases expose the same operation.** A canonical endpoint should be selected before broader plugin adoption.
6. **`/payments` is not a live data feed yet.** It deliberately returns an unavailable empty collection because a distinct, proven Oracle payment entity has not been identified.

## 9. Recommended next documentation step

For the ecosystem evaluation, create a consumer matrix for every Olama plugin with:

- API endpoint used;
- fields consumed;
- local table and field receiving the data;
- source-of-truth owner (Oracle or Olama Core);
- refresh frequency;
- change/deletion handling;
- fallback behavior when Oracle is unavailable.

That matrix will show which endpoints are essential, duplicated, unused, or missing before the synchronization workflow is redesigned.
