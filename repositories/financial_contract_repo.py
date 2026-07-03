from datetime import date, datetime
from decimal import Decimal

from db import query_all, query_one


SOURCE_FIN_FAMILY = "SCH_FIN_FAMILY_CARD"
SOURCE_FIN_STUDENT = "SCH_FIN_STUDENT_CARD"
SOURCE_DUES = "SCH_FAMILY_DUE_ALLOC"
SOURCE_STUDENT_YEAR = "SCH_STUDENT_CARD_YEAR"


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return value


def _money(value):
    value = _json_value(value)
    return None if value is None else float(value)


def _safe_int(value):
    return None if value is None else int(value)


def _oracle_student_key(family_id, student_id):
    if family_id is None or student_id is None:
        return None
    return f"{int(family_id)}:{int(student_id)}"


def _identity_scope(student_id):
    return "student" if student_id is not None else "family"


def _direction(debit, credit):
    if debit is None or credit is None:
        return "unknown"
    effect = float(debit) - float(credit)
    if effect > 0:
        return "debit"
    if effect < 0:
        return "credit"
    return "zero"


def _missing_requirements(stable_key, family_id, amount, record_date, study_year):
    missing = []
    if not stable_key:
        missing.append("stable_key")
    if family_id is None:
        missing.append("identity_link")
    if amount is None:
        missing.append("amount")
    if record_date is None:
        missing.append("date")
    if not study_year:
        missing.append("study_year")
    return missing


def get_family_summary_contract(family_id, study_year):
    summary_sql = """
        SELECT
            FAMILY_ID AS family_id,
            STUDY_YEAR AS study_year,
            BEGIN_DR AS begin_dr,
            BEGIN_CR AS begin_cr,
            YEAR_DR AS year_dr,
            YEAR_CR AS year_cr
        FROM SCH_FIN_FAMILY_CARD
        WHERE FAMILY_ID = :family_id
          AND STUDY_YEAR = :study_year
    """
    summary_row = query_one(summary_sql, {
        "family_id": family_id,
        "study_year": study_year,
    })

    students_sql = """
        SELECT
            y.FAMILY_ID AS family_id,
            y.STUDENT_ID AS student_id,
            y.STUDY_YEAR AS study_year,
            y.CLASS_ID AS class_id,
            y.SECTION_ID AS section_id,
            y.STUDENT_STATUS AS student_status,
            NVL(SUM(fs.DR_AMOUNT), 0) AS debit_total,
            NVL(SUM(fs.CR_AMOUNT), 0) AS credit_total,
            COUNT(fs.SERIAL_ID) AS trans_count
        FROM SCH_STUDENT_CARD_YEAR y
        LEFT JOIN SCH_FIN_STUDENT_CARD fs
          ON fs.FAMILY_ID = y.FAMILY_ID
         AND fs.STUDENT_ID = y.STUDENT_ID
         AND fs.STUDY_YEAR = y.STUDY_YEAR
        WHERE y.FAMILY_ID = :family_id
          AND y.STUDY_YEAR = :study_year
        GROUP BY
            y.FAMILY_ID, y.STUDENT_ID, y.STUDY_YEAR,
            y.CLASS_ID, y.SECTION_ID, y.STUDENT_STATUS
        ORDER BY y.STUDENT_ID
    """
    student_rows = query_all(students_sql, {
        "family_id": family_id,
        "study_year": study_year,
    })

    students = []
    for row in student_rows:
        family_id_value = _safe_int(row.get("family_id"))
        student_id_value = _safe_int(row.get("student_id"))
        debit = _money(row.get("debit_total")) or 0.0
        credit = _money(row.get("credit_total")) or 0.0
        students.append({
            "oracle_family_id": family_id_value,
            "oracle_student_id": student_id_value,
            "oracle_student_key": _oracle_student_key(
                family_id_value, student_id_value
            ),
            "identity_scope": _identity_scope(student_id_value),
            "study_year": str(row["study_year"]),
            "class_id": _safe_int(row.get("class_id")),
            "section_id": _safe_int(row.get("section_id")),
            "student_status": _json_value(row.get("student_status")),
            "student_financial_available": int(row.get("trans_count") or 0) > 0,
            "balance": debit - credit,
            "due_total": None,
            "paid_total": credit,
        })

    summary = None
    if summary_row:
        begin_debit = _money(summary_row.get("begin_dr")) or 0.0
        begin_credit = _money(summary_row.get("begin_cr")) or 0.0
        year_debit = _money(summary_row.get("year_dr")) or 0.0
        year_credit = _money(summary_row.get("year_cr")) or 0.0
        total_debit = begin_debit + year_debit
        total_credit = begin_credit + year_credit
        summary = {
            "oracle_family_id": int(summary_row["family_id"]),
            "study_year": str(summary_row["study_year"]),
            "begin_debit": begin_debit,
            "begin_credit": begin_credit,
            "year_debit": year_debit,
            "year_credit": year_credit,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance": total_debit - total_credit,
            "balance_direction": _direction(total_debit, total_credit),
            "currency": "JOD",
            "import_readiness": "NOT_IMPORT_READY",
            "missing_requirements": ["as_of_date", "stable_snapshot_key"],
        }

    return {
        "status": "ok",
        "family_id": int(family_id),
        "study_year": study_year,
        "financial_available": summary is not None,
        "summary": summary,
        "students": students,
        "source": {
            "oracle_tables": [SOURCE_FIN_FAMILY, SOURCE_FIN_STUDENT, SOURCE_STUDENT_YEAR],
            "stable_keys": ["serial_id", "receipt_id"],
            "notes": [
                "Official family balance uses Oracle family-card debit minus credit.",
                "Family due allocations are not assigned to students by this contract.",
                "Balance snapshots require an as-of key before import.",
            ],
        },
    }


