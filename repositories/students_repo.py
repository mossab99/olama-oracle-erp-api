from db import query_all, query_one
from config import Config


def get_all_students():
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

            f.SPONSER_FULL_NAME AS sponsor_full_name,
            f.FATHER_MOBILE AS father_mobile,
            f.MOTHER_MOBILE AS mother_mobile,

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

        JOIN SCH_FAMILY_CARD f
            ON f.FAMILY_ID = s.FAMILY_ID

        LEFT JOIN SCH_SCHOOL school
            ON school.SCHOOL_ID = y.SCHOOL_ID

        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID

        LEFT JOIN SCH_STUDY_BRANCHES br
            ON br.BRANCH_ID = y.BRANCH_ID

        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID

        WHERE y.STUDY_YEAR = :current_year
          AND y.STUDENT_STATUS = 1

        ORDER BY
            cls.CLASS_ORDER,
            sec.SECTION_DESC,
            student_name
    """

    return query_all(sql, {
        "current_year": Config.CURRENT_YEAR
    })


def get_student_by_family_and_student_id(family_id, student_id):
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
            s.MOTHER_NAME AS student_mother_name,
            s.NOTES AS notes,

            f.SPONSER_FULL_NAME AS sponsor_full_name,
            f.FATHER_MOBILE AS father_mobile,
            f.MOTHER_MOBILE AS mother_mobile,
            f.FAMILY_ADDRESS AS family_address,

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

        JOIN SCH_FAMILY_CARD f
            ON f.FAMILY_ID = s.FAMILY_ID

        LEFT JOIN SCH_SCHOOL school
            ON school.SCHOOL_ID = y.SCHOOL_ID

        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID

        LEFT JOIN SCH_STUDY_BRANCHES br
            ON br.BRANCH_ID = y.BRANCH_ID

        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID

        WHERE s.FAMILY_ID = :family_id
          AND s.STUDENT_ID = :student_id
          AND y.STUDY_YEAR = :current_year
    """

    return query_one(sql, {
        "family_id": family_id,
        "student_id": student_id,
        "current_year": Config.CURRENT_YEAR
    })


def search_students(search_text):
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
            s.STUDENT_MOBILE AS student_mobile,

            f.SPONSER_FULL_NAME AS sponsor_full_name,
            f.FATHER_MOBILE AS father_mobile,
            f.MOTHER_MOBILE AS mother_mobile,

            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,

            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,

            y.STUDENT_STATUS AS student_status

        FROM SCH_STUDENT_CARD s

        JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = s.FAMILY_ID
           AND y.STUDENT_ID = s.STUDENT_ID

        JOIN SCH_FAMILY_CARD f
            ON f.FAMILY_ID = s.FAMILY_ID

        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID

        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID

        WHERE y.STUDY_YEAR = :current_year
          AND y.STUDENT_STATUS = 1
          AND (
                LOWER(
                    s.STUDENT_NAME_1 || ' ' ||
                    s.STUDENT_NAME_2 || ' ' ||
                    s.STUDENT_NAME_3 || ' ' ||
                    s.STUDENT_SURNAME
                ) LIKE LOWER(:search_text)

                OR LOWER(NVL(s.STUDENT_NATIONAL_NO, '')) LIKE LOWER(:search_text)

                OR TO_CHAR(s.FAMILY_ID) LIKE :search_text_plain
          )

        ORDER BY
            cls.CLASS_ORDER,
            sec.SECTION_DESC,
            student_name
    """

    return query_all(sql, {
        "current_year": Config.CURRENT_YEAR,
        "search_text": f"%{search_text}%",
        "search_text_plain": f"%{search_text}%"
    })