from db import query_all, query_one
from config import Config


def get_all_families():
    sql = """
        SELECT
            f.FAMILY_ID AS family_id,

            TRIM(
                f.FATHER_NAME_1 || ' ' ||
                f.FATHER_NAME_2 || ' ' ||
                f.FATHER_NAME_3 || ' ' ||
                f.FATHER_SURNAME
            ) AS father_name,

            f.SPONSER_FULL_NAME AS sponsor_full_name,
            f.FATHER_MOBILE AS father_mobile,
            f.FATHER_EMAIL AS father_email,
            f.MOTHER_FULL_NAME AS mother_name,
            f.MOTHER_MOBILE AS mother_mobile,
            f.MOTHER_EMAIL AS mother_email,
            f.FAMILY_ADDRESS AS family_address,
            f.FAMILY_HOME_PHONE AS family_home_phone,
            f.FAM_CLASS_ID AS family_class_id,
            fc.CLASS_DESC AS family_class_name,
            f.IS_ACTIVE AS is_active,

            NVL(sc.student_count, 0) AS student_count

        FROM SCH_FAMILY_CARD f

        LEFT JOIN SCH_FAMILY_CLASS fc
            ON fc.CLASS_ID = f.FAM_CLASS_ID

        LEFT JOIN (
            SELECT
                FAMILY_ID,
                COUNT(*) AS student_count
            FROM SCH_STUDENT_CARD_YEAR
            WHERE STUDY_YEAR = :current_year
              AND STUDENT_STATUS = 1
            GROUP BY FAMILY_ID
        ) sc
            ON sc.FAMILY_ID = f.FAMILY_ID

        WHERE f.IS_ACTIVE = 1

        ORDER BY f.FAMILY_ID
    """

    return query_all(sql, {
        "current_year": Config.CURRENT_YEAR
    })


def get_family_by_id(family_id):
    sql = """
        SELECT
            f.FAMILY_ID AS family_id,

            TRIM(
                f.FATHER_NAME_1 || ' ' ||
                f.FATHER_NAME_2 || ' ' ||
                f.FATHER_NAME_3 || ' ' ||
                f.FATHER_SURNAME
            ) AS father_name,

            f.SPONSER_FULL_NAME AS sponsor_full_name,
            f.FATHER_MOBILE AS father_mobile,
            f.FATHER_EMAIL AS father_email,
            f.MOTHER_FULL_NAME AS mother_name,
            f.MOTHER_MOBILE AS mother_mobile,
            f.MOTHER_EMAIL AS mother_email,
            f.FAMILY_ADDRESS AS family_address,
            f.FAMILY_HOME_PHONE AS family_home_phone,
            f.FATHER_NATIONAL_NO AS father_national_no,
            f.MOTHER_NATIONAL_NO AS mother_national_no,
            f.FAM_CLASS_ID AS family_class_id,
            fc.CLASS_DESC AS family_class_name,
            f.IS_ACTIVE AS is_active,
            f.NOTES AS notes

        FROM SCH_FAMILY_CARD f

        LEFT JOIN SCH_FAMILY_CLASS fc
            ON fc.CLASS_ID = f.FAM_CLASS_ID

        WHERE f.FAMILY_ID = :family_id
    """

    return query_one(sql, {
        "family_id": family_id
    })


def get_students_by_family_id(family_id):
    sql = """
        SELECT
            y.STUDY_YEAR AS study_year,
            s.FAMILY_ID AS family_id,
            s.STUDENT_ID AS student_id,

            TRIM(
                s.STUDENT_NAME_1 || ' ' ||
                s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' ||
                s.STUDENT_SURNAME
            ) AS student_name,

            s.STUDENT_NATIONAL_NO AS student_national_no,
            s.STUDENT_GENDER AS student_gender,
            s.BIRTH_DATE AS birth_date,
            s.STUDENT_MOBILE AS student_mobile,
            s.EMAIL AS email,

            y.SCHOOL_ID AS school_id,
            school.SCHOOL_DESC AS school_name,

            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,

            y.BRANCH_ID AS branch_id,
            br.BRANCH_DESC AS branch_name,

            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,

            y.STUDENT_STATUS AS student_status,

            CASE y.STUDENT_STATUS
                WHEN 1 THEN 'ACTIVE'
                WHEN 2 THEN 'INACTIVE'
                ELSE 'UNKNOWN'
            END AS student_status_text,

            y.REGISTRATION_DATE AS registration_date,
            y.WITHDRAW_DATE AS withdraw_date

        FROM SCH_STUDENT_CARD s

        JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = s.FAMILY_ID
           AND y.STUDENT_ID = s.STUDENT_ID

        LEFT JOIN SCH_SCHOOL school
            ON school.SCHOOL_ID = y.SCHOOL_ID

        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID

        LEFT JOIN SCH_STUDY_BRANCHES br
            ON br.BRANCH_ID = y.BRANCH_ID

        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID

        WHERE s.FAMILY_ID = :family_id
          AND y.STUDY_YEAR = :current_year
          AND y.STUDENT_STATUS = 1

        ORDER BY
            cls.CLASS_ORDER,
            sec.SECTION_DESC,
            s.STUDENT_ID
    """

    return query_all(sql, {
        "family_id": family_id,
        "current_year": Config.CURRENT_YEAR
    })