def get_family_transactions(family_id, study_year, limit, offset, student_id=None):
    student_filter = ""
    params = {
        "family_id": family_id,
        "study_year": study_year,
        "max_row": offset + limit,
        "offset": offset,
    }
    if student_id is not None:
        student_filter = " AND fs.STUDENT_ID = :student_id"
        params["student_id"] = student_id

    sql = f"""
        SELECT *
        FROM (
            SELECT tx_rows.*, ROWNUM rn
            FROM (
                SELECT
                    fs.SERIAL_ID AS serial_id,
                    fs.RECEIPT_ID AS receipt_id,
                    fs.FAMILY_ID AS family_id,
                    fs.STUDENT_ID AS student_id,
                    fs.STUDY_YEAR AS study_year,
                    fs.TRANS_DATE AS trans_date,
                    fs.TITLE_ID AS title_id,
                    fs.TITLE_TYPE AS title_type,
                    fs.TRANS_STATUS AS trans_status,
                    fs.DR_AMOUNT AS debit_amount,
                    fs.CR_AMOUNT AS credit_amount,
                    COUNT(*) OVER (
                        PARTITION BY fs.RECEIPT_ID
                    ) AS receipt_count,
                    COUNT(*) OVER (
                        PARTITION BY fs.SERIAL_ID
                    ) AS serial_count
                FROM SCH_FIN_STUDENT_CARD fs
                WHERE fs.FAMILY_ID = :family_id
                  AND fs.STUDY_YEAR = :study_year
                  {student_filter}
                ORDER BY
                    fs.TRANS_DATE, fs.RECEIPT_ID,
                    fs.SERIAL_ID, fs.STUDENT_ID
            ) tx_rows
            WHERE ROWNUM <= :max_row
        )
        WHERE rn > :offset
    """
    rows = query_all(sql, params)
    return [_transaction_contract(row) for row in rows]


