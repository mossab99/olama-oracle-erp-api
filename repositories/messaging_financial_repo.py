from datetime import date, datetime
from decimal import Decimal
from db import query_all, query_one
from config import Config
from repositories.financial_repo import _json_safe, _json_safe_row, _json_safe_rows


def _calculate_monthly_due(due_allocations):
    """
    Calculate monthly_due and monthly_due_source from family due allocations.
    Returns (monthly_due, monthly_due_source)
    """
    if not due_allocations:
        return None, "unavailable"

    today = datetime.now().date()
    unpaid_items = []

    for item in due_allocations:
        due_amt = float(item.get("due_amount") or 0)
        paid_amt = float(item.get("paid_amount") or 0)
        rcpt_amt = float(item.get("receipt_paid") or 0)
        
        # Calculate remaining due with safety clamping (never negative)
        rem = max(due_amt - paid_amt - rcpt_amt, 0.0)

        if rem > 0.001:
            # Parse due_date
            d_val = item.get("due_date")
            d_obj = None
            if isinstance(d_val, (date, datetime)):
                d_obj = d_val if isinstance(d_val, date) else d_val.date()
            elif isinstance(d_val, str):
                try:
                    d_obj = datetime.fromisoformat(d_val[:10]).date()
                except Exception:
                    pass

            unpaid_items.append({"remaining": rem, "due_date": d_obj})

    if not unpaid_items:
        return 0.0, "current_month_due"

    # Filter for current month/year
    current_month_unpaid = [
        it for it in unpaid_items
        if it["due_date"] and it["due_date"].year == today.year and it["due_date"].month == today.month
    ]

    if current_month_unpaid:
        total_curr = sum(it["remaining"] for it in current_month_unpaid)
        return max(round(total_curr, 3), 0.0), "current_month_due"

    # Fallback to next upcoming unpaid installment
    # Sort unpaid_items by due_date
    sorted_unpaid = sorted(
        unpaid_items,
        key=lambda x: x["due_date"] or date.max
    )
    first_rem = sorted_unpaid[0]["remaining"]
    return max(round(first_rem, 3), 0.0), "next_unpaid_due"


def get_last_payment(family_id, study_year):
    """
    Query the most recent credit transaction (payment receipt) for a family.
    """
    sql = """
        SELECT
            TRANS_DATE AS trans_date,
            RECEIPT_ID AS receipt_id,
            CR_AMOUNT AS credit_amount
        FROM SCH_FIN_STUDENT_CARD
        WHERE FAMILY_ID = :family_id
          AND STUDY_YEAR = :study_year
          AND NVL(CR_AMOUNT, 0) > 0
        ORDER BY TRANS_DATE DESC, RECEIPT_ID DESC
    """
    rows = query_all(sql, {"family_id": family_id, "study_year": study_year})
    if not rows:
        return None

    row = rows[0]
    dt_val = _json_safe(row.get("trans_date"))
    if dt_val and len(str(dt_val)) >= 10:
        dt_val = str(dt_val)[:10]

    return {
        "date": dt_val,
        "amount": float(row.get("credit_amount") or 0),
        "receipt_no": str(row.get("receipt_id") or "") if row.get("receipt_id") else None
    }


