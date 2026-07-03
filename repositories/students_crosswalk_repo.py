from db import query_all, query_one


def _iso_dates(rows):
    for row in rows:
        for key in ("registration_date", "withdraw_date"):
            value = row.get(key)
            if value is not None and hasattr(value, "isoformat"):
                row[key] = value.date().isoformat() if hasattr(value, "date") else value.isoformat()
        row.pop("rn", None)
    return rows


def _public_crosswalk_rows(rows):
    for row in rows:
        if "legacy_ref" in row:
            row["immutable_legacy_billing_student_ref"] = row.pop("legacy_ref")
    return rows


def _public_diagnostics(diagnostics):
    if "sid_reuse_families" in diagnostics:
        diagnostics["student_id_values_reused_across_families"] = diagnostics.pop("sid_reuse_families")
    return diagnostics


def get_student_crosswalk(
    study_year=None,
    include_inactive=False,
    family_id=None,
    student_id=None,
    limit=500,
    offset=0,
):
    filters = []
    params = {
        "max_row": offset + limit,
        "offset": offset,
    }

    if study_year is not None:
        filters.append("y.STUDY_YEAR = :study_year")
        params["study_year"] = study_year
    if not include_inactive:
        filters.append("y.STUDENT_STATUS = 1")
    if family_id is not None:
        filters.append("s.FAMILY_ID = :family_id")
        params["family_id"] = family_id
    if student_id is not None:
        filters.append("s.STUDENT_ID = :student_id")
        params["student_id"] = student_id

    where_clause = " AND ".join(filters) if filters else "1 = 1"
    sql = f"""
        SELECT *
        FROM (
            SELECT inner_query.*, ROWNUM AS rn
            FROM (
                SELECT
                    s.FAMILY_ID AS oracle_family_id,
                    s.STUDENT_ID AS oracle_student_id,
                    TO_CHAR(s.FAMILY_ID) || ':' || TO_CHAR(s.STUDENT_ID)
                        AS oracle_student_key,
                    y.STUDY_YEAR AS study_year,
                    y.STUDENT_STATUS AS student_status,
                    CASE y.STUDENT_STATUS
                        WHEN 1 THEN 'ACTIVE'
                        WHEN 2 THEN 'INACTIVE'
                        ELSE 'UNKNOWN'
                    END AS student_status_text,
                    y.CLASS_ID AS class_id,
                    cls.CLASS_DESC AS class_name,
                    y.SECTION_ID AS section_id,
                    sec.SECTION_DESC AS section_name,
                    y.SCHOOL_ID AS school_id,
                    school.SCHOOL_DESC AS school_name,
                    y.BRANCH_ID AS branch_id,
                    br.BRANCH_DESC AS branch_name,
                    y.REGISTRATION_DATE AS registration_date,
                    y.WITHDRAW_DATE AS withdraw_date,
                    CAST(NULL AS VARCHAR2(100))
                        AS legacy_ref,
                    CAST(NULL AS VARCHAR2(100)) AS legacy_billing_student_id,
                    CAST(NULL AS VARCHAR2(100)) AS legacy_school_student_id
                FROM SCH_STUDENT_CARD s
                JOIN SCH_STUDENT_CARD_YEAR y
                    ON y.FAMILY_ID = s.FAMILY_ID
                   AND y.STUDENT_ID = s.STUDENT_ID
                LEFT JOIN SCH_CLASSES cls
                    ON cls.CLASS_ID = y.CLASS_ID
                LEFT JOIN SCH_SECTIONS sec
                    ON sec.SECTION_ID = y.SECTION_ID
                LEFT JOIN SCH_SCHOOL school
                    ON school.SCHOOL_ID = y.SCHOOL_ID
                LEFT JOIN SCH_STUDY_BRANCHES br
                    ON br.BRANCH_ID = y.BRANCH_ID
                WHERE {where_clause}
                ORDER BY y.STUDY_YEAR, s.FAMILY_ID, s.STUDENT_ID
            ) inner_query
            WHERE ROWNUM <= :max_row
        )
        WHERE rn > :offset
    """

    return _public_crosswalk_rows(_iso_dates(query_all(sql, params)))