def _transaction_contract(row):
    serial_id = _safe_int(row.get("serial_id"))
    receipt_id = _safe_int(row.get("receipt_id"))
    family_id = _safe_int(row.get("family_id"))
    student_id = _safe_int(row.get("student_id"))
    receipt_unique = receipt_id is not None and int(row.get("receipt_count") or 0) == 1
    stable_key = None
    if serial_id is not None and int(row.get("serial_count") or 0) == 1:
        stable_key = f"serial:{serial_id}"
    elif receipt_unique:
        stable_key = f"receipt:{receipt_id}"

    debit = _money(row.get("debit_amount")) or 0.0
    credit = _money(row.get("credit_amount")) or 0.0
    amount = debit if debit != 0 else credit
    trans_date = _json_value(row.get("trans_date"))
    missing = _missing_requirements(
        stable_key, family_id, amount, trans_date, row.get("study_year")
    )
    if credit > 0 and receipt_id is not None:
        trans_type = "receipt"
    elif credit > 0:
        trans_type = "payment"
    elif debit > 0:
        trans_type = "charge"
    else:
        trans_type = "unknown"

    return {
        "oracle_transaction_key": stable_key,
        "serial_id": serial_id,
        "receipt_id": receipt_id,
        "oracle_family_id": family_id,
        "oracle_student_id": student_id,
        "oracle_student_key": _oracle_student_key(family_id, student_id),
        "identity_scope": _identity_scope(student_id),
        "study_year": str(row["study_year"]),
        "transaction_date": trans_date,
        "transaction_type": trans_type,
        "title_id": _safe_int(row.get("title_id")),
        "title_type": _json_value(row.get("title_type")),
        "status": _json_value(row.get("trans_status")),
        "debit_amount": debit,
        "credit_amount": credit,
        "amount": amount,
        "balance_effect": _direction(debit, credit),
        "import_readiness": "IMPORT_READY" if not missing else "NOT_IMPORT_READY",
        "missing_requirements": missing,
        "source_table": SOURCE_FIN_STUDENT,
    }


def get_family_dues(family_id, study_year, limit, offset):
    sql = """
        SELECT *
        FROM (
            SELECT due_rows.*, ROWNUM rn
            FROM (
                SELECT
                    FAMILY_ID AS family_id,
                    STUDY_YEAR AS study_year,
                    DUE_DATE AS due_date,
                    PERCENT_VALUE AS pct_value,
                    DUE_AMOUNT AS due_amount,
                    PAID_AMOUNT AS paid_amount,
                    RECEIPT_PAID AS receipt_paid
                FROM SCH_FAMILY_DUE_ALLOC
                WHERE FAMILY_ID = :family_id
                  AND STUDY_YEAR = :study_year
                ORDER BY DUE_DATE, DUE_AMOUNT, PERCENT_VALUE, ROWID
            ) due_rows
            WHERE ROWNUM <= :max_row
        )
        WHERE rn > :offset
    """
    rows = query_all(sql, {
        "family_id": family_id,
        "study_year": study_year,
        "max_row": offset + limit,
        "offset": offset,
    })
    dues = []
    for row in rows:
        due_amount = _money(row.get("due_amount")) or 0.0
        paid_amount = (_money(row.get("paid_amount")) or 0.0) + (
            _money(row.get("receipt_paid")) or 0.0
        )
        remaining = due_amount - paid_amount
        if remaining <= 0:
            status = "paid"
        elif paid_amount > 0:
            status = "partial"
        else:
            status = "open"
        dues.append({
            "oracle_due_key": None,
            "serial_id": None,
            "oracle_family_id": int(row["family_id"]),
            "oracle_student_id": None,
            "oracle_student_key": None,
            "identity_scope": "family",
            "study_year": str(row["study_year"]),
            "due_date": _json_value(row.get("due_date")),
            "title_id": None,
            "title_type": None,
            "title_code": None,
            "due_amount": due_amount,
            "paid_amount": paid_amount,
            "remaining_amount": remaining,
            "status": status,
            "import_readiness": "NOT_IMPORT_READY",
            "missing_requirements": ["stable_key"],
            "source_table": SOURCE_DUES,
        })
    return dues


