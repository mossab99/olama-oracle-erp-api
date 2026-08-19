"""Bulk, read-only projections used by the WordPress Fast Sync client."""

from datetime import date, datetime
from decimal import Decimal

from db import query_all, query_one


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _safe_rows(rows):
    return [
        {key: _json_safe(value) for key, value in row.items()}
        for row in rows
    ]


def _family_binds(family_ids, study_year=None):
    binds = {"family_{}".format(index): family_id for index, family_id in enumerate(family_ids)}
    if study_year is not None:
        binds["study_year"] = study_year
    placeholders = ", ".join(":family_{}".format(index) for index in range(len(family_ids)))
    return placeholders, binds


def _group(rows, key="family_id"):
    grouped = {}
    for row in rows:
        grouped.setdefault(str(row.get(key)), []).append(row)
    return grouped


def get_fast_sync_page(study_year, limit=50, cursor=0):
    """Return sync-ready family bundles using seven bulk Oracle queries per page."""
    families = _safe_rows(query_all("""
        SELECT * FROM (
            SELECT
                f.FAMILY_ID AS family_id,
                f.SPONSER_FULL_NAME AS sponsor_full_name,
                f.SPONSER_NAME_S AS sponsor_name_s,
                TRIM(f.FATHER_NAME_1 || ' ' || f.FATHER_NAME_2 || ' ' ||
                     f.FATHER_NAME_3 || ' ' || f.FATHER_SURNAME) AS father_name,
                f.FATHER_MOBILE AS father_mobile,
                f.FATHER_EMAIL AS father_email,
                f.FATHER_NATIONAL_NO AS father_national_no,
                f.FATHER_NATION AS father_nation,
                f.FATHER_WORK_PLACE AS father_work_place,
                f.FATHER_JOB AS father_job,
                f.FATHER_WORK_PHONE AS father_work_phone,
                f.FATHER_IS_EMPLOYEE AS father_is_employee,
                f.MOTHER_FULL_NAME AS mother_name,
                f.MOTHER_MOBILE AS mother_mobile,
                f.MOTHER_EMAIL AS mother_email,
                f.MOTHER_NATIONAL_NO AS mother_national_no,
                f.MOTHER_NATION AS mother_nation,
                f.MOTHER_WORK_PLACE AS mother_work_place,
                f.MOTHER_JOB AS mother_job,
                f.MOTHER_WORK_PHONE AS mother_work_phone,
                f.MOTHER_IS_EMPLOYEE AS mother_is_employee,
                f.FAMILY_ADDRESS AS family_address,
                f.FAMILY_HOME_PHONE AS family_home_phone,
                f.BLDNGNO AS building_no,
                f.HOMENO AS home_no,
                f.TRANS_REGION_ID AS trans_region_id,
                tr.REGION_DESC AS trans_region_name,
                f.FAM_CLASS_ID AS family_class_id,
                fc.CLASS_DESC AS family_class_name,
                f.IS_ACTIVE AS is_active,
                f.NOTES AS notes,
                f.DATE_CREATED AS date_created,
                f.DATE_MODIFIED AS date_modified
            FROM SCH_FAMILY_CARD f
            LEFT JOIN SCH_TRANS_REGIONS tr ON tr.REGION_ID = f.TRANS_REGION_ID
            LEFT JOIN SCH_FAMILY_CLASS fc ON fc.CLASS_ID = f.FAM_CLASS_ID
            WHERE f.IS_ACTIVE = 1 AND f.FAMILY_ID > :cursor
            ORDER BY f.FAMILY_ID
        ) WHERE ROWNUM <= :limit
    """, {"cursor": cursor, "limit": limit}))

    total_row = query_one("""
        SELECT COUNT(*) AS total FROM SCH_FAMILY_CARD WHERE IS_ACTIVE = 1
    """) or {}
    total = int(total_row.get("total") or 0)
    if not families:
        return {"families": [], "total": total, "next_cursor": None, "has_more": False}

    family_ids = [int(family["family_id"]) for family in families]
    in_sql, binds = _family_binds(family_ids, study_year)

    students = _safe_rows(query_all("""
        SELECT
            s.FAMILY_ID AS family_id, s.STUDENT_ID AS student_id,
            s.STUDENT_NATIONAL_NO AS student_national_no,
            TRIM(s.STUDENT_NAME_1 || ' ' || s.STUDENT_NAME_2 || ' ' ||
                 s.STUDENT_NAME_3 || ' ' || s.STUDENT_SURNAME) AS student_name,
            s.STUDENT_NAME_1 AS student_name_1, s.STUDENT_NAME_2 AS student_name_2,
            s.STUDENT_NAME_3 AS student_name_3, s.STUDENT_SURNAME AS student_surname,
            s.STUDENT_NAME_1_S AS student_name_1_s, s.STUDENT_NAME_2_S AS student_name_2_s,
            s.STUDENT_NAME_3_S AS student_name_3_s, s.STUDENT_SURNAME_S AS student_surname_s,
            s.STUDENT_GENDER AS student_gender, s.BIRTH_DATE AS birth_date,
            s.BIRTH_PLACE AS birth_place, s.STUDENT_MOBILE AS student_mobile,
            s.EMAIL AS email, s.NATIONALITY AS nationality,
            s.MOTHER_NAME AS mother_name, s.SCH_MOTHER_MOBILE AS sch_mother_mobile,
            y.STUDY_YEAR AS study_year, y.SCHOOL_ID AS school_id,
            school.SCHOOL_DESC AS school_name, y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name, y.BRANCH_ID AS branch_id,
            y.SECTION_ID AS section_id, sec.SECTION_DESC AS section_name,
            y.STUDENT_STATUS AS student_status, y.REGISTRATION_DATE AS registration_date,
            y.WITHDRAW_DATE AS withdraw_date, y.RENEW_STUDENT AS renew_student
        FROM SCH_STUDENT_CARD s
        JOIN SCH_STUDENT_CARD_YEAR y ON y.FAMILY_ID = s.FAMILY_ID
            AND y.STUDENT_ID = s.STUDENT_ID AND y.STUDY_YEAR = :study_year
        LEFT JOIN SCH_SCHOOL school ON school.SCHOOL_ID = y.SCHOOL_ID
        LEFT JOIN SCH_CLASSES cls ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec ON sec.SECTION_ID = y.SECTION_ID
        WHERE s.FAMILY_ID IN (""" + in_sql + ") ORDER BY s.FAMILY_ID, s.STUDENT_ID""", binds))

    summaries = _safe_rows(query_all("""
        SELECT FAMILY_ID AS family_id, STUDY_YEAR AS study_year,
            BEGIN_DR AS begin_debit, BEGIN_CR AS begin_credit,
            YEAR_DR AS year_debit, YEAR_CR AS year_credit,
            NVL(BEGIN_DR, 0) - NVL(BEGIN_CR, 0) + NVL(YEAR_DR, 0) - NVL(YEAR_CR, 0) AS balance
        FROM SCH_FIN_FAMILY_CARD
        WHERE STUDY_YEAR = :study_year AND FAMILY_ID IN (""" + in_sql + ")""", binds))

    dues = _safe_rows(query_all("""
        SELECT FAMILY_ID AS family_id, DUE_DATE AS due_date,
            PERCENT_VALUE AS percent_value, DUE_AMOUNT AS due_amount,
            PAID_AMOUNT AS paid_amount, RECEIPT_PAID AS receipt_paid,
            NVL(DUE_AMOUNT, 0) - NVL(PAID_AMOUNT, 0) - NVL(RECEIPT_PAID, 0) AS balance
        FROM SCH_FAMILY_DUE_ALLOC
        WHERE STUDY_YEAR = :study_year AND FAMILY_ID IN (""" + in_sql + """)
        ORDER BY FAMILY_ID, DUE_DATE""", binds))

    transactions = _safe_rows(query_all("""
        SELECT fs.SERIAL_ID AS serial_id, fs.FAMILY_ID AS family_id,
            fs.STUDENT_ID AS student_id,
            TRIM(s.STUDENT_NAME_1 || ' ' || s.STUDENT_NAME_2 || ' ' ||
                 s.STUDENT_NAME_3 || ' ' || s.STUDENT_SURNAME) AS student_name,
            fs.TITLE_ID AS title_id, fs.TITLE_TYPE AS title_type,
            NVL(ft.TITLE_DESC, TO_CHAR(fs.TITLE_ID)) AS title,
            ft.TITLE_DESC AS title_desc, ft.TITLE_DESC_S AS title_desc_s,
            fs.TRANS_DATE AS trans_date, fs.RECEIPT_ID AS receipt_id,
            fs.DR_AMOUNT AS debit_amount, fs.CR_AMOUNT AS credit_amount,
            fs.NOTES AS notes, fs.TRANS_STATUS AS trans_status,
            fs.BEGIN_YEAR AS begin_year
        FROM SCH_FIN_STUDENT_CARD fs
        LEFT JOIN SCH_STUDENT_CARD s ON s.FAMILY_ID = fs.FAMILY_ID AND s.STUDENT_ID = fs.STUDENT_ID
        LEFT JOIN SCH_FEES_TITLES ft ON ft.TITLE_ID = fs.TITLE_ID AND ft.TITLE_TYPE = fs.TITLE_TYPE
        WHERE fs.STUDY_YEAR = :study_year AND fs.FAMILY_ID IN (""" + in_sql + """)
        ORDER BY fs.FAMILY_ID, fs.TRANS_DATE, fs.RECEIPT_ID, fs.SERIAL_ID""", binds))

    transportation = _safe_rows(query_all("""
        SELECT st.FAMILY_ID AS family_id, st.STUDENT_ID AS student_id,
            TRIM(s.STUDENT_NAME_1 || ' ' || s.STUDENT_NAME_2 || ' ' ||
                 s.STUDENT_NAME_3 || ' ' || s.STUDENT_SURNAME) AS student_name,
            st.STUDY_YEAR AS study_year, y.SCHOOL_ID AS school_id,
            school.SCHOOL_DESC AS school_name, y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name, y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name, st.GROUP_ID AS group_id,
            grp.GROUP_DESC AS group_name, grp.GROUP_DESC_S AS group_name_s,
            st.TRANS_ROUTE AS trans_route,
            CASE st.TRANS_ROUTE WHEN 1 THEN 'حضور وعودة' WHEN 2 THEN 'حضور فقط'
                WHEN 3 THEN 'عودة فقط' ELSE 'غير معروف' END AS trans_route_name,
            st.ARRIVAL_BUS AS arrival_bus, arrival_bus.BUS_DESC AS arrival_bus_name,
            st.ARRIVAL_BUS_SEQ AS arrival_bus_seq,
            st.DEPARTURE_BUS AS departure_bus, departure_bus.BUS_DESC AS departure_bus_name,
            st.DEPARTURE_BUS_SEQ AS departure_bus_seq, st.FROM_DATE AS from_date,
            st.TO_DATE AS to_date, st.IS_ACTIVE AS is_active,
            st.TRANS_AMOUNT AS trans_amount
        FROM SCH_STUDENT_TRANS st
        LEFT JOIN SCH_STUDENT_CARD s ON s.FAMILY_ID = st.FAMILY_ID AND s.STUDENT_ID = st.STUDENT_ID
        LEFT JOIN SCH_STUDENT_CARD_YEAR y ON y.FAMILY_ID = st.FAMILY_ID
            AND y.STUDENT_ID = st.STUDENT_ID AND y.STUDY_YEAR = st.STUDY_YEAR
        LEFT JOIN SCH_SCHOOL school ON school.SCHOOL_ID = y.SCHOOL_ID
        LEFT JOIN SCH_CLASSES cls ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec ON sec.SECTION_ID = y.SECTION_ID
        LEFT JOIN SCH_TRANS_GROUPS grp ON grp.GROUP_ID = st.GROUP_ID
        LEFT JOIN SCH_BUS_IDS arrival_bus ON arrival_bus.BUS_SCHOOL_NUMBER = st.ARRIVAL_BUS
        LEFT JOIN SCH_BUS_IDS departure_bus ON departure_bus.BUS_SCHOOL_NUMBER = st.DEPARTURE_BUS
        WHERE st.STUDY_YEAR = :study_year AND st.FAMILY_ID IN (""" + in_sql + """)
        ORDER BY st.FAMILY_ID, st.STUDENT_ID""", binds))

    students_by_family = _group(students)
    summaries_by_family = {str(row["family_id"]): row for row in summaries}
    dues_by_family = _group(dues)
    transactions_by_family = _group(transactions)
    transportation_by_family = _group(transportation)
    bundles = []
    for family in families:
        key = str(family["family_id"])
        family["is_active_name"] = (
            "فعال" if family.get("is_active") == 1 else "غير فعال"
        )
        for student in students_by_family.get(key, []):
            student["student_gender_name"] = {
                1: "ذكر", 2: "أنثى"
            }.get(student.get("student_gender"), "غير معروف")
            student["student_status_name"] = {
                1: "مستمر", 2: "غير مستمر"
            }.get(student.get("student_status"), "غير معروف")
        bundles.append({
            "family": family,
            "students": students_by_family.get(key, []),
            "financial": {
                "family_summary": summaries_by_family.get(key),
                "due_allocations": dues_by_family.get(key, []),
                "student_transactions": transactions_by_family.get(key, []),
            },
            "transportation": transportation_by_family.get(key, []),
        })

    next_cursor = int(families[-1]["family_id"])
    return {
        "families": bundles,
        "total": total,
        "next_cursor": next_cursor,
        "has_more": len(families) == limit,
    }
