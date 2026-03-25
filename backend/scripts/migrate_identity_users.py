from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bcrypt
from sqlalchemy import or_, select

from backend.core.config import load_settings
from backend.core import database as dbmod
from backend.core.database import UserModel
from backend.core.rbac import PlatformRole


FORBIDDEN_EMAIL_DOMAINS = {
    "platform.local",
    "example.com",
    "example.org",
    "example.net",
    "test.local",
    "localhost",
    "localdomain",
}


@dataclass
class IdentityRecord:
    external_id: str
    email: str
    display_name: str
    role: str
    is_active: bool


def _to_bool(value: Any, fallback: bool = True) -> bool:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return fallback


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_email_no_placeholder(email: str) -> tuple[bool, str | None]:
    if "@" not in email:
        return False, "email is invalid"
    domain = email.split("@", 1)[1].lower()
    if domain in FORBIDDEN_EMAIL_DOMAINS or domain.endswith(".local"):
        return False, f"email domain '{domain}' is blocked (placeholder/test domain)"
    return True, None


def _parse_role(raw_role: str, default_role: str, strict_roles: bool) -> tuple[str | None, str | None]:
    role = (raw_role or "").strip().upper()
    if not role:
        return default_role, None
    if role in PlatformRole.all_values():
        return role, None
    if strict_roles:
        return None, f"unknown role '{raw_role}'"
    return default_role, None


def _build_unusable_password_hash() -> str:
    token = secrets.token_urlsafe(32)
    return bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _infer_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".jsonl", ".ndjson"}:
        return "jsonl"
    return "json"


def _load_records(path: Path, fmt: str) -> list[dict[str, Any]]:
    if fmt == "csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if fmt == "jsonl":
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_no, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc
                if not isinstance(obj, dict):
                    raise ValueError(f"Line {line_no} must be a JSON object")
                rows.append(obj)
        return rows

    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise ValueError("JSON array must contain only objects")
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("users"), list):
        users = payload["users"]
        if not all(isinstance(item, dict) for item in users):
            raise ValueError("'users' array must contain only objects")
        return users
    raise ValueError("JSON input must be a list of objects or an object containing a 'users' list")


def _normalize_record(
    row: dict[str, Any],
    default_role: str,
    strict_roles: bool,
) -> tuple[IdentityRecord | None, str | None]:
    external_id = str(row.get("external_id") or row.get("id") or "").strip()
    email = _normalize_email(str(row.get("email") or ""))
    display_name = str(row.get("display_name") or row.get("name") or email).strip()
    role_raw = str(row.get("platform_role") or row.get("role") or "").strip()
    is_active = _to_bool(row.get("is_active"), fallback=True)

    if not external_id:
        return None, "external_id is required"
    if not email:
        return None, "email is required"

    ok, reason = _validate_email_no_placeholder(email)
    if not ok:
        return None, reason

    role, role_error = _parse_role(role_raw, default_role=default_role, strict_roles=strict_roles)
    if role_error:
        return None, role_error

    return IdentityRecord(
        external_id=external_id,
        email=email,
        display_name=display_name or email,
        role=role or default_role,
        is_active=is_active,
    ), None


