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


def get_family_financial_summary(family_id, study_year):
    sql = """
        SELECT
            FAMILY_ID AS family_id,
            STUDY_YEAR AS study_year,
            BEGIN_DR AS begin_debit,
            BEGIN_CR AS begin_credit,
            YEAR_DR AS year_debit,
            YEAR_CR AS year_credit,
            (
                NVL(BEGIN_DR, 0)
                - NVL(BEGIN_CR, 0)
                + NVL(YEAR_DR, 0)
                - NVL(YEAR_CR, 0)
            ) AS balance
        FROM SCH_FIN_FAMILY_CARD
        WHERE FAMILY_ID = :family_id
          AND STUDY_YEAR = :study_year
    """

    return _json_safe_row(query_one(sql, {
        "family_id": family_id,
        "study_year": study_year
    }))


def get_family_financial_students(family_id, study_year):
    sql = """
        SELECT
            y.FAMILY_ID AS family_id,
            y.STUDENT_ID AS student_id,
            TRIM(
                s.STUDENT_NAME_1 || ' ' ||
                s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' ||
                s.STUDENT_SURNAME
            ) AS student_name,
            y.STUDY_YEAR AS study_year,
            y.SCHOOL_ID AS school_id,
            school.SCHOOL_DESC AS school_name,
            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,
            y.STUDENT_STATUS AS student_status
        FROM SCH_STUDENT_CARD_YEAR y

        LEFT JOIN SCH_STUDENT_CARD s
            ON s.FAMILY_ID = y.FAMILY_ID
           AND s.STUDENT_ID = y.STUDENT_ID

        LEFT JOIN SCH_SCHOOL school
            ON school.SCHOOL_ID = y.SCHOOL_ID

        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID

        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID

        WHERE y.FAMILY_ID = :family_id
          AND y.STUDY_YEAR = :study_year

        ORDER BY
            cls.CLASS_ORDER,
            sec.SECTION_DESC,
            y.STUDENT_ID
    """

    return _json_safe_rows(query_all(sql, {
        "family_id": family_id,
        "study_year": study_year
    }))


def get_family_due_allocations(family_id, study_year):
    sql = """
        SELECT
            DUE_DATE AS due_date,
            PERCENT_VALUE AS percent_value,
            DUE_AMOUNT AS due_amount,
            PAID_AMOUNT AS paid_amount,
            RECEIPT_PAID AS receipt_paid,
            (
                NVL(DUE_AMOUNT, 0)
                - NVL(PAID_AMOUNT, 0)
                - NVL(RECEIPT_PAID, 0)
            ) AS balance
        FROM SCH_FAMILY_DUE_ALLOC
        WHERE FAMILY_ID = :family_id
          AND STUDY_YEAR = :study_year
        ORDER BY DUE_DATE
    """

    return _json_safe_rows(query_all(sql, {
        "family_id": family_id,
        "study_year": study_year
    }))


def get_family_student_transactions(family_id, study_year):
    sql = """
        SELECT
            fs.SERIAL_ID AS serial_id,
            fs.FAMILY_ID AS family_id,
            fs.STUDENT_ID AS student_id,
            TRIM(
                s.STUDENT_NAME_1 || ' ' ||
                s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' ||
                s.STUDENT_SURNAME
            ) AS student_name,
            fs.TITLE_ID AS title_id,
            TO_CHAR(fs.TITLE_ID) AS title,
            fs.TRANS_DATE AS trans_date,
            fs.RECEIPT_ID AS receipt_id,
            fs.DR_AMOUNT AS debit_amount,
            fs.CR_AMOUNT AS credit_amount,
            fs.NOTES AS notes,
            fs.TRANS_STATUS AS trans_status,
            fs.TITLE_TYPE AS title_type,
            fs.BEGIN_YEAR AS begin_year
        FROM SCH_FIN_STUDENT_CARD fs

        LEFT JOIN SCH_STUDENT_CARD s
            ON s.FAMILY_ID = fs.FAMILY_ID
           AND s.STUDENT_ID = fs.STUDENT_ID

        WHERE fs.FAMILY_ID = :family_id
          AND fs.STUDY_YEAR = :study_year

        ORDER BY
            fs.TRANS_DATE,
            fs.RECEIPT_ID,
            fs.SERIAL_ID,
            fs.STUDENT_ID
    """

    return _json_safe_rows(query_all(sql, {
        "family_id": family_id,
        "study_year": study_year
    }))


def get_family_financial_card(family_id, study_year):
    return {
        "family_summary": get_family_financial_summary(family_id, study_year),
        "students": get_family_financial_students(family_id, study_year),
        "due_allocations": get_family_due_allocations(family_id, study_year),
        "student_transactions": get_family_student_transactions(family_id, study_year),
    }
