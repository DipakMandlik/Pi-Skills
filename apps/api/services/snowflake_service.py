from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger("backend.snowflake")

_ROLE_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 minutes


class SnowflakeService:
    def __init__(self, settings=None):
        self.settings = settings
        self._conn = None
        self._connector = None
        self._connected = False

    def _load_connector(self):
        if self._connector is not None:
            return self._connector
        try:
            import collections
            import collections.abc
            if not hasattr(collections, "Mapping"):
                collections.Mapping = collections.abc.Mapping  # type: ignore[attr-defined]
            if not hasattr(collections, "MutableMapping"):
                collections.MutableMapping = collections.abc.MutableMapping  # type: ignore[attr-defined]
            import snowflake.connector  # type: ignore
            self._connector = snowflake.connector
            return self._connector
        except ImportError:
            logger.error("snowflake-connector-python not installed")
            return None

    def _connect_sync(self):
        connector = self._load_connector()
        if connector is None:
            raise RuntimeError("Snowflake connector not available")

        logger.info(
            "Connecting to Snowflake account=%s user=%s role=%s warehouse=%s",
            self.settings.snowflake_account,
            self.settings.snowflake_user,
            self.settings.snowflake_role,
            self.settings.snowflake_warehouse,
        )

        self._conn = connector.connect(
            account=self.settings.snowflake_account,
            user=self.settings.snowflake_user,
            password=self.settings.snowflake_password,
            role=self.settings.snowflake_role,
            warehouse=self.settings.snowflake_warehouse,
            database=self.settings.snowflake_database,
            schema=self.settings.snowflake_schema,
            login_timeout=30,
            network_timeout=60,
            client_session_keep_alive=True,
            ocsp_fail_open=True,
        )
        self._connected = True
        logger.info("Snowflake connection established successfully")

    def _ensure_connected(self):
        if self._connected and self._conn is not None:
            return
        self._connect_sync()

    def _query_role_sync(self, username: str) -> str:
        self._ensure_connected()
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                  CASE
                    WHEN COUNT(CASE WHEN GRANTED_ROLE_NAME = 'PLATFORM_ADMIN' THEN 1 END) > 0 THEN 'admin'
                    WHEN COUNT(CASE WHEN GRANTED_ROLE_NAME = 'PLATFORM_USER' THEN 1 END) > 0 THEN 'user'
                    ELSE 'viewer'
                  END as platform_role
                FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_USERS
                WHERE GRANTEE_NAME = UPPER(%s)
                  AND DELETED_ON IS NULL
                """,
                (username,),
            )
            row = cursor.fetchone()
            return row[0] if row else "viewer"
        finally:
            cursor.close()

    def _execute_query_sync(self, query: str) -> dict:
        self._ensure_connected()
        cursor = self._conn.cursor()
        try:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall() if columns else []
            return {
                "query_id": cursor.sfqid,
                "columns": columns,
                "rows": [list(row) for row in rows],
                "row_count": len(rows),
            }
        finally:
            cursor.close()

    async def get_user_platform_role(self, username: str) -> str:
        now = time.monotonic()
        cached = _ROLE_CACHE.get(username)
        if cached and now - cached[1] < _CACHE_TTL:
            return cached[0]

        if not self.settings or not self.settings.snowflake_account:
            logger.warning("Snowflake not configured, using stored role for %s", username)
            return "viewer"

        try:
            role = await asyncio.to_thread(self._query_role_sync, username)
            logger.info("Snowflake role for %s: %s", username, role)
        except Exception as exc:
            logger.error("Snowflake role fetch failed for %s: %s", username, exc)
            role = "viewer"

        _ROLE_CACHE[username] = (role, now)
        return role

    async def execute_query(self, query: str) -> dict:
        if not self.settings or not self.settings.snowflake_account:
            raise RuntimeError("Snowflake not configured")
        return await asyncio.to_thread(self._execute_query_sync, query)

    async def validate_credentials(self, username: str, password: str) -> bool:
        connector = self._load_connector()
        if connector is None:
            return False
        try:
            test_conn = await asyncio.to_thread(
                connector.connect,
                user=username,
                password=password,
                account=self.settings.snowflake_account,
                login_timeout=15,
            )
            await asyncio.to_thread(test_conn.close)
            return True
        except Exception:
            return False

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._connected = False
