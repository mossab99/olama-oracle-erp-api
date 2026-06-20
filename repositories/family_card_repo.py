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


def _map_is_active_name(is_active):
    if is_active == 1:
        return "فعال"

    if is_active == 0:
        return "غير فعال"

    return "غير معروف"


def _map_student_gender_name(student_gender):
    if student_gender == 1:
        return "ذكر"

    if student_gender == 2:
        return "أنثى"

    return "غير معروف"


def _map_student_status_name(student_status):
    if student_status == 1:
        return "مستمر"

    if student_status == 2:
        return "غير مستمر"

    return "غير معروف"


def _add_family_labels(family):
    if family is None:
        return None

    family["is_active_name"] = _map_is_active_name(family.get("is_active"))
    return family


def _add_student_labels(student):
    student["student_gender_name"] = _map_student_gender_name(
        student.get("student_gender")
    )
    student["student_status_name"] = _map_student_status_name(
        student.get("student_status")
    )
    return student


def _add_students_labels(students):
    return [_add_student_labels(student) for student in students]


def get_family_card_family(family_id):
    sql = """
        SELECT
            f.FAMILY_ID AS family_id,

            f.SPONSER_FULL_NAME AS sponsor_full_name,
            f.SPONSER_NAME_S AS sponsor_name_s,

            TRIM(
                f.FATHER_NAME_1 || ' ' ||
                f.FATHER_NAME_2 || ' ' ||
                f.FATHER_NAME_3 || ' ' ||
                f.FATHER_SURNAME
            ) AS father_name,
            f.FATHER_NAME_1 AS father_name_1,
            f.FATHER_NAME_2 AS father_name_2,
            f.FATHER_NAME_3 AS father_name_3,
            f.FATHER_SURNAME AS father_surname,
            f.FATHER_NAME_1_S AS father_name_1_s,
            f.FATHER_NAME_2_S AS father_name_2_s,
            f.FATHER_NAME_3_S AS father_name_3_s,
            f.FATHER_SURNAME_S AS father_surname_s,
            f.FATHER_NATION AS father_nation,
            f.FATHER_NATIONAL_NO AS father_national_no,
            f.FATHER_WORK_PLACE AS father_work_place,
            f.FATHER_JOB AS father_job,
            f.FATHER_WORK_PHONE AS father_work_phone,
            f.FATHER_MOBILE AS father_mobile,
            f.FATHER_EMAIL AS father_email,
            f.FATHER_IS_EMPLOYEE AS father_is_employee,

            f.MOTHER_FULL_NAME AS mother_name,
            f.MOTHER_NATION AS mother_nation,
            f.MOTHER_NATIONAL_NO AS mother_national_no,
            f.MOTHER_WORK_PLACE AS mother_work_place,
            f.MOTHER_JOB AS mother_job,
            f.MOTHER_WORK_PHONE AS mother_work_phone,
            f.MOTHER_MOBILE AS mother_mobile,
            f.MOTHER_EMAIL AS mother_email,
            f.MOTHER_IS_EMPLOYEE AS mother_is_employee,

            f.FAMILY_ADDRESS AS family_address,
            f.FAMILY_HOME_PHONE AS family_home_phone,
            f.BLDNGNO AS building_no,
            f.HOMENO AS home_no,

            f.TRANS_REGION_ID AS trans_region_id,
            tr.REGION_DESC AS trans_region_name,
            tr.REGION_DESC_S AS trans_region_name_s,

            f.FAM_CLASS_ID AS family_class_id,
            f.IS_ACTIVE AS is_active,
            f.NOTES AS notes,

            f.DATE_CREATED AS date_created,
            f.DATE_MODIFIED AS date_modified

        FROM SCH_FAMILY_CARD f

        LEFT JOIN SCH_TRANS_REGIONS tr
            ON tr.REGION_ID = f.TRANS_REGION_ID

        WHERE f.FAMILY_ID = :family_id
    """

    return _add_family_labels(_json_safe_row(query_one(sql, {
        "family_id": family_id
    })))


