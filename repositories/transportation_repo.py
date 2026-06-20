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