async def _migrate(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    if not source.exists():
        print(f"ERROR: source file not found: {source}")
        return 2

    fmt = args.format or _infer_format(source)
    if fmt not in {"csv", "json", "jsonl"}:
        print(f"ERROR: unsupported format '{fmt}'. Use csv, json, or jsonl")
        return 2

    settings = load_settings()
    dbmod.init_engine(settings)
    await dbmod.create_tables()

    if dbmod._session_factory is None:
        print("ERROR: database session factory not initialized")
        return 2

    provider = args.provider.strip()
    default_role = args.default_role.strip().upper()
    if default_role not in PlatformRole.all_values():
        print(f"ERROR: default role '{default_role}' is invalid")
        return 2

    raw_rows = _load_records(source, fmt)

    run_id = secrets.token_hex(8)
    imported_external_ids: set[str] = set()

    summary: dict[str, Any] = {
        "run_id": run_id,
        "source": str(source),
        "provider": provider,
        "format": fmt,
        "dry_run": args.dry_run,
        "input_rows": len(raw_rows),
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "deactivated": 0,
        "skipped": 0,
        "errors": [],
    }

    async with dbmod._session_factory() as db:
        for idx, row in enumerate(raw_rows, start=1):
            record, err = _normalize_record(
                row,
                default_role=default_role,
                strict_roles=args.strict_roles,
            )
            if err:
                summary["skipped"] += 1
                summary["errors"].append({"row": idx, "external_id": row.get("external_id"), "error": err})
                continue

            imported_external_ids.add(record.external_id)

            query = select(UserModel).where(
                or_(
                    UserModel.external_id == record.external_id,
                    UserModel.email == record.email,
                )
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing is None:
                metadata = {
                    "identity_managed": True,
                    "identity_provider": provider,
                    "imported_by": "migrate_identity_users",
                    "import_run_id": run_id,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }
                user = UserModel(
                    external_id=record.external_id,
                    email=record.email,
                    display_name=record.display_name,
                    platform_role=record.role,
                    is_active=record.is_active,
                    password_hash=_build_unusable_password_hash(),
                    metadata_=metadata,
                )
                db.add(user)
                summary["created"] += 1
                continue

            changed = False
            if existing.external_id != record.external_id:
                existing.external_id = record.external_id
                changed = True
            if existing.email != record.email:
                existing.email = record.email
                changed = True
            if (existing.display_name or "") != record.display_name:
                existing.display_name = record.display_name
                changed = True
            if (existing.platform_role or "").upper() != record.role:
                existing.platform_role = record.role
                changed = True
            if bool(existing.is_active) != record.is_active:
                existing.is_active = record.is_active
                changed = True

            metadata = dict(existing.metadata_ or {})
            metadata.update(
                {
                    "identity_managed": True,
                    "identity_provider": provider,
                    "imported_by": "migrate_identity_users",
                    "import_run_id": run_id,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            if existing.metadata_ != metadata:
                existing.metadata_ = metadata
                changed = True

            if changed:
                summary["updated"] += 1
            else:
                summary["unchanged"] += 1

        if args.deactivate_missing:
            all_users = await db.execute(select(UserModel))
            for user in all_users.scalars().all():
                metadata = dict(user.metadata_ or {})
                if not metadata.get("identity_managed"):
                    continue
                if metadata.get("identity_provider") != provider:
                    continue
                if user.external_id in imported_external_ids:
                    continue
                if not user.is_active:
                    continue

                user.is_active = False
                metadata["deactivated_by"] = "migrate_identity_users"
                metadata["deactivated_at"] = datetime.now(timezone.utc).isoformat()
                metadata["deactivated_run_id"] = run_id
                user.metadata_ = metadata
                summary["deactivated"] += 1

        if args.dry_run:
            await db.rollback()
        else:
            await db.commit()

    print(json.dumps(summary, indent=2))

    if summary["errors"] and args.fail_on_skipped:
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate real identity users into backend users table without placeholder accounts. "
            "Supports CSV/JSON/JSONL, validates roles, and can deactivate missing identity users."
        )
    )
    parser.add_argument("--source", required=True, help="Path to identity export file (csv/json/jsonl)")
    parser.add_argument("--format", choices=["csv", "json", "jsonl"], help="Input format (auto-inferred if omitted)")
    parser.add_argument("--provider", default="identity-source", help="Identity provider label (e.g. okta, entra-id)")
    parser.add_argument("--default-role", default="VIEWER", help="Default platform role when role is not provided")
    parser.add_argument("--strict-roles", action=argparse.BooleanOptionalAction, default=True, help="Reject unknown roles (default: true)")
    parser.add_argument("--deactivate-missing", action="store_true", help="Deactivate identity-managed users not present in current import")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview changes without committing")
    parser.add_argument("--fail-on-skipped", action="store_true", help="Return non-zero exit code when any rows are skipped")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_migrate(args))


if __name__ == "__main__":
    raise SystemExit(main())