def get_family_receipts(family_id, study_year, limit, offset, student_id=None):
    student_filter = ""
    params = {
        "family_id": family_id,
        "study_year": study_year,
        "max_row": offset + limit,
        "offset": offset,
    }
    if student_id is not None:
        student_filter = " AND fs.STUDENT_ID = :student_id"
        params["student_id"] = student_id
    sql = f"""
        SELECT *
        FROM (
            SELECT rcpt_rows.*, ROWNUM rn
            FROM (
                SELECT
                    fs.RECEIPT_ID AS receipt_id,
                    MIN(fs.SERIAL_ID) AS serial_id,
                    fs.FAMILY_ID AS family_id,
                    CASE
                        WHEN COUNT(DISTINCT fs.STUDENT_ID) = 1
                        THEN MIN(fs.STUDENT_ID)
                        ELSE NULL
                    END AS student_id,
                    fs.STUDY_YEAR AS study_year,
                    MIN(fs.TRANS_DATE) AS receipt_date,
                    SUM(NVL(fs.CR_AMOUNT, 0)) AS receipt_amount,
                    MAX(fs.TRANS_STATUS) AS trans_status,
                    COUNT(*) AS line_count
                FROM SCH_FIN_STUDENT_CARD fs
                WHERE fs.FAMILY_ID = :family_id
                  AND fs.STUDY_YEAR = :study_year
                  AND fs.RECEIPT_ID IS NOT NULL
                  AND NVL(fs.CR_AMOUNT, 0) > 0
                  {student_filter}
                GROUP BY fs.RECEIPT_ID, fs.FAMILY_ID, fs.STUDY_YEAR
                ORDER BY MIN(fs.TRANS_DATE), fs.RECEIPT_ID
            ) rcpt_rows
            WHERE ROWNUM <= :max_row
        )
        WHERE rn > :offset
    """
    rows = query_all(sql, params)
    receipts = []
    for row in rows:
        receipt_id = _safe_int(row.get("receipt_id"))
        family = _safe_int(row.get("family_id"))
        student = _safe_int(row.get("student_id"))
        receipt_date = _json_value(row.get("receipt_date"))
        amount = _money(row.get("receipt_amount"))
        stable_key = f"receipt:{receipt_id}" if receipt_id is not None else None
        missing = _missing_requirements(
            stable_key, family, amount, receipt_date, row.get("study_year")
        )
        receipts.append({
            "oracle_receipt_key": stable_key,
            "receipt_id": receipt_id,
            "serial_id": _safe_int(row.get("serial_id")) if int(row.get("line_count") or 0) == 1 else None,
            "oracle_family_id": family,
            "oracle_student_id": student,
            "oracle_student_key": _oracle_student_key(family, student),
            "identity_scope": _identity_scope(student),
            "study_year": str(row["study_year"]),
            "receipt_date": receipt_date,
            "receipt_amount": amount,
            "payment_method": "unknown",
            "status": _json_value(row.get("trans_status")) or "unknown",
            "import_readiness": "IMPORT_READY" if not missing else "NOT_IMPORT_READY",
            "missing_requirements": missing,
            "source_table": SOURCE_FIN_STUDENT,
        })
    return receipts


def get_student_financial_summary(family_id, student_id, study_year):
    sql = """
        SELECT
            :family_id AS family_id,
            :student_id AS student_id,
            :study_year AS study_year,
            NVL(SUM(DR_AMOUNT), 0) AS debit_total,
            NVL(SUM(CR_AMOUNT), 0) AS credit_total,
            COUNT(*) AS trans_count,
            COUNT(DISTINCT RECEIPT_ID) AS receipt_count
        FROM SCH_FIN_STUDENT_CARD
        WHERE FAMILY_ID = :family_id
          AND STUDENT_ID = :student_id
          AND STUDY_YEAR = :study_year
    """
    row = query_one(sql, {
        "family_id": family_id,
        "student_id": student_id,
        "study_year": study_year,
    }) or {}
    debit = _money(row.get("debit_total")) or 0.0
    credit = _money(row.get("credit_total")) or 0.0
    transactions = int(row.get("trans_count") or 0)
    receipts = int(row.get("receipt_count") or 0)
    family_id_value = _safe_int(family_id)
    student_id_value = _safe_int(student_id)
    return {
        "status": "ok",
        "oracle_student_key": _oracle_student_key(
            family_id_value, student_id_value
        ),
        "oracle_family_id": family_id_value,
        "oracle_student_id": student_id_value,
        "identity_scope": _identity_scope(student_id_value),
        "study_year": study_year,
        "summary": {
            "due_total": None,
            "paid_total": credit,
            "debit_total": debit,
            "credit_total": credit,
            "balance": debit - credit,
            "balance_direction": _direction(debit, credit),
        },
        "counts": {
            "transactions": transactions,
            "dues": 0,
            "receipts": receipts,
            "payments": 0,
        },
        "financial_available": transactions > 0,
        "source": {
            "oracle_tables": [SOURCE_FIN_STUDENT],
            "notes": [
                "Family due allocations cannot be assigned to a student from proven columns.",
                "Oracle does not expose a distinct payment entity in this contract.",
            ],
        },
    }


