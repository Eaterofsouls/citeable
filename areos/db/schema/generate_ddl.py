# areos/db/schema/generate_ddl.py
#
# DEPRECATED (Readiness Audit, Blocker 1): this generator only reads
# artifacts.py and silently omits everything mixins.py contributes
# (_txn_context, changelog, the audit triggers write_as() depends on).
# Running this script and committing its output is exactly how
# areos/db/schema.sql drifted out of sync with the real schema before.
#
# Use the root-level generate_schema.py instead — it compiles both
# mixins.py AND artifacts.py — then copy its output here:
#   python generate_schema.py && cp schema.sql areos/db/schema.sql
#
# This file is kept only for reference and is not called by migrate_audit_tables.py.
#
# USAGE (legacy, do not use): python -m areos.db.schema.generate_ddl
#
# Reads TABLES and STANDALONE_INDEXES from artifacts.py and renders
# schema.sql. schema.sql is a GENERATED FILE - do not edit it by hand.
# Edit artifacts.py, then re-run this script.

from __future__ import annotations

from pathlib import Path

from areos.db.schema.artifacts import STANDALONE_INDEXES, TABLES


def render_sql(tables: dict) -> str:  # noqa: E501
    """
    Render CREATE TABLE and CREATE INDEX statements from the TABLES DSL.
    Returns the full SQL string.
    """
    lines: list[str] = [
        "-- GENERATED FILE - edit artifacts.py, then run generate_ddl.py",
        "-- DO NOT EDIT DIRECTLY.",
        "",
    ]

    for table_name, spec in tables.items():
        cols = spec.get("columns", [])
        col_defs = []
        for col in cols:
            col_name, col_type, constraint = col[0], col[1], col[2]
            if constraint:
                col_defs.append(f"    {col_name:<24} {col_type:<10} {constraint}")
            else:
                col_defs.append(f"    {col_name:<24} {col_type}")
        col_block = ",\n".join(col_defs)
        lines.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")
        lines.append(col_block)
        lines.append(");")
        lines.append("")

        # Per-table indexes
        for idx_sql in spec.get("indexes", []):
            lines.append(idx_sql)
        if spec.get("indexes"):
            lines.append("")

    # Standalone indexes
    if STANDALONE_INDEXES:
        lines.append("-- Standalone indexes (SEC-21)")
        for idx_sql in STANDALONE_INDEXES:
            lines.append(idx_sql)
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    sql = render_sql(TABLES)
    output_path = Path(__file__).resolve().parents[1] / "schema.sql"
    output_path.write_text(sql, encoding="utf-8")
    print(f"schema.sql written to {output_path}")


if __name__ == "__main__":
    main()