def get_bulk_messaging_recipients(study_year, min_balance=None, class_id=None, section_id=None, class_name=None, section_name=None, family_id=None, limit=50, offset=0):
    """
    Bulk query recipients with financial summary.
    """
    params = {"study_year": study_year}
    
    where_clauses = ["f.IS_ACTIVE = 1"]
    if family_id:
        where_clauses.append("f.FAMILY_ID = :family_id")
        params["family_id"] = int(family_id)
    if class_id:
        where_clauses.append("y.CLASS_ID = :class_id")
        params["class_id"] = int(class_id)
    if section_id:
        where_clauses.append("y.SECTION_ID = :section_id")
        params["section_id"] = int(section_id)
    if class_name:
        where_clauses.append("TRIM(cls.CLASS_DESC) = :class_name")
        params["class_name"] = class_name.strip()
    if section_name:
        where_clauses.append("TRIM(sec.SECTION_DESC) = :section_name")
        params["section_name"] = section_name.strip()

    where_sql = " AND ".join(where_clauses)

    # OFFICIAL BALANCE FORMULA SOURCE OF TRUTH
    # The official aggregate family balance is queried from SCH_FIN_FAMILY_CARD:
    # calc_balance = NVL(BEGIN_DR, 0) - NVL(BEGIN_CR, 0) + NVL(YEAR_DR, 0) - NVL(YEAR_CR, 0)
    # This matches the family aggregate financial card screen in Oracle ERP.
    # Note: The alternative formula (total_due_allocated - NVL(total_fin_payments, 0)) is
    # a conceptual due reconciliation. Due allocation tables (SCH_FAMILY_DUE_ALLOC) are
    # used specifically for calculating monthly_due and due_items, NOT for the main family balance
    # to avoid double-counting or discrepancies with the official ERP ledger card.
    sql_families = f"""
        SELECT DISTINCT
            f.FAMILY_ID AS family_id,
            f.SPONSER_FULL_NAME AS sponsor_name,
            TRIM(
                f.FATHER_NAME_1 || ' ' ||
                f.FATHER_NAME_2 || ' ' ||
                f.FATHER_NAME_3 || ' ' ||
                f.FATHER_SURNAME
            ) AS father_name,
            f.FATHER_MOBILE AS father_mobile,
            f.MOTHER_FULL_NAME AS mother_name,
            f.MOTHER_MOBILE AS mother_mobile,
            fin.BEGIN_DR AS begin_debit,
            fin.BEGIN_CR AS begin_credit,
            fin.YEAR_DR AS year_debit,
            fin.YEAR_CR AS year_credit,
            (
                NVL(fin.BEGIN_DR, 0)
                - NVL(fin.BEGIN_CR, 0)
                + NVL(fin.YEAR_DR, 0)
                - NVL(fin.YEAR_CR, 0)
            ) AS calc_balance,
            CASE WHEN fin.FAMILY_ID IS NOT NULL THEN 1 ELSE 0 END AS has_fin_card
        FROM SCH_FAMILY_CARD f
        JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = f.FAMILY_ID
           AND y.STUDY_YEAR = :study_year
           AND y.STUDENT_STATUS = 1
        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID
        LEFT JOIN SCH_FIN_FAMILY_CARD fin
            ON fin.FAMILY_ID = f.FAMILY_ID
           AND fin.STUDY_YEAR = :study_year
        WHERE {where_sql}
        ORDER BY f.FAMILY_ID
    """

    all_families = query_all(sql_families, params)

    # Filter by min_balance if requested
    if min_balance is not None:
        min_b = float(min_balance)
        filtered = []
        for fam in all_families:
            if fam.get("has_fin_card") == 1:
                bal = float(fam.get("calc_balance") or 0)
                if bal >= min_b - 0.001:
                    filtered.append(fam)
        all_families = filtered

    total_count = len(all_families)
    sliced_families = all_families[offset : offset + limit]

    if not sliced_families:
        return total_count, []

    fam_ids = [int(f["family_id"]) for f in sliced_families]
    in_placeholders = ", ".join(f":f_{i}" for i in range(len(fam_ids)))
    in_params = {f"f_{i}": fid for i, fid in enumerate(fam_ids)}
    in_params["study_year"] = study_year

    # Query students for sliced families
    sql_students = f"""
        SELECT
            y.FAMILY_ID AS family_id,
            s.STUDENT_ID AS student_id,
            TRIM(
                s.STUDENT_NAME_1 || ' ' ||
                s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' ||
                s.STUDENT_SURNAME
            ) AS student_name,
            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name
        FROM SCH_STUDENT_CARD s
        JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = s.FAMILY_ID
           AND y.STUDENT_ID = s.STUDENT_ID
           AND y.STUDY_YEAR = :study_year
           AND y.STUDENT_STATUS = 1
        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID
        WHERE s.FAMILY_ID IN ({in_placeholders})
        ORDER BY cls.CLASS_ORDER, sec.SECTION_DESC, s.STUDENT_ID
    """
    student_rows = query_all(sql_students, in_params)

    students_by_fam = {}
    for st in student_rows:
        fid = int(st["family_id"])
        if fid not in students_by_fam:
            students_by_fam[fid] = []
        students_by_fam[fid].append({
            "student_id": int(st["student_id"]),
            "student_name": _json_safe(st["student_name"]),
            "class_id": st.get("class_id"),
            "class_name": _json_safe(st.get("class_name")),
            "section_id": st.get("section_id"),
            "section_name": _json_safe(st.get("section_name"))
        })

    # Query due allocations for sliced families
    sql_dues = f"""
        SELECT
            FAMILY_ID AS family_id,
            DUE_DATE AS due_date,
            DUE_AMOUNT AS due_amount,
            PAID_AMOUNT AS paid_amount,
            RECEIPT_PAID AS receipt_paid
        FROM SCH_FAMILY_DUE_ALLOC
        WHERE FAMILY_ID IN ({in_placeholders})
          AND STUDY_YEAR = :study_year
        ORDER BY DUE_DATE
    """
    due_rows = query_all(sql_dues, in_params)
    dues_by_fam = {}
    for dr in due_rows:
        fid = int(dr["family_id"])
        if fid not in dues_by_fam:
            dues_by_fam[fid] = []
        dues_by_fam[fid].append(dr)

    # Assemble result
    recipients = []
    for fam in sliced_families:
        fid = int(fam["family_id"])
        has_fin = fam.get("has_fin_card") == 1
        bal_val = float(fam.get("calc_balance") or 0) if has_fin else None
        
        m_due, m_src = _calculate_monthly_due(dues_by_fam.get(fid, [])) if has_fin else (None, "unavailable")

        recipients.append({
            "family_id": fid,
            "oracle_family_id": str(fid),
            "sponsor_name": _json_safe(fam.get("sponsor_name") or ""),
            "father_name": _json_safe(fam.get("father_name") or ""),
            "father_mobile": _json_safe(fam.get("father_mobile") or ""),
            "mother_name": _json_safe(fam.get("mother_name") or ""),
            "mother_mobile": _json_safe(fam.get("mother_mobile") or ""),
            "students": students_by_fam.get(fid, []),
            "balance": round(bal_val, 3) if bal_val is not None else None,
            "monthly_due": m_due,
            "monthly_due_source": m_src,
            "currency": "JOD",
            "financial_available": has_fin
        })

    return total_count, recipients


