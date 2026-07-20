"""Read-only transportation queries for the Oracle ERP.

Oracle remains the source of truth for master data.  This repository never
inserts, updates, deletes, or invokes PL/SQL.
"""

from datetime import date, datetime
from decimal import Decimal

from db import query_all, query_one


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _row(row):
    return None if row is None else {
        key: _json_safe(value) for key, value in row.items()
    }


def _rows(rows):
    return [_row(row) for row in rows]


def _page(inner_sql, params, limit, offset, order_by):
    sql = f"""
        SELECT *
        FROM (
            SELECT transport_rows.*, ROWNUM AS rn
            FROM (
                {inner_sql}
                ORDER BY {order_by}
            ) transport_rows
            WHERE ROWNUM <= :max_row
        )
        WHERE rn > :offset
    """
    page_params = dict(params)
    page_params.update({"max_row": offset + limit, "offset": offset})
    result = _rows(query_all(sql, page_params))
    for item in result:
        item.pop("rn", None)
    return result


def get_transportation_students(
    study_year, limit=500, offset=0, family_id=None, region_id=None
):
    """Return the normalized Forms-backed student transportation projection."""
    filters = ["t.STUDY_YEAR = :study_year"]
    params = {"study_year": study_year}
    if family_id is not None:
        filters.append("t.FAMILY_ID = :family_id")
        params["family_id"] = family_id
    if region_id is not None:
        filters.append("t.TRANS_REGION_ID = :region_id")
        params["region_id"] = region_id

    # SCH_STUDENT_TOT_TRANS is the confirmed Forms projection.  Bus fields are
    # deliberately named legacy_* because Olama owns all new allocations.
    inner = f"""
        SELECT
            t.STUDENT_ID AS student_id,
            t.STUDENT_NAME AS student_name,
            t.FAMILY_ID AS family_id,
            t.STUDY_YEAR AS study_year,
            t.GROUP_DESC AS grade_name,
            t.CLASS_DESC AS class_name,
            t.SECTION_DESC AS section_name,
            t.TRANS_REGION_ID AS oracle_region_id,
            t.FAMILY_ADDRESS AS family_address,
            t.HOMENO AS house_number,
            t.BLDNGNO AS building_number,
            t.DEPARTURE_X AS morning_enabled,
            t.DEPARTURE_BUS AS legacy_morning_bus_id,
            t.DEPARTURE_BUS_SEQ AS legacy_morning_sequence,
            t.ARRIVE_X AS afternoon_enabled,
            t.ARRIVAL_BUS AS legacy_afternoon_bus_id,
            t.ARRIVAL_BUS_SEQ AS legacy_afternoon_sequence,
            t.STD_ARV_SEQ_SET AS legacy_afternoon_sequence_set
        FROM SCH_STUDENT_TOT_TRANS t
        WHERE {" AND ".join(filters)}
    """
    return _page(
        inner, params, limit, offset,
        "t.FAMILY_ID, t.STUDENT_ID"
    )


def get_transportation_student_count(study_year, family_id=None, region_id=None):
    filters = ["t.STUDY_YEAR = :study_year"]
    params = {"study_year": study_year}
    if family_id is not None:
        filters.append("t.FAMILY_ID = :family_id")
        params["family_id"] = family_id
    if region_id is not None:
        filters.append("t.TRANS_REGION_ID = :region_id")
        params["region_id"] = region_id
    result = query_one(
        f"""SELECT COUNT(*) AS total
            FROM SCH_STUDENT_TOT_TRANS t
            WHERE {" AND ".join(filters)}""",
        params,
    )
    return int((result or {}).get("total", 0))


def get_transportation_buses(include_inactive=True):
    # The Forms screenshot confirms a visible status item but not its database
    # column name. Do not guess a column and break the fleet endpoint; status is
    # normalized to active until the Forms block query is confirmed.
    sql = """
        SELECT
            b.BUS_SCHOOL_ID AS oracle_bus_id,
            b.BUS_SCHOOL_NUM AS bus_number,
            b.BUS_DESC AS description,
            b.BUS_MODEL AS model,
            b.BUS_LICENSE_NUM AS plate_number,
            b.LAST_RENEW_LICENSE AS last_license_renewal,
            b.NEXT_RENEW_LICENSE AS next_license_renewal,
            b.BUS_GOV_NUMBER AS government_number,
            b.BUS_SHUSI_NUMBER AS chassis_number,
            b.BUS_CAPACITY AS registered_capacity,
            b.BUS_CC AS engine_capacity,
            b.EMP_ID AS driver_employee_id,
            b.COMPANION_EMP_ID AS companion_employee_id,
            1 AS is_active
        FROM SCH_BUS_IDS b
        ORDER BY b.BUS_SCHOOL_NUM
    """
    return _rows(query_all(sql))


def get_transportation_regions(study_year):
    sql = """
        SELECT
            t.TRANS_REGION_ID AS oracle_region_id,
            MIN(t.FAMILY_ADDRESS) AS sample_address,
            COUNT(DISTINCT t.FAMILY_ID) AS family_count,
            COUNT(*) AS student_count
        FROM SCH_STUDENT_TOT_TRANS t
        WHERE t.STUDY_YEAR = :study_year
          AND t.TRANS_REGION_ID IS NOT NULL
        GROUP BY t.TRANS_REGION_ID
        ORDER BY t.TRANS_REGION_ID
    """
    return _rows(query_all(sql, {"study_year": study_year}))


def get_transportation_employees():
    """Return confirmed fleet employee references without guessing a name table."""
    sql = """
        SELECT DISTINCT employee_id, employee_role
        FROM (
            SELECT b.EMP_ID AS employee_id, 'driver' AS employee_role
            FROM SCH_BUS_IDS b
            WHERE b.EMP_ID IS NOT NULL
            UNION ALL
            SELECT b.COMPANION_EMP_ID AS employee_id, 'companion' AS employee_role
            FROM SCH_BUS_IDS b
            WHERE b.COMPANION_EMP_ID IS NOT NULL
        )
        ORDER BY employee_role, employee_id
    """
    return _rows(query_all(sql))


def get_transportation_summary(study_year):
    totals = _row(query_one("""
        SELECT
            COUNT(*) AS students,
            COUNT(DISTINCT t.FAMILY_ID) AS families,
            COUNT(DISTINCT t.TRANS_REGION_ID) AS regions,
            SUM(CASE WHEN NVL(t.DEPARTURE_X, 0) <> 0 THEN 1 ELSE 0 END)
                AS morning_students,
            SUM(CASE WHEN NVL(t.ARRIVE_X, 0) <> 0 THEN 1 ELSE 0 END)
                AS afternoon_students
        FROM SCH_STUDENT_TOT_TRANS t
        WHERE t.STUDY_YEAR = :study_year
    """, {"study_year": study_year})) or {}
    bus_totals = _row(query_one("""
        SELECT
            COUNT(*) AS buses,
            SUM(NVL(b.BUS_CAPACITY, 0)) AS registered_capacity
        FROM SCH_BUS_IDS b
    """)) or {}
    totals.update(bus_totals)
    return totals


def get_family_transportation(family_id, study_year):
    """Compatibility contract retained for existing Olama consumers."""
    return get_transportation_students(
        study_year=study_year,
        family_id=family_id,
        limit=200,
        offset=0,
    )
