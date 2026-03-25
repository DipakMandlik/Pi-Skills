from __future__ import annotations

from backend.scripts.migrate_identity_users import main as backend_migration_main


def main() -> int:
    # Wrapper entrypoint for apps/api namespace.
    # Current migration workflow targets backend active data model.
    return backend_migration_main()


if __name__ == "__main__":
    raise SystemExit(main())
