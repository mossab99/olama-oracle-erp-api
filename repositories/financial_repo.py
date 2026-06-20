from datetime import date, datetime
from decimal import Decimal

from db import query_all, query_one


STUDENT_TRANSACTION_TABLES = (
    "SCH_FIN_STUDENT_CARD_INC",
    "SCH_FIN_STUDENT_CARD_INQ",
)


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


def _get_table_columns(table_name):
    rows = query_all("""
        SELECT column_name
        FROM user_tab_columns
        WHERE table_name = :table_name
    """, {
        "table_name": table_name
    })

    return {
        row["column_name"].upper()
        for row in rows
    }


def get_family_financial_summary(family_id, study_year):
    sql = """
        SELECT
            FAMILY_ID AS family_id,
            STUDY_YEAR AS study_year,
            BEGIN_CR AS begin_credit,
            YEAR_DR AS year_debit,
            YEAR_CR AS year_credit,
            BALANCE AS balance
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
            fs.FAMILY_ID AS family_id,
            fs.STUDENT_ID AS student_id,
            fs.STUDENT_ID_DESC AS student_name,
            y.STUDY_YEAR AS study_year,
            y.SCHOOL_ID AS school_id,
            school.SCHOOL_DESC AS school_name,
            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,
            y.STUDENT_STATUS AS student_status
        FROM SCH_FIN_STUDENT_CARD fs
        LEFT JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = fs.FAMILY_ID
           AND y.STUDENT_ID = fs.STUDENT_ID
           AND y.STUDY_YEAR = :study_year
        LEFT JOIN SCH_SCHOOL school
            ON school.SCHOOL_ID = y.SCHOOL_ID
        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID
        WHERE fs.FAMILY_ID = :family_id
          AND fs.STUDY_YEAR = :study_year
        ORDER BY
            cls.CLASS_ORDER,
            sec.SECTION_DESC,
            fs.STUDENT_ID
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
            BALANCE AS balance
        FROM SCH_FAMILY_DUE_ALLOC
        WHERE FAMILY_ID = :family_id
          AND STUDY_YEAR = :study_year
        ORDER BY DUE_DATE
    """

    return _json_safe_rows(query_all(sql, {
        "family_id": family_id,
        "study_year": study_year
    }))


def _find_student_transaction_table():
    required_columns = {
        "FAMILY_ID",
        "STUDY_YEAR",
        "STUDENT_ID",
        "STUDENT_ID_DESC",
        "TITLE_ID_DESC",
        "TRANS_DATE",
        "RECEIPT_ID",
        "DR_AMOUNT",
        "CR_AMOUNT",
    }

    for table_name in STUDENT_TRANSACTION_TABLES:
        columns = _get_table_columns(table_name)

        if required_columns.issubset(columns):
            return table_name

    return None


def get_family_student_transactions(family_id, study_year):
    table_name = _find_student_transaction_table()

    if not table_name:
        return []

    sql = f"""
        SELECT
            STUDENT_ID AS student_id,
            STUDENT_ID_DESC AS student_name,
            TITLE_ID_DESC AS title,
            TRANS_DATE AS trans_date,
            RECEIPT_ID AS receipt_id,
            DR_AMOUNT AS debit_amount,
            CR_AMOUNT AS credit_amount
        FROM {table_name}
        WHERE FAMILY_ID = :family_id
          AND STUDY_YEAR = :study_year
        ORDER BY
            TRANS_DATE,
            RECEIPT_ID,
            STUDENT_ID
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