def get_family_card_students(family_id, study_year=None):
    if study_year:
        sql = """
            SELECT
                s.FAMILY_ID AS family_id,
                s.STUDENT_ID AS student_id,
                s.STUDENT_NATIONAL_NO AS student_national_no,
                TRIM(
                    s.STUDENT_NAME_1 || ' ' ||
                    s.STUDENT_NAME_2 || ' ' ||
                    s.STUDENT_NAME_3 || ' ' ||
                    s.STUDENT_SURNAME
                ) AS student_name,
                s.STUDENT_NAME_1 AS student_name_1,
                s.STUDENT_NAME_2 AS student_name_2,
                s.STUDENT_NAME_3 AS student_name_3,
                s.STUDENT_SURNAME AS student_surname,
                s.STUDENT_NAME_1_S AS student_name_1_s,
                s.STUDENT_NAME_2_S AS student_name_2_s,
                s.STUDENT_NAME_3_S AS student_name_3_s,
                s.STUDENT_SURNAME_S AS student_surname_s,

                s.STUDENT_GENDER AS student_gender,
                s.BIRTH_DATE AS birth_date,
                s.BIRTH_PLACE AS birth_place,
                s.STUDENT_MOBILE AS student_mobile,
                s.EMAIL AS email,
                s.NATIONALITY AS nationality,
                s.MOTHER_NAME AS mother_name,
                s.SCH_MOTHER_MOBILE AS sch_mother_mobile,

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
                y.RENEW_STUDENT AS renew_student

            FROM SCH_STUDENT_CARD s

            JOIN SCH_STUDENT_CARD_YEAR y
                ON y.FAMILY_ID = s.FAMILY_ID
               AND y.STUDENT_ID = s.STUDENT_ID
               AND y.STUDY_YEAR = :study_year

            LEFT JOIN SCH_SCHOOL school
                ON school.SCHOOL_ID = y.SCHOOL_ID

            LEFT JOIN SCH_CLASSES cls
                ON cls.CLASS_ID = y.CLASS_ID

            LEFT JOIN SCH_SECTIONS sec
                ON sec.SECTION_ID = y.SECTION_ID

            WHERE s.FAMILY_ID = :family_id

            ORDER BY
                cls.CLASS_ORDER,
                sec.SECTION_DESC,
                s.STUDENT_ID
        """

        return _add_students_labels(_json_safe_rows(query_all(sql, {
            "family_id": family_id,
            "study_year": study_year
        })))

    sql = """
        SELECT
            s.FAMILY_ID AS family_id,
            s.STUDENT_ID AS student_id,
            s.STUDENT_NATIONAL_NO AS student_national_no,
            TRIM(
                s.STUDENT_NAME_1 || ' ' ||
                s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' ||
                s.STUDENT_SURNAME
            ) AS student_name,
            s.STUDENT_NAME_1 AS student_name_1,
            s.STUDENT_NAME_2 AS student_name_2,
            s.STUDENT_NAME_3 AS student_name_3,
            s.STUDENT_SURNAME AS student_surname,
            s.STUDENT_NAME_1_S AS student_name_1_s,
            s.STUDENT_NAME_2_S AS student_name_2_s,
            s.STUDENT_NAME_3_S AS student_name_3_s,
            s.STUDENT_SURNAME_S AS student_surname_s,

            s.STUDENT_GENDER AS student_gender,
            s.BIRTH_DATE AS birth_date,
            s.BIRTH_PLACE AS birth_place,
            s.STUDENT_MOBILE AS student_mobile,
            s.EMAIL AS email,
            s.NATIONALITY AS nationality,
            s.MOTHER_NAME AS mother_name,
            s.SCH_MOTHER_MOBILE AS sch_mother_mobile,

            NULL AS study_year,
            NULL AS school_id,
            NULL AS school_name,
            NULL AS class_id,
            NULL AS class_name,
            NULL AS branch_id,
            NULL AS section_id,
            NULL AS section_name,
            NULL AS student_status,
            NULL AS registration_date,
            NULL AS withdraw_date,
            NULL AS renew_student

        FROM SCH_STUDENT_CARD s

        WHERE s.FAMILY_ID = :family_id

        ORDER BY s.STUDENT_ID
    """

    return _add_students_labels(_json_safe_rows(query_all(sql, {
        "family_id": family_id
    })))


def get_family_card(family_id, study_year=None):
    family = get_family_card_family(family_id)

    if not family:
        return {
            "family": None,
            "students": [],
        }

    return {
        "family": family,
        "students": get_family_card_students(family_id, study_year),
    }
