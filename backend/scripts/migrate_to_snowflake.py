from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import snowflake.connector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backend.migrate_to_snowflake")

TABLE_ORDER: list[tuple[str, str]] = [
    ("APP", "users"),
    ("APP", "registered_models"),
    ("APP", "subscriptions"),
    ("APP", "user_subscriptions"),
    ("APP", "model_access_control"),
    ("APP", "feature_flags"),
    ("APP", "model_permissions"),
    ("APP", "skill_assignments"),
    ("APP", "user_tokens"),
    ("APP", "token_usage_log"),
    ("APP", "cost_tracking"),
    ("AUDIT", "audit_log"),
    ("APP", "mcp_sessions"),
]

VARIANT_COLUMNS = {
    "metadata",
    "allowed_models",
    "features",
    "allowed_roles",
    "enabled_for",
    "config",
}


@dataclass
class SnowflakeTarget:
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate operational data to Snowflake")
    parser.add_argument("--sqlite-path", required=True, help="Path to sqlite source DB")
    parser.add_argument("--sf-account", required=True)
    parser.add_argument("--sf-user", required=True)
    parser.add_argument("--sf-password", required=True)
    parser.add_argument("--sf-role", required=True)
    parser.add_argument("--sf-warehouse", required=True)
    parser.add_argument("--sf-database", default="PI_OPTIMIZED")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--truncate-target", action="store_true")
    return parser.parse_args()


def quote_ident(name: str) -> str:
    return f'"{name}"'


def parse_variant_if_needed(column: str, value: Any) -> Any:
    if value is None:
        return None
    if column not in VARIANT_COLUMNS:
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                return json.dumps(parsed)
            except json.JSONDecodeError:
                return json.dumps(value)
        return json.dumps(value)
    return json.dumps(value)


def get_sqlite_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(row[1]) for row in rows]


def fetch_sqlite_rows(conn: sqlite3.Connection, table_name: str) -> list[sqlite3.Row]:
    return conn.execute(f"SELECT * FROM {table_name}").fetchall()


def chunked(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    sf_cursor: snowflake.connector.cursor.SnowflakeCursor,
    schema_name: str,
    table_name: str,
    batch_size: int,
    dry_run: bool,
    truncate_target: bool,
) -> int:
    columns = get_sqlite_columns(sqlite_conn, table_name)
    rows = fetch_sqlite_rows(sqlite_conn, table_name)

    logger.info("%s.%s: source rows=%d", schema_name, table_name, len(rows))
    if not rows:
        return 0

    fq_table = f'{quote_ident(schema_name)}.{quote_ident(table_name)}'

    if dry_run:
        return len(rows)

    if truncate_target:
        sf_cursor.execute(f"TRUNCATE TABLE IF EXISTS {fq_table}")

    quoted_cols = ", ".join(quote_ident(c) for c in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = f"INSERT INTO {fq_table} ({quoted_cols}) VALUES ({placeholders})"

    total_inserted = 0
    for batch in chunked(rows, batch_size):
        converted_batch: list[tuple[Any, ...]] = []
        for row in batch:
            converted = tuple(parse_variant_if_needed(col, row[col]) for col in columns)
            converted_batch.append(converted)
        sf_cursor.executemany(insert_sql, converted_batch)
        total_inserted += len(batch)

    logger.info("%s.%s: migrated rows=%d", schema_name, table_name, total_inserted)
    return total_inserted


def main() -> int:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        logger.error("SQLite database not found: %s", sqlite_path)
        return 2

    target = SnowflakeTarget(
        account=args.sf_account,
        user=args.sf_user,
        password=args.sf_password,
        role=args.sf_role,
        warehouse=args.sf_warehouse,
        database=args.sf_database,
    )

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row

    sf_conn = snowflake.connector.connect(
        account=target.account,
        user=target.user,
        password=target.password,
        role=target.role,
        warehouse=target.warehouse,
        database=target.database,
    )

    try:
        sf_cursor = sf_conn.cursor()
        migrated_summary: dict[str, int] = {}

        for schema_name, table_name in TABLE_ORDER:
            sqlite_table_exists = sqlite_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
            if sqlite_table_exists is None:
                logger.warning("Skipping missing source table: %s", table_name)
                continue

            sf_cursor.execute(f"USE SCHEMA {quote_ident(schema_name)}")
            migrated = migrate_table(
                sqlite_conn=sqlite_conn,
                sf_cursor=sf_cursor,
                schema_name=schema_name,
                table_name=table_name,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
                truncate_target=args.truncate_target,
            )
            migrated_summary[f"{schema_name}.{table_name}"] = migrated

        if args.dry_run:
            logger.info("Dry run complete. No writes were made.")
        else:
            sf_conn.commit()
            logger.info("Migration committed.")

        total_rows = sum(migrated_summary.values())
        logger.info("Total migrated rows=%d", total_rows)
        for table_key, row_count in migrated_summary.items():
            logger.info("  %s -> %d", table_key, row_count)

        return 0
    except Exception:
        if not args.dry_run:
            sf_conn.rollback()
        logger.exception("Migration failed")
        return 1
    finally:
        sf_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
