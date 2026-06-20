from datetime import date, datetime
from decimal import Decimal

from db import query_all, query_one


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


def yes_no_label(value):
    if value == 1:
        return "ظ†ط¹ظ…"

    if value == 0:
        return "ظ„ط§"

    return None


def active_label(value):
    if value == 1:
        return "ظپط¹ط§ظ„"

    if value == 0:
        return "ط؛ظٹط± ظپط¹ط§ظ„"

    return None


def student_gender_label(value):
    if value == 1:
        return "ط°ظƒط±"

    if value == 2:
        return "ط£ظ†ط«ظ‰"

    return None


def student_status_label(value):
    if value == 1:
        return "ظ…ط³طھظ…ط±"

    if value == 2:
        return "ظ…ظ†ط³ط­ط¨"

    return None


def trans_route_label(value):
    if value == 1:
        return "ط­ط¶ظˆط± ظˆط¹ظˆط¯ط©"

    if value == 2:
        return "ط­ط¶ظˆط± ظپظ‚ط·"

    if value == 3:
        return "ط¹ظˆط¯ط© ظپظ‚ط·"

    return None


def _add_student_labels(student):
    if student is None:
        return None

    student["student_gender_name"] = student_gender_label(
        student.get("student_gender")
    )
    student["black_list_name"] = yes_no_label(student.get("black_list"))
    student["has_renew_name"] = yes_no_label(student.get("has_renew"))
    student["will_not_renew_name"] = yes_no_label(student.get("will_not_renew"))
    return student


def _add_family_labels(family):
    if family is None:
        return None

    family["is_active_name"] = active_label(family.get("is_active"))
    return family


def _add_academic_labels(academic):
    if academic is None:
        return None

    academic["student_status_name"] = student_status_label(
        academic.get("student_status")
    )
    return academic


def _add_academic_rows_labels(rows):
    return [_add_academic_labels(row) for row in rows]


def _add_transportation_labels(transportation):
    if transportation is None:
        return None

    transportation["is_active_name"] = active_label(
        transportation.get("is_active")
    )
    transportation["trans_route_name"] = trans_route_label(
        transportation.get("trans_route")
    )
    return transportation


def get_student_core(family_id, student_id):
    sql = """
        SELECT
            s.FAMILY_ID AS family_id,
            s.STUDENT_ID AS student_id,
            s.STUDENT_NATIONAL_NO AS student_national_no,
            s.STUDENT_NAME_1 AS student_name_1,
            s.STUDENT_NAME_2 AS student_name_2,
            s.STUDENT_NAME_3 AS student_name_3,
            s.STUDENT_SURNAME AS student_surname,
            TRIM(
                s.STUDENT_NAME_1 || ' ' ||
                s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' ||
                s.STUDENT_SURNAME
            ) AS student_name,
            s.STUDENT_NAME_1_S AS student_name_1_s,
            s.STUDENT_NAME_2_S AS student_name_2_s,
            s.STUDENT_NAME_3_S AS student_name_3_s,
            s.STUDENT_SURNAME_S AS student_surname_s,
            s.STUDENT_GENDER AS student_gender,
            s.BIRTH_DATE AS birth_date,
            s.BIRTH_PLACE AS birth_place,
            s.NATIONALITY AS nationality,
            s.REGISTRATION_DATE AS registration_date,
            s.FROM_SCHOOL AS from_school,
            s.FROM_SCHOOL_AVE AS from_school_ave,
            s.EMAIL AS email,
            s.STUDENT_MOBILE AS student_mobile,
            s.MOTHER_NAME AS mother_name,
            s.SCH_MOTHER_FULL_NAME AS sch_mother_full_name,
            s.SCH_MOTHER_MOBILE AS sch_mother_mobile,
            s.BLACK_LIST AS black_list,
            s.BLACK_LIST_REASON AS black_list_reason,
            s.HAS_RENEW AS has_renew,
            s.RENEW_YEAR AS renew_year,
            s.RENEW_DATE AS renew_date,
            s.WILL_NOT_RENEW AS will_not_renew,
            s.NO_RENEW_REASON AS no_renew_reason,
            s.NON_TRANS_ID AS non_trans_id,
            s.STUDENT_HEALTH AS student_health,
            s.SOCIAL_CASE AS social_case,
            s.REFUGEE_EMIGRANT AS refugee_emigrant,
            s.RELIGION_ID AS religion_id,
            s.PASS_FAIL AS pass_fail,
            s.MONTHLY_INCOME AS monthly_income,
            s.ADDRESS_1 AS address_1,
            s.ADDRESS_2 AS address_2,
            s.ADDRESS_3 AS address_3,
            s.ADDRESS_4 AS address_4,
            s.ADDRESS_5 AS address_5,
            s.DATE_CREATED AS date_created,
            s.DATE_MODIFIED AS date_modified

        FROM SCH_STUDENT_CARD s

        WHERE s.FAMILY_ID = :family_id
          AND s.STUDENT_ID = :student_id
    """

    return _add_student_labels(_json_safe_row(query_one(sql, {
        "family_id": family_id,
        "student_id": student_id
    })))


def get_student_family_summary(family_id):
    sql = """
        SELECT
            f.FAMILY_ID AS family_id,
            f.SPONSER_FULL_NAME AS sponsor_full_name,
            TRIM(
                f.FATHER_NAME_1 || ' ' ||
                f.FATHER_NAME_2 || ' ' ||
                f.FATHER_NAME_3 || ' ' ||
                f.FATHER_SURNAME
            ) AS father_name,
            f.FATHER_MOBILE AS father_mobile,
            f.FATHER_NATIONAL_NO AS father_national_no,
            f.MOTHER_FULL_NAME AS mother_name,
            f.MOTHER_MOBILE AS mother_mobile,
            f.MOTHER_NATIONAL_NO AS mother_national_no,
            f.FAMILY_ADDRESS AS family_address,
            f.TRANS_REGION_ID AS trans_region_id,
            tr.REGION_DESC AS trans_region_name,
            f.IS_ACTIVE AS is_active

        FROM SCH_FAMILY_CARD f

        LEFT JOIN SCH_TRANS_REGIONS tr
            ON tr.REGION_ID = f.TRANS_REGION_ID

        WHERE f.FAMILY_ID = :family_id
    """

    return _add_family_labels(_json_safe_row(query_one(sql, {
        "family_id": family_id
    })))


