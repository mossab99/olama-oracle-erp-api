from datetime import date, datetime
from decimal import Decimal
import re

from db import query_all


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def _rows(sql, params=None):
    return [
        {key: _json_safe(value) for key, value in row.items()}
        for row in query_all(sql, params or {})
    ]


def get_grades():
    return _rows("""
        SELECT CLASS_ID AS grade_id, CLASS_DESC AS grade_name
        FROM SCH_CLASSES
        WHERE CLASS_ID IS NOT NULL
        ORDER BY CLASS_ID
    """)


def get_sections():
    return _rows("""
        SELECT SECTION_ID AS section_id, SECTION_DESC AS section_name
        FROM SCH_SECTIONS
        WHERE SECTION_ID IS NOT NULL
        ORDER BY SECTION_ID
    """)


def get_grade_sections(study_year):
    return _rows("""
        SELECT DISTINCT
            y.STUDY_YEAR AS study_year,
            y.CLASS_ID AS grade_id,
            cls.CLASS_DESC AS grade_name,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name
        FROM SCH_STUDENT_CARD_YEAR y
        LEFT JOIN SCH_CLASSES cls ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec ON sec.SECTION_ID = y.SECTION_ID
        WHERE y.STUDY_YEAR = :study_year
          AND y.CLASS_ID IS NOT NULL
          AND y.SECTION_ID IS NOT NULL
        ORDER BY y.CLASS_ID, y.SECTION_ID
    """, {"study_year": study_year})


def get_academic_students(study_year, grade_id=None, section_id=None):
    where = [
        "y.STUDY_YEAR = :study_year",
        "y.CLASS_ID IS NOT NULL",
        "y.STUDENT_STATUS = 1",
    ]
    params = {"study_year": study_year}
    if grade_id is not None:
        where.append("y.CLASS_ID = :grade_id")
        params["grade_id"] = grade_id
    if section_id is not None:
        where.append("y.SECTION_ID = :section_id")
        params["section_id"] = section_id

    return _rows(f"""
        SELECT
            y.STUDY_YEAR AS study_year,
            y.FAMILY_ID AS family_id,
            y.STUDENT_ID AS student_id,
            TRIM(
                s.STUDENT_NAME_1 || ' ' || s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' || s.STUDENT_SURNAME
            ) AS student_name,
            y.CLASS_ID AS grade_id,
            cls.CLASS_DESC AS grade_name,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,
            y.STUDENT_STATUS AS student_status
        FROM SCH_STUDENT_CARD_YEAR y
        JOIN SCH_STUDENT_CARD s
          ON s.FAMILY_ID = y.FAMILY_ID AND s.STUDENT_ID = y.STUDENT_ID
        LEFT JOIN SCH_CLASSES cls ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec ON sec.SECTION_ID = y.SECTION_ID
        WHERE {' AND '.join(where)}
        ORDER BY y.CLASS_ID, y.SECTION_ID, student_name, y.FAMILY_ID, y.STUDENT_ID
    """, params)


def _grade_subject_source():
    metadata = query_all("""
        SELECT table_name, column_name
        FROM user_tab_columns
        WHERE table_name LIKE 'SCH_MRK_CLS_SUBJECTS%'
        ORDER BY table_name, column_id
    """)
    columns_by_table = {}
    for row in metadata:
        table_name = str(row.get("table_name", "")).upper()
        column_name = str(row.get("column_name", "")).upper()
        if re.fullmatch(r"[A-Z0-9_$#]+", table_name) and re.fullmatch(
            r"[A-Z0-9_$#]+", column_name
        ):
            columns_by_table.setdefault(table_name, set()).add(column_name)

    candidates = [
        (table_name, columns)
        for table_name, columns in columns_by_table.items()
        if {"CLASS_ID", "SUBJECT_ID"}.issubset(columns)
    ]
    if not candidates:
        raise RuntimeError("Oracle grade-subject source table was not found")

    candidates.sort(key=lambda item: ("STUDY_YEAR" not in item[1], item[0]))
    return candidates[0]


def get_grade_subjects(study_year):
    table_name, columns = _grade_subject_source()
    year_filter = "AND link.STUDY_YEAR = :study_year" if "STUDY_YEAR" in columns else ""
    year_select = "link.STUDY_YEAR" if "STUDY_YEAR" in columns else ":study_year"
    active_filter = "AND NVL(link.IS_ACTIVE, 1) = 1" if "IS_ACTIVE" in columns else ""
    subject_name = (
        "link.SUBJECT_ID_DESC" if "SUBJECT_ID_DESC" in columns
        else "subject.SUBJECT_DESC"
    )
    subject_join = (
        "" if "SUBJECT_ID_DESC" in columns
        else "LEFT JOIN SCH_SUBJECTS subject ON subject.SUBJECT_ID = link.SUBJECT_ID"
    )

    return _rows(f"""
        SELECT DISTINCT
            {year_select} AS study_year,
            link.CLASS_ID AS grade_id,
            cls.CLASS_DESC AS grade_name,
            link.SUBJECT_ID AS subject_id,
            {subject_name} AS subject_name
        FROM {table_name} link
        LEFT JOIN SCH_CLASSES cls ON cls.CLASS_ID = link.CLASS_ID
        {subject_join}
        WHERE link.CLASS_ID IS NOT NULL
          AND link.SUBJECT_ID IS NOT NULL
          {year_filter}
          {active_filter}
        ORDER BY link.CLASS_ID, link.SUBJECT_ID
    """, {"study_year": study_year})


def get_academic_snapshot(study_year):
    return {
        "study_year": study_year,
        "grades": get_grades(),
        "sections": get_sections(),
        "grade_sections": get_grade_sections(study_year),
        "students": get_academic_students(study_year),
        "grade_subjects": get_grade_subjects(study_year),
    }
