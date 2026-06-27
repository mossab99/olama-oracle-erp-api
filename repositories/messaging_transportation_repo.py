"""Read-only Oracle queries for transportation messaging audiences."""

from datetime import date, datetime
from decimal import Decimal

from db import query_all


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return value


def _route_label(value):
    return {
        1: "\u062d\u0636\u0648\u0631 \u0648\u0639\u0648\u062f\u0629",
        2: "\u062d\u0636\u0648\u0631 \u0641\u0642\u0637",
        3: "\u0639\u0648\u062f\u0629 \u0641\u0642\u0637",
    }.get(int(value) if value is not None else None, "\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641")


def _bus_name_sql(bus_expression):
    # SCH_BUS_IDS exposes no school/year discriminator in the current API
    # mapping. A correlated MIN prevents repeated bus numbers from duplicating
    # students or families while keeping the existing mapping deterministic.
    return (
        "(SELECT MIN(b.BUS_DESC) FROM SCH_BUS_IDS b "
        f"WHERE b.BUS_SCHOOL_NUMBER = {bus_expression})"
    )


def _append_bus_filters(where_clauses, params, departure_bus, arrival_bus, route_mode):
    departure_clause = None
    arrival_clause = None
    if departure_bus is not None:
        departure_clause = "st.DEPARTURE_BUS = :departure_bus"
        params["departure_bus"] = int(departure_bus)
    if arrival_bus is not None:
        arrival_clause = "st.ARRIVAL_BUS = :arrival_bus"
        params["arrival_bus"] = int(arrival_bus)

    if route_mode == "departure":
        if departure_clause:
            where_clauses.append(departure_clause)
    elif route_mode == "arrival":
        if arrival_clause:
            where_clauses.append(arrival_clause)
    elif route_mode == "both":
        if departure_clause:
            where_clauses.append(departure_clause)
        if arrival_clause:
            where_clauses.append(arrival_clause)
    else:  # either
        candidates = [c for c in (departure_clause, arrival_clause) if c]
        if candidates:
            where_clauses.append("(" + " OR ".join(candidates) + ")")


def _dedupe_bus_options(rows):
    """Collapse repeated bus mappings without relying on Oracle GROUP BY quirks."""
    buses = {}
    for row in rows:
        bus_id = _json_safe(row.get("bus_id"))
        if bus_id is None:
            continue
        candidate = {
            "bus_id": bus_id,
            "bus_name": _json_safe(row.get("bus_name")),
            "bus_seq": _json_safe(row.get("bus_seq")),
        }
        current = buses.get(bus_id)
        if current is None:
            buses[bus_id] = candidate
            continue
        current_seq = current["bus_seq"] if current["bus_seq"] is not None else 10**9
        candidate_seq = candidate["bus_seq"] if candidate["bus_seq"] is not None else 10**9
        if (candidate_seq, str(candidate["bus_name"] or "")) < (
            current_seq,
            str(current["bus_name"] or ""),
        ):
            buses[bus_id] = candidate
    return sorted(
        buses.values(),
        key=lambda item: (
            item["bus_seq"] if item["bus_seq"] is not None else 10**9,
            item["bus_id"],
            str(item["bus_name"] or ""),
        ),
    )