def get_single_family_financial_summary(family_id, study_year):
    """
    Lightweight financial lookup for a single family.
    """
    # OFFICIAL BALANCE FORMULA SOURCE OF TRUTH
    # The official aggregate family balance is queried from SCH_FIN_FAMILY_CARD:
    # calc_balance = NVL(BEGIN_DR, 0) - NVL(BEGIN_CR, 0) + NVL(YEAR_DR, 0) - NVL(YEAR_CR, 0)
    # This matches the family aggregate financial card screen in Oracle ERP.
    # Note: The alternative formula (total_due_allocated - NVL(total_fin_payments, 0)) is
    # a conceptual due reconciliation. Due allocation tables (SCH_FAMILY_DUE_ALLOC) are
    # used specifically for calculating monthly_due and due_items, NOT for the main family balance
    # to avoid double-counting or discrepancies with the official ERP ledger card.
    sql = """
        SELECT
            BEGIN_DR AS begin_debit,
            BEGIN_CR AS begin_credit,
            YEAR_DR AS year_debit,
            YEAR_CR AS year_credit,
            (
                NVL(BEGIN_DR, 0)
                - NVL(BEGIN_CR, 0)
                + NVL(YEAR_DR, 0)
                - NVL(YEAR_CR, 0)
            ) AS calc_balance
        FROM SCH_FIN_FAMILY_CARD
        WHERE FAMILY_ID = :family_id
          AND STUDY_YEAR = :study_year
    """
    row = query_one(sql, {"family_id": family_id, "study_year": study_year})
    if not row:
        return {
            "family_id": family_id,
            "oracle_family_id": str(family_id),
            "study_year": study_year,
            "balance": None,
            "monthly_due": None,
            "monthly_due_source": "unavailable",
            "last_payment_date": None,
            "last_payment_amount": None,
            "currency": "JOD",
            "financial_available": False
        }

    bal = float(row.get("calc_balance") or 0)
    
    # Due allocations
    sql_dues = """
        SELECT DUE_DATE AS due_date, DUE_AMOUNT AS due_amount, PAID_AMOUNT AS paid_amount, RECEIPT_PAID AS receipt_paid
        FROM SCH_FAMILY_DUE_ALLOC
        WHERE FAMILY_ID = :family_id AND STUDY_YEAR = :study_year
    """
    dues = query_all(sql_dues, {"family_id": family_id, "study_year": study_year})
    m_due, m_src = _calculate_monthly_due(dues)

    last_p = get_last_payment(family_id, study_year)

    return {
        "family_id": family_id,
        "oracle_family_id": str(family_id),
        "study_year": study_year,
        "balance": round(bal, 3),
        "monthly_due": m_due,
        "monthly_due_source": m_src,
        "last_payment_date": last_p["date"] if last_p else None,
        "last_payment_amount": last_p["amount"] if last_p else None,
        "currency": "JOD",
        "financial_available": True
    }