def get_student_crosswalk_diagnostics(study_year=None):
    params = {"study_year": study_year}
    base_filter = "(:study_year IS NULL OR y.STUDY_YEAR = :study_year)"
    sql = f"""
        SELECT
            COUNT(*) AS student_year_rows,
            COUNT(DISTINCT TO_CHAR(s.FAMILY_ID) || ':' || TO_CHAR(s.STUDENT_ID))
                AS unique_oracle_student_keys,
            SUM(CASE WHEN s.FAMILY_ID IS NULL THEN 1 ELSE 0 END)
                AS students_missing_family_id,
            SUM(CASE WHEN s.STUDENT_ID IS NULL THEN 1 ELSE 0 END)
                AS students_missing_student_id,
            SUM(CASE WHEN y.STUDENT_STATUS = 1 THEN 1 ELSE 0 END)
                AS active_rows,
            SUM(CASE WHEN y.STUDENT_STATUS <> 1 OR y.STUDENT_STATUS IS NULL
                THEN 1 ELSE 0 END) AS inactive_rows
        FROM SCH_STUDENT_CARD s
        JOIN SCH_STUDENT_CARD_YEAR y
            ON y.FAMILY_ID = s.FAMILY_ID
           AND y.STUDENT_ID = s.STUDENT_ID
        WHERE {base_filter}
    """
    diagnostics = query_one(sql, params) or {}

    duplicate_sql = f"""
        SELECT COUNT(*) AS duplicate_oracle_student_keys
        FROM (
            SELECT y.STUDY_YEAR, s.FAMILY_ID, s.STUDENT_ID
            FROM SCH_STUDENT_CARD s
            JOIN SCH_STUDENT_CARD_YEAR y
                ON y.FAMILY_ID = s.FAMILY_ID
               AND y.STUDENT_ID = s.STUDENT_ID
            WHERE {base_filter}
            GROUP BY y.STUDY_YEAR, s.FAMILY_ID, s.STUDENT_ID
            HAVING COUNT(*) > 1
        )
    """
    reused_sql = f"""
        SELECT COUNT(*) AS sid_reuse_families
        FROM (
            SELECT s.STUDENT_ID
            FROM SCH_STUDENT_CARD s
            JOIN SCH_STUDENT_CARD_YEAR y
                ON y.FAMILY_ID = s.FAMILY_ID
               AND y.STUDENT_ID = s.STUDENT_ID
            WHERE {base_filter}
            GROUP BY s.STUDENT_ID
            HAVING COUNT(DISTINCT s.FAMILY_ID) > 1
        )
    """
    duplicate = query_one(duplicate_sql, params) or {}
    reused = query_one(reused_sql, params) or {}
    diagnostics.update(duplicate)
    diagnostics.update(reused)

    for key, value in diagnostics.items():
        diagnostics[key] = int(value or 0)
    return _public_diagnostics(diagnostics)


def get_student_crosswalk_schema_candidates():
    sql = """
        SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name
        FROM USER_TAB_COLUMNS
        WHERE TABLE_NAME IN ('SCH_STUDENT_CARD', 'SCH_STUDENT_CARD_YEAR')
          AND (
                COLUMN_NAME LIKE '%BILL%'
             OR COLUMN_NAME LIKE '%LEGACY%'
             OR COLUMN_NAME LIKE '%OLD%'
             OR COLUMN_NAME LIKE '%REF%'
             OR COLUMN_NAME LIKE '%SERIAL%'
             OR COLUMN_NAME LIKE '%SEQ%'
             OR COLUMN_NAME LIKE '%NO%'
             OR COLUMN_NAME LIKE '%NUMBER%'
             OR COLUMN_NAME LIKE '%REG%'
             OR COLUMN_NAME LIKE '%REGISTER%'
          )
        ORDER BY TABLE_NAME, COLUMN_ID
    """
    return query_all(sql)