def get_transportation_recipients(
    study_year,
    class_id=None,
    section_id=None,
    departure_bus=None,
    arrival_bus=None,
    trans_route=None,
    route_mode="either",
    active_only=True,
    family_id=None,
    limit=50,
    offset=0,
):
    """Return deduplicated family recipients and their matching students."""
    params = {"study_year": study_year}
    where = ["st.STUDY_YEAR = :study_year"]

    if active_only:
        # These are the active flags confirmed by the existing Oracle mapping.
        where.extend(["f.IS_ACTIVE = 1", "y.STUDENT_STATUS = 1", "st.IS_ACTIVE = 1"])
    if family_id is not None:
        where.append("st.FAMILY_ID = :family_id")
        params["family_id"] = int(family_id)
    if class_id is not None:
        where.append("y.CLASS_ID = :class_id")
        params["class_id"] = int(class_id)
    if section_id is not None:
        where.append("y.SECTION_ID = :section_id")
        params["section_id"] = int(section_id)
    if trans_route is not None:
        where.append("st.TRANS_ROUTE = :trans_route")
        params["trans_route"] = int(trans_route)

    _append_bus_filters(where, params, departure_bus, arrival_bus, route_mode)

    departure_name = _bus_name_sql("st.DEPARTURE_BUS")
    arrival_name = _bus_name_sql("st.ARRIVAL_BUS")
    sql = f"""
        SELECT
            f.FAMILY_ID AS family_id,
            f.SPONSER_FULL_NAME AS sponsor_full_name,
            TRIM(
                f.FATHER_NAME_1 || ' ' || f.FATHER_NAME_2 || ' ' ||
                f.FATHER_NAME_3 || ' ' || f.FATHER_SURNAME
            ) AS father_name,
            f.FATHER_MOBILE AS father_mobile,
            f.MOTHER_FULL_NAME AS mother_name,
            f.MOTHER_MOBILE AS mother_mobile,
            st.STUDENT_ID AS student_id,
            TRIM(
                s.STUDENT_NAME_1 || ' ' || s.STUDENT_NAME_2 || ' ' ||
                s.STUDENT_NAME_3 || ' ' || s.STUDENT_SURNAME
            ) AS student_name,
            y.CLASS_ID AS class_id,
            cls.CLASS_DESC AS class_name,
            y.SECTION_ID AS section_id,
            sec.SECTION_DESC AS section_name,
            st.DEPARTURE_BUS AS departure_bus,
            {departure_name} AS departure_bus_name,
            st.DEPARTURE_BUS_SEQ AS departure_bus_seq,
            st.ARRIVAL_BUS AS arrival_bus,
            {arrival_name} AS arrival_bus_name,
            st.ARRIVAL_BUS_SEQ AS arrival_bus_seq,
            st.TRANS_ROUTE AS trans_route
        FROM SCH_STUDENT_TRANS st
        JOIN SCH_FAMILY_CARD f
          ON f.FAMILY_ID = st.FAMILY_ID
        JOIN SCH_STUDENT_CARD s
          ON s.FAMILY_ID = st.FAMILY_ID
         AND s.STUDENT_ID = st.STUDENT_ID
        JOIN SCH_STUDENT_CARD_YEAR y
          ON y.FAMILY_ID = st.FAMILY_ID
         AND y.STUDENT_ID = st.STUDENT_ID
         AND y.STUDY_YEAR = st.STUDY_YEAR
        LEFT JOIN SCH_CLASSES cls ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec ON sec.SECTION_ID = y.SECTION_ID
        WHERE {" AND ".join(where)}
        ORDER BY f.FAMILY_ID, cls.CLASS_ORDER, sec.SECTION_DESC, st.STUDENT_ID
    """
    rows = query_all(sql, params)

    families = {}
    student_keys = set()
    for row in rows:
        family_key = int(row["family_id"])
        if family_key not in families:
            families[family_key] = {
                "family_id": family_key,
                "sponsor_full_name": _json_safe(row.get("sponsor_full_name") or ""),
                "father_name": _json_safe(row.get("father_name") or ""),
                "father_mobile": _json_safe(row.get("father_mobile") or ""),
                "mother_name": _json_safe(row.get("mother_name") or ""),
                "mother_mobile": _json_safe(row.get("mother_mobile") or ""),
                "student_count": 0,
                "matched_student_count": 0,
                "matching_students": [],
            }

        student_key = (
            family_key,
            int(row["student_id"]),
            row.get("departure_bus"),
            row.get("arrival_bus"),
            row.get("trans_route"),
        )
        if student_key in student_keys:
            continue
        student_keys.add(student_key)
        families[family_key]["matching_students"].append({
            "student_id": int(row["student_id"]),
            "student_name": _json_safe(row.get("student_name") or ""),
            "class_id": _json_safe(row.get("class_id")),
            "class_name": _json_safe(row.get("class_name")),
            "section_id": _json_safe(row.get("section_id")),
            "section_name": _json_safe(row.get("section_name")),
            "departure_bus": _json_safe(row.get("departure_bus")),
            "departure_bus_name": _json_safe(row.get("departure_bus_name")),
            "departure_bus_seq": _json_safe(row.get("departure_bus_seq")),
            "arrival_bus": _json_safe(row.get("arrival_bus")),
            "arrival_bus_name": _json_safe(row.get("arrival_bus_name")),
            "arrival_bus_seq": _json_safe(row.get("arrival_bus_seq")),
            "trans_route": _json_safe(row.get("trans_route")),
            "trans_route_name": _route_label(row.get("trans_route")),
        })

    all_recipients = list(families.values())
    total_count = len(all_recipients)
    recipients = all_recipients[offset:offset + limit]

    if recipients:
        family_ids = [recipient["family_id"] for recipient in recipients]
        placeholders = ", ".join(f":family_{i}" for i in range(len(family_ids)))
        count_params = {"study_year": study_year}
        count_params.update({f"family_{i}": value for i, value in enumerate(family_ids)})
        active_year = "AND y.STUDENT_STATUS = 1" if active_only else ""
        count_rows = query_all(f"""
            SELECT y.FAMILY_ID AS family_id, COUNT(DISTINCT y.STUDENT_ID) AS student_count
            FROM SCH_STUDENT_CARD_YEAR y
            WHERE y.STUDY_YEAR = :study_year
              AND y.FAMILY_ID IN ({placeholders})
              {active_year}
            GROUP BY y.FAMILY_ID
        """, count_params)
        counts = {int(row["family_id"]): int(row["student_count"]) for row in count_rows}
        for recipient in recipients:
            recipient["student_count"] = counts.get(recipient["family_id"], 0)
            recipient["matched_student_count"] = len(recipient["matching_students"])

    return total_count, recipients


