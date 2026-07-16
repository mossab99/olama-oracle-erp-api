import re
from datetime import date, datetime

from config import Config
from db import query_all


EMPLOYEE_TABLE = "HR_EMP_CARD"

FIELD_CANDIDATES = {
    "employee_id": ("EMP_ID",),
    "full_name": ("EMP_FULL_NAME",),
    "national_number": ("NATIONAL_NUMBER",),
    "birth_date": ("BIRTH_DATE",),
    "gender": ("EMP_GENDER",),
    "job_title": ("EMP_JOB_ID_DESC",),
    "appointment_date": (
        "EMP_APPOINTMEN",
        "EMP_APPOINTMENT",
        "EMP_APPOINTMENT_DATE",
        "EMP_APPOINTMENT_DT",
    ),
    "address": ("EMP_ADDRESS",),
    "phones": ("EMP_PHONES",),
    "certificate_grade": (
        "CERT_GRADE_ID_DESC",
        "CERT_GRADE_DESC",
        "CERT_GRADE_ID_D",
    ),
    "certificate_type": ("CERT_TYPE_DESC",),
    "certificate_date": ("CERT_DATE",),
    "certificate_average": ("CERT_AVERAGE",),
}

STATUS_ID_CANDIDATES = (
    "EMPLOYTE_CASE_ID",
    "EMPLOYEE_CASE_ID",
    "EMP_CASE_ID",
)

STATUS_DESC_CANDIDATES = (
    "EMPLOYTE_CASE_DESC",
    "EMPLOYEE_CASE_DESC",
    "EMP_CASE_DESC",
    "EMPLOYTE_CASE_NAME",
    "EMPLOYEE_CASE_NAME",
    "EMP_CASE_NAME",
)


def _safe_identifier(value):
    value = str(value or "").upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9_$#]{0,29}", value):
        raise RuntimeError("Oracle metadata returned an unsafe identifier")
    return value


def _table_columns(table_name):
    rows = query_all(
        """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM USER_TAB_COLUMNS
        WHERE TABLE_NAME = :table_name
        """,
        {"table_name": table_name},
    )
    return {
        _safe_identifier(row["column_name"]): str(row["data_type"]).upper()
        for row in rows
    }