def get_student_academic_current(family_id, student_id, study_year):
    sql = """
        SELECT
            y.STUDY_YEAR AS study_year,
            y.SCHOOL_ID AS school_id,
            school.SCHOOL_DESC AS school_name,
            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,
            y.BRANCH_ID AS branch_id,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,
            y.STUDENT_STATUS AS student_status,
            y.REGISTRATION_DATE AS registration_date,
            y.WITHDRAW_DATE AS withdraw_date,
            y.RENEW_STUDENT AS renew_student,
            y.SYSTEM_RESPECT AS system_respect,
            y.NO_ABSENT AS no_absent,
            y.FINAL_MRK_RESULT AS final_mrk_result,
            y.NOTES AS notes,
            y.DATE_CREATED AS date_created,
            y.DATE_MODIFIED AS date_modified

        FROM SCH_STUDENT_CARD_YEAR y

        LEFT JOIN SCH_SCHOOL school
            ON school.SCHOOL_ID = y.SCHOOL_ID

        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID

        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID

        WHERE y.FAMILY_ID = :family_id
          AND y.STUDENT_ID = :student_id
          AND y.STUDY_YEAR = :study_year
    """

    return _add_academic_labels(_json_safe_row(query_one(sql, {
        "family_id": family_id,
        "student_id": student_id,
        "study_year": study_year
    })))


def get_student_academic_history(family_id, student_id):
    sql = """
        SELECT
            y.STUDY_YEAR AS study_year,
            y.SCHOOL_ID AS school_id,
            school.SCHOOL_DESC AS school_name,
            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,
            y.BRANCH_ID AS branch_id,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,
            y.STUDENT_STATUS AS student_status,
            y.REGISTRATION_DATE AS registration_date,
            y.WITHDRAW_DATE AS withdraw_date,
            y.RENEW_STUDENT AS renew_student,
            y.SYSTEM_RESPECT AS system_respect,
            y.NO_ABSENT AS no_absent,
            y.FINAL_MRK_RESULT AS final_mrk_result,
            y.NOTES AS notes,
            y.DATE_CREATED AS date_created,
            y.DATE_MODIFIED AS date_modified

        FROM SCH_STUDENT_CARD_YEAR y

        LEFT JOIN SCH_SCHOOL school
            ON school.SCHOOL_ID = y.SCHOOL_ID

        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID

        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID

        WHERE y.FAMILY_ID = :family_id
          AND y.STUDENT_ID = :student_id

        ORDER BY y.STUDY_YEAR
    """

    return _add_academic_rows_labels(_json_safe_rows(query_all(sql, {
        "family_id": family_id,
        "student_id": student_id
    })))


def get_student_transportation_current(family_id, student_id, study_year):
    sql = """
        SELECT
            st.STUDY_YEAR AS study_year,
            st.FAMILY_ID AS family_id,
            st.STUDENT_ID AS student_id,
            st.GROUP_ID AS group_id,
            grp.GROUP_DESC AS group_name,
            st.TRANS_ROUTE AS trans_route,
            st.ARRIVAL_BUS AS arrival_bus,
            arrival_bus.BUS_DESC AS arrival_bus_name,
            st.ARRIVAL_BUS_SEQ AS arrival_bus_seq,
            st.DEPARTURE_BUS AS departure_bus,
            departure_bus.BUS_DESC AS departure_bus_name,
            st.DEPARTURE_BUS_SEQ AS departure_bus_seq,
            st.FROM_DATE AS from_date,
            st.TO_DATE AS to_date,
            st.IS_ACTIVE AS is_active,
            st.TRANS_AMOUNT AS trans_amount,
            st.DATE_CREATED AS date_created,
            st.DATE_MODIFIED AS date_modified

        FROM SCH_STUDENT_TRANS st

        LEFT JOIN SCH_TRANS_GROUPS grp
            ON grp.GROUP_ID = st.GROUP_ID

        LEFT JOIN SCH_BUS_IDS arrival_bus
            ON arrival_bus.BUS_SCHOOL_NUMBER = st.ARRIVAL_BUS

        LEFT JOIN SCH_BUS_IDS departure_bus
            ON departure_bus.BUS_SCHOOL_NUMBER = st.DEPARTURE_BUS

        WHERE st.FAMILY_ID = :family_id
          AND st.STUDENT_ID = :student_id
          AND st.STUDY_YEAR = :study_year
    """

    return _add_transportation_labels(_json_safe_row(query_one(sql, {
        "family_id": family_id,
        "student_id": student_id,
        "study_year": study_year
    })))


def get_student_card(family_id, student_id, study_year):
    student = get_student_core(family_id, student_id)

    if student is None:
        return {
            "student": None,
            "family": None,
            "academic_current": None,
            "academic_history": [],
            "transportation_current": None
        }

    return {
        "student": student,
        "family": get_student_family_summary(family_id),
        "academic_current": get_student_academic_current(
            family_id,
            student_id,
            study_year
        ),
        "academic_history": get_student_academic_history(family_id, student_id),
        "transportation_current": get_student_transportation_current(
            family_id,
            student_id,
            study_year
        )
    }