def get_transportation_options(study_year, active_only=True):
    """Return distinct, consistently sorted transportation filter options."""
    params = {"study_year": study_year}
    where = ["st.STUDY_YEAR = :study_year"]
    if active_only:
        where.extend(["f.IS_ACTIVE = 1", "y.STUDENT_STATUS = 1", "st.IS_ACTIVE = 1"])
    where_sql = " AND ".join(where)
    base_joins = """
        FROM SCH_STUDENT_TRANS st
        JOIN SCH_FAMILY_CARD f ON f.FAMILY_ID = st.FAMILY_ID
        JOIN SCH_STUDENT_CARD_YEAR y
          ON y.FAMILY_ID = st.FAMILY_ID
         AND y.STUDENT_ID = st.STUDENT_ID
         AND y.STUDY_YEAR = st.STUDY_YEAR
        LEFT JOIN SCH_CLASSES cls ON cls.CLASS_ID = y.CLASS_ID
        LEFT JOIN SCH_SECTIONS sec ON sec.SECTION_ID = y.SECTION_ID
    """

    classes = query_all(f"""
        SELECT DISTINCT y.CLASS_ID AS class_id, cls.CLASS_DESC AS class_name
        {base_joins} WHERE {where_sql} AND y.CLASS_ID IS NOT NULL
        ORDER BY y.CLASS_ID
    """, params)
    sections = query_all(f"""
        SELECT DISTINCT y.CLASS_ID AS class_id, y.SECTION_ID AS section_id,
               sec.SECTION_DESC AS section_name
        {base_joins} WHERE {where_sql} AND y.SECTION_ID IS NOT NULL
        ORDER BY y.CLASS_ID, y.SECTION_ID
    """, params)

    departure_name = _bus_name_sql("st.DEPARTURE_BUS")
    arrival_name = _bus_name_sql("st.ARRIVAL_BUS")
    departure_rows = query_all(f"""
        SELECT DISTINCT st.DEPARTURE_BUS AS bus_id, {departure_name} AS bus_name,
               st.DEPARTURE_BUS_SEQ AS bus_seq
        {base_joins}
        WHERE {where_sql} AND NVL(st.DEPARTURE_BUS, 0) NOT IN (0, 999)
    """, params)
    arrival_rows = query_all(f"""
        SELECT DISTINCT st.ARRIVAL_BUS AS bus_id, {arrival_name} AS bus_name,
               st.ARRIVAL_BUS_SEQ AS bus_seq
        {base_joins}
        WHERE {where_sql} AND NVL(st.ARRIVAL_BUS, 0) NOT IN (0, 999)
    """, params)
    route_rows = query_all(f"""
        SELECT DISTINCT st.TRANS_ROUTE AS trans_route
        {base_joins} WHERE {where_sql} AND st.TRANS_ROUTE IS NOT NULL
        ORDER BY st.TRANS_ROUTE
    """, params)

    return {
        "classes": [{key: _json_safe(value) for key, value in row.items()} for row in classes],
        "sections": [{key: _json_safe(value) for key, value in row.items()} for row in sections],
        "departure_buses": _dedupe_bus_options(departure_rows),
        "arrival_buses": _dedupe_bus_options(arrival_rows),
        "routes": [
            {"trans_route": _json_safe(row["trans_route"]), "label": _route_label(row["trans_route"])}
            for row in route_rows
        ],
    }
