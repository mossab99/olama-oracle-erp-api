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


def _table_columns(table_name):
    rows = query_all(
        """
        SELECT COLUMN_NAME
        FROM USER_TAB_COLUMNS
        WHERE TABLE_NAME = :table_name
        """,
        {"table_name": table_name},
    )
    return {str(row["column_name"]).upper() for row in rows}


def _first_column(columns, *candidates):
    return next((candidate for candidate in candidates if candidate in columns), None)


def _first_prefixed(columns, *prefixes):
    return next(
        (
            column
            for prefix in prefixes
            for column in sorted(columns)
            if column.startswith(prefix)
        ),
        None,
    )


def _select_column(columns, alias, *candidates):
    column = _first_column(columns, *candidates)
    return "{} AS {}".format(column, alias) if column else "NULL AS {}".format(alias)


def get_family_transportation(family_id, study_year):
    sql = """
        SELECT
            st.FAMILY_ID AS family_id,
            st.STUDENT_ID AS student_id,
            TRIM(
                s.STUDENT_NAME_1 || ' ' ||
                s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' ||
                s.STUDENT_SURNAME
            ) AS student_name,
            st.STUDY_YEAR AS study_year,

            y.SCHOOL_ID AS school_id,
            school.SCHOOL_DESC AS school_name,
            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,

            st.GROUP_ID AS group_id,
            grp.GROUP_DESC AS group_name,
            grp.GROUP_DESC_S AS group_name_s,

            st.TRANS_ROUTE AS trans_route,
            CASE st.TRANS_ROUTE
                WHEN 1 THEN 'حضور وعودة'
                WHEN 2 THEN 'حضور فقط'
                WHEN 3 THEN 'عودة فقط'
                ELSE 'غير معروف'
            END AS trans_route_name,

            st.ARRIVAL_BUS AS arrival_bus,
            CASE
                WHEN NVL(st.ARRIVAL_BUS, 0) = 0 THEN 'غير محدد'
                ELSE arrival_bus.BUS_DESC
            END AS arrival_bus_name,
            st.ARRIVAL_BUS_SEQ AS arrival_bus_seq,

            st.DEPARTURE_BUS AS departure_bus,
            CASE
                WHEN NVL(st.DEPARTURE_BUS, 0) = 0 THEN 'غير محدد'
                ELSE departure_bus.BUS_DESC
            END AS departure_bus_name,
            st.DEPARTURE_BUS_SEQ AS departure_bus_seq,

            st.FROM_DATE AS from_date,
            st.TO_DATE AS to_date,

            st.IS_ACTIVE AS is_active,
            CASE st.IS_ACTIVE
                WHEN 1 THEN 'فعال'
                WHEN 0 THEN 'غير فعال'
                ELSE 'غير معروف'
            END AS is_active_name,

            st.TRANS_AMOUNT AS trans_amount

        FROM SCH_STUDENT_TRANS st

        LEFT JOIN SCH_STUDENT_CARD s
            ON s.FAMILY_ID = st.FAMILY_ID
           AND s.STUDENT_ID = st.STUDENT_ID

        LEFT JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = st.FAMILY_ID
           AND y.STUDENT_ID = st.STUDENT_ID
           AND y.STUDY_YEAR = st.STUDY_YEAR

        LEFT JOIN SCH_SCHOOL school
            ON school.SCHOOL_ID = y.SCHOOL_ID

        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID

        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID

        LEFT JOIN SCH_TRANS_GROUPS grp
            ON grp.GROUP_ID = st.GROUP_ID

        LEFT JOIN SCH_BUS_IDS arrival_bus
            ON arrival_bus.BUS_SCHOOL_NUMBER = st.ARRIVAL_BUS

        LEFT JOIN SCH_BUS_IDS departure_bus
            ON departure_bus.BUS_SCHOOL_NUMBER = st.DEPARTURE_BUS

        WHERE st.FAMILY_ID = :family_id
          AND st.STUDY_YEAR = :study_year

        ORDER BY
            cls.CLASS_ORDER,
            sec.SECTION_DESC,
            st.STUDENT_ID
    """

    return _rows(query_all(sql, {
        "family_id": family_id,
        "study_year": study_year
    }))


