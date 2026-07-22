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


def _grade_subject_schema():
    metadata = query_all("""
        SELECT table_name, column_name
        FROM user_tab_columns
        WHERE table_name LIKE 'SCH_MRK_CLS_SUBJECTS%'
           OR table_name = 'SCH_MRK_AVE_PARAM'
           OR (table_name LIKE 'SCH%SUBJECT%' AND table_name NOT LIKE 'SCH_MRK_CLS_SUBJECTS%')
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

    detail_candidates = [
        (table_name, columns)
        for table_name, columns in columns_by_table.items()
        if table_name.startswith("SCH_MRK_CLS_SUBJECTS")
        and "SUBJECT_ID" in columns
    ]
    if not detail_candidates:
        raise RuntimeError("Oracle grade-subject source table was not found")

    detail_candidates.sort(key=lambda item: ("STUDY_YEAR" not in item[1], item[0]))
    detail_table, detail_columns = detail_candidates[0]
    parent_columns = columns_by_table.get("SCH_MRK_AVE_PARAM", set())

    parent_join = ""
    grade_expression = "link.CLASS_ID"
    grade_columns = detail_columns
    grade_alias = "link"
    if "CLASS_ID" not in detail_columns:
        if "CLASS_ID" not in parent_columns:
            raise RuntimeError("Oracle grade-subject source has no CLASS_ID mapping")
        join_priority = (
            "LAW_ID", "AVE_ID", "PARAM_ID", "SERIAL_ID", "STUDY_YEAR",
            "SCHOOL_ID", "COMPANY_ID",
        )
        join_columns = [
            column for column in join_priority
            if column in detail_columns and column in parent_columns
        ]
        if not join_columns:
            raise RuntimeError("Oracle grade-subject parent relationship was not found")
        parent_join = "JOIN SCH_MRK_AVE_PARAM grade_param ON " + " AND ".join(
            f"grade_param.{column} = link.{column}" for column in join_columns
        )
        grade_expression = "grade_param.CLASS_ID"
        grade_columns = parent_columns
        grade_alias = "grade_param"

    subject_name = None
    subject_join = ""
    for description_column in ("SUBJECT_ID_DESC", "SUBJECT_DESC", "SUBJECT_NAME"):
        if description_column in detail_columns:
            subject_name = f"link.{description_column}"
            break

    if subject_name is None:
        lookup_candidates = []
        for table_name, columns in columns_by_table.items():
            if table_name.startswith("SCH_MRK_CLS_SUBJECTS") or "SUBJECT_ID" not in columns:
                continue
            description_column = next((
                column for column in ("SUBJECT_ID_DESC", "SUBJECT_DESC", "SUBJECT_NAME")
                if column in columns
            ), None)
            if description_column:
                lookup_candidates.append((table_name, columns, description_column))
        if lookup_candidates:
            lookup_candidates.sort(key=lambda item: (item[0] != "SCH_SUBJECTS", item[0]))
            lookup_table, lookup_columns, description_column = lookup_candidates[0]
            join_columns = ["SUBJECT_ID"] + [
                column for column in ("COMPANY_ID", "SCHOOL_ID")
                if column in detail_columns and column in lookup_columns
            ]
            subject_join = f"LEFT JOIN {lookup_table} subject ON " + " AND ".join(
                f"subject.{column} = link.{column}" for column in join_columns
            )
            subject_name = f"subject.{description_column}"

    if subject_name is None:
        subject_name = "TO_CHAR(link.SUBJECT_ID)"

    return {
        "detail_table": detail_table,
        "detail_columns": detail_columns,
        "parent_join": parent_join,
        "grade_expression": grade_expression,
        "grade_columns": grade_columns,
        "grade_alias": grade_alias,
        "subject_join": subject_join,
        "subject_name": subject_name,
    }


def get_grade_subjects(study_year):
    schema = _grade_subject_schema()
    columns = schema["detail_columns"]
    grade_columns = schema["grade_columns"]
    grade_alias = schema["grade_alias"]
    if "STUDY_YEAR" in columns:
        year_filter = "AND link.STUDY_YEAR = :study_year"
        year_select = "link.STUDY_YEAR"
    elif "STUDY_YEAR" in grade_columns:
        year_filter = f"AND {grade_alias}.STUDY_YEAR = :study_year"
        year_select = f"{grade_alias}.STUDY_YEAR"
    else:
        year_filter = ""
        year_select = ":study_year"
    active_filter = "AND NVL(link.IS_ACTIVE, 1) = 1" if "IS_ACTIVE" in columns else ""

    return _rows(f"""
        SELECT DISTINCT
            {year_select} AS study_year,
            {schema['grade_expression']} AS grade_id,
            cls.CLASS_DESC AS grade_name,
            link.SUBJECT_ID AS subject_id,
            {schema['subject_name']} AS subject_name
        FROM {schema['detail_table']} link
        {schema['parent_join']}
        LEFT JOIN SCH_CLASSES cls ON cls.CLASS_ID = {schema['grade_expression']}
        {schema['subject_join']}
        WHERE {schema['grade_expression']} IS NOT NULL
          AND link.SUBJECT_ID IS NOT NULL
          {year_filter}
          {active_filter}
        ORDER BY {schema['grade_expression']}, link.SUBJECT_ID
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