def get_financial_diagnostics(study_year):
    counts_sql = """
        SELECT
            COUNT(DISTINCT FAMILY_ID) AS family_count,
            COUNT(DISTINCT FAMILY_ID || ':' || STUDENT_ID) AS student_count,
            COUNT(*) AS trans_rows,
            SUM(CASE WHEN RECEIPT_ID IS NOT NULL THEN 1 ELSE 0 END) AS receipt_rows,
            SUM(CASE WHEN FAMILY_ID IS NULL THEN 1 ELSE 0 END) AS missing_family,
            SUM(CASE WHEN STUDENT_ID IS NULL THEN 1 ELSE 0 END) AS missing_student,
            SUM(CASE
                WHEN SERIAL_ID IS NULL AND RECEIPT_ID IS NULL THEN 1
                ELSE 0
            END) AS missing_key
        FROM SCH_FIN_STUDENT_CARD
        WHERE STUDY_YEAR = :study_year
    """
    counts = query_one(counts_sql, {"study_year": study_year}) or {}
    due_sql = """
        SELECT COUNT(*) AS due_rows
        FROM SCH_FAMILY_DUE_ALLOC
        WHERE STUDY_YEAR = :study_year
    """
    dues = query_one(due_sql, {"study_year": study_year}) or {}
    serial_sql = """
        SELECT COUNT(*) AS duplicate_count
        FROM (
            SELECT SERIAL_ID
            FROM SCH_FIN_STUDENT_CARD
            WHERE STUDY_YEAR = :study_year
              AND SERIAL_ID IS NOT NULL
            GROUP BY SERIAL_ID
            HAVING COUNT(*) > 1
        )
    """
    receipt_sql = """
        SELECT COUNT(*) AS duplicate_count
        FROM (
            SELECT RECEIPT_ID
            FROM SCH_FIN_STUDENT_CARD
            WHERE STUDY_YEAR = :study_year
              AND RECEIPT_ID IS NOT NULL
            GROUP BY RECEIPT_ID
            HAVING COUNT(*) > 1
        )
    """
    reused_sql = """
        SELECT COUNT(*) AS reused_count
        FROM (
            SELECT STUDENT_ID
            FROM SCH_FIN_STUDENT_CARD
            WHERE STUDY_YEAR = :study_year
              AND STUDENT_ID IS NOT NULL
            GROUP BY STUDENT_ID
            HAVING COUNT(DISTINCT FAMILY_ID) > 1
        )
    """
    duplicate_serials = query_one(serial_sql, {"study_year": study_year}) or {}
    duplicate_receipts = query_one(receipt_sql, {"study_year": study_year}) or {}
    reused_students = query_one(reused_sql, {"study_year": study_year}) or {}
    return {
        "families_with_financial_rows": int(counts.get("family_count") or 0),
        "students_with_financial_rows": int(counts.get("student_count") or 0),
        "transaction_rows": int(counts.get("trans_rows") or 0),
        "due_rows": int(dues.get("due_rows") or 0),
        "receipt_rows": int(counts.get("receipt_rows") or 0),
        "rows_missing_family_id": int(counts.get("missing_family") or 0),
        "rows_missing_student_id": int(counts.get("missing_student") or 0),
        "rows_missing_stable_key": int(counts.get("missing_key") or 0),
        "duplicate_serial_ids": int(duplicate_serials.get("duplicate_count") or 0),
        "duplicate_receipt_ids": int(duplicate_receipts.get("duplicate_count") or 0),
        "student_id_values_reused_across_families": int(reused_students.get("reused_count") or 0),
    }