def get_transportation_buses(include_inactive=True):
    """Return the confirmed bus master while tolerating Forms item aliases."""
    columns = _table_columns("SCH_BUS_IDS")
    bus_number = _first_column(columns, "BUS_SCHOOL_NUMBER", "BUS_SCHOOL_NUM")
    if not bus_number:
        raise RuntimeError("SCH_BUS_IDS has no supported bus-number column")

    school_id = _first_column(columns, "BUS_SCHOOL_ID", "SCHOOL_ID")
    # BUS_SCHOOL_NUMBER is the identifier used by student transportation
    # assignments. BUS_SCHOOL_ID is a separate, nullable school reference.
    oracle_id = "TO_CHAR({})".format(bus_number)
    plate_column = _first_column(
        columns,
        "BUS_LICENSE_NUM",
        "BUS_LICENSE_NUMBER",
        "BUS_LICENCE_NUM",
        "BUS_LICENCE_NUMBER",
    ) or _first_prefixed(columns, "BUS_LICENSE_NUM", "BUS_LICENCE_NUM")
    last_renew_column = _first_column(
        columns,
        "LAST_RENEW_LICENSE",
        "LAST_RENEW_LICI",
        "LAST_RENEW_LICENCE",
        "LAST_LICENSE_RENEWAL",
    ) or _first_prefixed(columns, "LAST_RENEW_LIC")
    next_renew_column = _first_column(
        columns,
        "NEXT_RENEW_LICENSE",
        "NEXT_RENEW_LICI",
        "NEXT_RENEW_LICENCE",
        "NEXT_LICENSE_RENEWAL",
    ) or _first_prefixed(columns, "NEXT_RENEW_LIC")

    selections = [
        "{} AS oracle_bus_id".format(oracle_id),
        "{} AS school_id".format(school_id) if school_id else "NULL AS school_id",
        "{} AS bus_number".format(bus_number),
        _select_column(columns, "description", "BUS_DESC"),
        _select_column(columns, "model", "BUS_MODEL"),
        "{} AS driver_license_number".format(plate_column) if plate_column else "NULL AS driver_license_number",
        "{} AS last_license_renewal".format(last_renew_column) if last_renew_column else "NULL AS last_license_renewal",
        "{} AS next_license_renewal".format(next_renew_column) if next_renew_column else "NULL AS next_license_renewal",
        _select_column(columns, "government_number", "BUS_GOV_NUMBER"),
        _select_column(columns, "chassis_number", "BUS_SHUSI_NUMBER", "BUS_CHASSIS_NUMBER"),
        _select_column(columns, "registered_capacity", "BUS_CAPACITY"),
        _select_column(columns, "engine_capacity", "BUS_CC"),
        _select_column(columns, "fuel_type", "BUS_FUEL_TYPE", "FUEL_TYPE"),
        _select_column(columns, "driver_employee_id", "EMP_ID"),
        _select_column(
            columns,
            "driver_employee_name",
            "EMP_ID_DESC",
            "EMP_DESC",
            "DRIVER_NAME",
        ),
        _select_column(columns, "companion_employee_id", "COMPANION_EMP_ID"),
        _select_column(
            columns,
            "companion_employee_name",
            "COMPANION_EMP_ID_DESC",
            "COMPANION_EMP_DESC",
            "COMPANION_NAME",
        ),
        "1 AS is_active",
    ]
    sql = "SELECT\n    {}\nFROM SCH_BUS_IDS\nORDER BY {}".format(
        ",\n    ".join(selections),
        bus_number,
    )
    return _rows(query_all(sql))


def get_transportation_regions(study_year):
    """Build source-region demand from proven family and student-year tables."""
    sql = """
        SELECT
            f.TRANS_REGION_ID AS oracle_region_id,
            MIN(tr.REGION_DESC) AS region_name,
            MIN(f.FAMILY_ADDRESS) AS sample_address,
            COUNT(DISTINCT f.FAMILY_ID) AS family_count,
            COUNT(DISTINCT TO_CHAR(y.FAMILY_ID) || ':' || TO_CHAR(y.STUDENT_ID))
                AS student_count
        FROM SCH_FAMILY_CARD f
        LEFT JOIN SCH_TRANS_REGIONS tr
            ON tr.REGION_ID = f.TRANS_REGION_ID
        LEFT JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = f.FAMILY_ID
           AND y.STUDY_YEAR = :study_year
           AND y.STUDENT_STATUS = 1
        WHERE f.TRANS_REGION_ID IS NOT NULL
        GROUP BY f.TRANS_REGION_ID
        ORDER BY f.TRANS_REGION_ID
    """
    return _rows(query_all(sql, {"study_year": study_year}))