def _first_available(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _find_status_lookup():
    candidates = STATUS_ID_CANDIDATES + STATUS_DESC_CANDIDATES
    binds = {"column_{}".format(index): name for index, name in enumerate(candidates)}
    placeholders = ", ".join(":" + key for key in binds)
    rows = query_all(
        """
        SELECT TABLE_NAME, COLUMN_NAME
        FROM USER_TAB_COLUMNS
        WHERE COLUMN_NAME IN ({})
          AND TABLE_NAME <> :employee_table
        ORDER BY TABLE_NAME, COLUMN_ID
        """.format(placeholders),
        dict(binds, employee_table=EMPLOYEE_TABLE),
    )

    tables = {}
    for row in rows:
        table = _safe_identifier(row["table_name"])
        tables.setdefault(table, set()).add(_safe_identifier(row["column_name"]))

    for table, columns in tables.items():
        status_id = _first_available(columns, STATUS_ID_CANDIDATES)
        status_desc = _first_available(columns, STATUS_DESC_CANDIDATES)
        if status_id and status_desc:
            return table, status_id, status_desc

    return None


def _status_sql(columns):
    status_desc = _first_available(columns, STATUS_DESC_CANDIDATES)
    status_id = _first_available(columns, STATUS_ID_CANDIDATES)

    if status_desc:
        return (
            "",
            "e.{} AS employee_status".format(_safe_identifier(status_desc)),
            "TRIM(e.{}) = :active_status".format(_safe_identifier(status_desc)),
            {"active_status": Config.EMPLOYEE_ACTIVE_STATUS},
        )

    if status_id:
        if status_id == "EMPLOYEE_CASE_ID":
            lookup_columns = _table_columns("HR_EMPLOYEE_CASES")
            if "CASE_ID" in lookup_columns and "CASE_DESC" in lookup_columns:
                join_conditions = [
                    "employee_case.CASE_ID = e.EMPLOYEE_CASE_ID"
                ]
                if "COMPANY_ID" in columns and "COMPANY_ID" in lookup_columns:
                    join_conditions.append(
                        "employee_case.COMPANY_ID = e.COMPANY_ID"
                    )
                return (
                    "LEFT JOIN HR_EMPLOYEE_CASES employee_case ON "
                    + " AND ".join(join_conditions),
                    "employee_case.CASE_DESC AS employee_status",
                    "TRIM(employee_case.CASE_DESC) = :active_status",
                    {"active_status": Config.EMPLOYEE_ACTIVE_STATUS},
                )

        lookup = _find_status_lookup()
        if lookup:
            table, lookup_id, lookup_desc = lookup
            join_sql = "LEFT JOIN {} employee_case ON employee_case.{} = e.{}".format(
                table, lookup_id, status_id
            )
            return (
                join_sql,
                "employee_case.{} AS employee_status".format(lookup_desc),
                "TRIM(employee_case.{}) = :active_status".format(lookup_desc),
                {"active_status": Config.EMPLOYEE_ACTIVE_STATUS},
            )

        if Config.EMPLOYEE_ACTIVE_STATUS_ID:
            return (
                "",
                ":active_status AS employee_status",
                "TO_CHAR(e.{}) = :active_status_id".format(status_id),
                {
                    "active_status": Config.EMPLOYEE_ACTIVE_STATUS,
                    "active_status_id": Config.EMPLOYEE_ACTIVE_STATUS_ID,
                },
            )

    raise RuntimeError(
        "Could not resolve the HR_EMP_CARD employee status field or lookup"
    )


def _serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def get_active_employees(limit=100, offset=0):
    limit = int(limit)
    offset = int(offset)
    if limit < 1 or limit > 1000 or offset < 0:
        raise ValueError("Invalid pagination")

    columns = _table_columns(EMPLOYEE_TABLE)
    employee_id = _first_available(columns, FIELD_CANDIDATES["employee_id"])
    full_name = _first_available(columns, FIELD_CANDIDATES["full_name"])
    if not employee_id or not full_name:
        raise RuntimeError("HR_EMP_CARD is missing EMP_ID or EMP_FULL_NAME")

    select_fields = []
    enrichment_joins = []
    for alias, candidates in FIELD_CANDIDATES.items():
        column = _first_available(columns, candidates)
        if column:
            select_fields.append("e.{} AS {}".format(column, alias))
        elif alias == "job_title" and "EMP_JOB_ID" in columns:
            select_fields.append("job_lookup.JOB_DESC AS job_title")
            job_conditions = ["job_lookup.JOB_ID = e.EMP_JOB_ID"]
            if "COMPANY_ID" in columns:
                job_conditions.append("job_lookup.COMPANY_ID = e.COMPANY_ID")
            enrichment_joins.append(
                "LEFT JOIN HR_GENERAL_JOB_TITLE job_lookup ON "
                + " AND ".join(job_conditions)
            )
        elif alias == "certificate_grade" and "CERT_GRADE_ID" in columns:
            select_fields.append("certificate_grade_lookup.GRADE_DESC AS certificate_grade")
            enrichment_joins.append(
                "LEFT JOIN HR_CERTIFICATE_GRADE certificate_grade_lookup "
                "ON certificate_grade_lookup.GRADE_ID = e.CERT_GRADE_ID"
            )
        elif alias == "certificate_type" and "CERT_TYPE" in columns:
            select_fields.append("certificate_type_lookup.CERT_DESC AS certificate_type")
            enrichment_joins.append(
                "LEFT JOIN HR_CERTIFICATE_TYPE certificate_type_lookup "
                "ON certificate_type_lookup.CERT_ID = e.CERT_TYPE"
            )
        else:
            select_fields.append("NULL AS {}".format(alias))

    join_sql, status_select, status_where, status_params = _status_sql(columns)
    select_fields.append(status_select)

    sql = """
        SELECT *
        FROM (
            SELECT employee_rows.*, ROWNUM AS rn
            FROM (
                SELECT
                    {select_fields}
                FROM {employee_table} e
                {enrichment_joins}
                {join_sql}
                WHERE {status_where}
                ORDER BY e.{employee_id}
            ) employee_rows
            WHERE ROWNUM <= :max_row
        )
        WHERE rn > :offset
    """.format(
        select_fields=",\n                    ".join(select_fields),
        employee_table=EMPLOYEE_TABLE,
        enrichment_joins="\n                ".join(enrichment_joins),
        join_sql=join_sql,
        status_where=status_where,
        employee_id=employee_id,
    )

    params = dict(status_params, max_row=offset + limit, offset=offset)
    rows = query_all(sql, params)
    for row in rows:
        row.pop("rn", None)
        for key, value in list(row.items()):
            row[key] = _serialize_value(value)
    return rows