def get_students_by_family_id_and_year(family_id, study_year):
    """
    Query students for a family in a specific study year.
    Ensures that payment report students respect the requested study_year,
    falling back to an empty list if none are found.
    """
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
            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name
        FROM SCH_STUDENT_CARD s
        JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = s.FAMILY_ID
           AND y.STUDENT_ID = s.STUDENT_ID
        LEFT JOIN SCH_CLASSES cls
            ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec
            ON sec.SECTION_ID = y.SECTION_ID
        WHERE s.FAMILY_ID = :family_id
          AND y.STUDY_YEAR = :study_year
          AND y.STUDENT_STATUS = 1
        ORDER BY
            cls.CLASS_ORDER,
            sec.SECTION_DESC,
            s.STUDENT_ID
    """
    return query_all(sql, {
        "family_id": family_id,
        "study_year": study_year
    })


def get_family_payment_report_payload(family_id, study_year):
    """
    Full data payload for the public parent payment report page.
    """
    from repositories.families_repo import get_family_by_id

    fam = get_family_by_id(family_id)
    if not fam:
        return None

    students_raw = get_students_by_family_id_and_year(family_id, study_year)
    students = []
    for st in students_raw:
        students.append({
            "student_id": int(st["student_id"]),
            "student_name": _json_safe(st.get("student_name")),
            "class_id": st.get("class_id"),
            "class_name": _json_safe(st.get("class_name")),
            "section_id": st.get("section_id"),
            "section_name": _json_safe(st.get("section_name"))
        })

    # OFFICIAL BALANCE FORMULA SOURCE OF TRUTH
    # The official aggregate family balance is queried from SCH_FIN_FAMILY_CARD:
    # calc_balance = NVL(BEGIN_DR, 0) - NVL(BEGIN_CR, 0) + NVL(YEAR_DR, 0) - NVL(YEAR_CR, 0)
    # This matches the family aggregate financial card screen in Oracle ERP.
    # Note: The alternative formula (total_due_allocated - NVL(total_fin_payments, 0)) is
    # a conceptual due reconciliation. Due allocation tables (SCH_FAMILY_DUE_ALLOC) are
    # used specifically for calculating monthly_due and due_items, NOT for the main family balance
    # to avoid double-counting or discrepancies with the official ERP ledger card.
    sql_fin = """
        SELECT
            BEGIN_DR AS begin_debit,
            BEGIN_CR AS begin_credit,
            YEAR_DR AS year_debit,
            YEAR_CR AS year_credit,
            (
                NVL(BEGIN_DR, 0)
                - NVL(BEGIN_CR, 0)
                + NVL(YEAR_DR, 0)
                - NVL(YEAR_CR, 0)
            ) AS calc_balance
        FROM SCH_FIN_FAMILY_CARD
        WHERE FAMILY_ID = :family_id
          AND STUDY_YEAR = :study_year
    """
    fin_row = query_one(sql_fin, {"family_id": family_id, "study_year": study_year})

    if not fin_row:
        return {
            "family_id": family_id,
            "oracle_family_id": str(family_id),
            "study_year": study_year,
            "sponsor_name": _json_safe(fam.get("sponsor_full_name") or ""),
            "father_name": _json_safe(fam.get("father_name") or ""),
            "father_mobile": _json_safe(fam.get("father_mobile") or ""),
            "mother_name": _json_safe(fam.get("mother_name") or ""),
            "mother_mobile": _json_safe(fam.get("mother_mobile") or ""),
            "students": students,
            "financial": {
                "financial_available": False,
                "message": "Financial data is not available for this family/study_year"
            }
        }

    bal = float(fin_row.get("calc_balance") or 0)

    # Due allocations
    sql_dues = """
        SELECT DUE_DATE AS due_date, DUE_AMOUNT AS due_amount, PAID_AMOUNT AS paid_amount, RECEIPT_PAID AS receipt_paid
        FROM SCH_FAMILY_DUE_ALLOC
        WHERE FAMILY_ID = :family_id AND STUDY_YEAR = :study_year
        ORDER BY DUE_DATE
    """
    dues_raw = query_all(sql_dues, {"family_id": family_id, "study_year": study_year})
    m_due, m_src = _calculate_monthly_due(dues_raw)

    due_items = []
    for d in dues_raw:
        due_amt = float(d.get("due_amount") or 0)
        paid_amt = float(d.get("paid_amount") or 0)
        rcpt_amt = float(d.get("receipt_paid") or 0)
        total_p = paid_amt + rcpt_amt
        rem = max(0.0, due_amt - total_p)
        status = "paid" if rem <= 0.001 else ("partial" if total_p > 0.001 else "unpaid")

        dt_str = _json_safe(d.get("due_date"))
        if dt_str and len(str(dt_str)) >= 10:
            dt_str = str(dt_str)[:10]

        due_items.append({
            "title": "القسط المدرسي",
            "due_date": dt_str,
            "amount": round(due_amt, 3),
            "paid": round(total_p, 3),
            "remaining": round(rem, 3),
            "status": status
        })

    last_p = get_last_payment(family_id, study_year)

    return {
        "family_id": family_id,
        "oracle_family_id": str(family_id),
        "study_year": study_year,
        "sponsor_name": _json_safe(fam.get("sponsor_full_name") or ""),
        "father_name": _json_safe(fam.get("father_name") or ""),
        "father_mobile": _json_safe(fam.get("father_mobile") or ""),
        "mother_name": _json_safe(fam.get("mother_name") or ""),
        "mother_mobile": _json_safe(fam.get("mother_mobile") or ""),
        "students": students,
        "financial": {
            "balance": round(bal, 3),
            "monthly_due": m_due,
            "monthly_due_source": m_src,
            "currency": "JOD",
            "financial_available": True,
            "last_payment": last_p,
            "due_items": due_items
        }
    }
