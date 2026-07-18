from datetime import date, datetime
from decimal import Decimal

from db import query_all


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)

    return value


def _json_safe_row(row):
    if row is None:
        return None

    return {
        key: _json_safe(value)
        for key, value in row.items()
    }


def _json_safe_rows(rows):
    return [_json_safe_row(row) for row in rows]


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

    return _json_safe_rows(query_all(sql, {
        "family_id": family_id,
        "study_year": study_year
    }))


def get_transportation_buses():
    """Return the confirmed bus master while tolerating Forms item aliases."""
    columns = _table_columns("SCH_BUS_IDS")
    bus_number = _first_column(columns, "BUS_SCHOOL_NUMBER", "BUS_SCHOOL_NUM")
    if not bus_number:
        raise RuntimeError("SCH_BUS_IDS has no supported bus-number column")

    school_id = _first_column(columns, "BUS_SCHOOL_ID", "SCHOOL_ID")
    oracle_id = (
        "TO_CHAR({}) || ':' || TO_CHAR({})".format(school_id, bus_number)
        if school_id
        else "TO_CHAR({})".format(bus_number)
    )
    selections = [
        "{} AS oracle_bus_id".format(oracle_id),
        "{} AS school_id".format(school_id) if school_id else "NULL AS school_id",
        "{} AS bus_number".format(bus_number),
        _select_column(columns, "description", "BUS_DESC"),
        _select_column(columns, "model", "BUS_MODEL"),
        _select_column(columns, "plate_number", "BUS_LICENSE_NUM"),
        _select_column(columns, "last_license_renewal", "LAST_RENEW_LICENSE"),
        _select_column(columns, "next_license_renewal", "NEXT_RENEW_LICENSE"),
        _select_column(columns, "government_number", "BUS_GOV_NUMBER"),
        _select_column(columns, "chassis_number", "BUS_SHUSI_NUMBER", "BUS_CHASSIS_NUMBER"),
        _select_column(columns, "registered_capacity", "BUS_CAPACITY"),
        _select_column(columns, "engine_capacity", "BUS_CC"),
        _select_column(columns, "fuel_type", "BUS_FUEL_TYPE", "FUEL_TYPE"),
        _select_column(columns, "driver_employee_id", "EMP_ID"),
        _select_column(columns, "companion_employee_id", "COMPANION_EMP_ID"),
        "1 AS is_active",
    ]
    sql = "SELECT\n    {}\nFROM SCH_BUS_IDS\nORDER BY {}".format(
        ",\n    ".join(selections),
        bus_number,
    )
    return _json_safe_rows(query_all(sql))


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
    return _json_safe_rows(query_all(sql, {"study_year": study_year}))
