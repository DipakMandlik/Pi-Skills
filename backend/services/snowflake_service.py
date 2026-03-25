from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

logger = logging.getLogger("backend.snowflake")

_ROLE_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300

_sf_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="snowflake")


class SnowflakeService:
    def __init__(self, settings=None):
        self.settings = settings
        self._conn = None
        self._connector = None
        self._connected = False
        self._available = False

        # Suppress AWS cloud metadata probes before any Snowflake import
        if settings and getattr(settings, "suppress_cloud_metadata_probes", False):
            os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
            os.environ.setdefault("AWS_METADATA_SERVICE_TIMEOUT", "1")
            os.environ.setdefault("AWS_METADATA_SERVICE_NUM_ATTEMPTS", "1")

    def _load_connector(self):
        if self._connector is not None:
            return self._connector

        # Set OCSP bypass env vars BEFORE importing snowflake.connector
        os.environ.setdefault("DISABLE_OCSP_CHECKS", "true")
        os.environ.setdefault("SF_OCSP_INSECURE_MODE", "true")
        os.environ.setdefault("SF_OCSP_RESPONSE_CACHE_SERVER_ENABLED", "false")

        try:
            import collections
            import collections.abc
            if not hasattr(collections, "Mapping"):
                collections.Mapping = collections.abc.Mapping  # type: ignore[attr-defined]
            if not hasattr(collections, "MutableMapping"):
                collections.MutableMapping = collections.abc.MutableMapping  # type: ignore[attr-defined]
            if not hasattr(collections, "Sequence"):
                collections.Sequence = collections.abc.Sequence  # type: ignore[attr-defined]
            import snowflake.connector  # type: ignore
            self._connector = snowflake.connector
            logger.info("Snowflake connector loaded (version %s)", snowflake.connector.__version__)
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
            login_timeout=15,
            network_timeout=60,
            client_session_keep_alive=True,
            ocsp_fail_open=True,
            insecure_mode=True,
        )
        self._connected = True
        self._available = True
        logger.info("Snowflake connection established successfully")

    def _ensure_connected(self):
        if self._connected and self._conn is not None:
            return
        self._connect_sync()

    def _query_role_sync(self, username: str) -> list[str]:
        """Query Snowflake for all platform roles assigned to a user. Returns list of roles."""
        self._ensure_connected()
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                SELECT DISTINCT
                  CASE
                    WHEN ROLE IN ('ORG_ADMIN', 'PLATFORM_ADMIN')  THEN 'ORG_ADMIN'
                    WHEN ROLE = 'SECURITY_ADMIN'                   THEN 'SECURITY_ADMIN'
                    WHEN ROLE = 'DATA_ENGINEER'                    THEN 'DATA_ENGINEER'
                    WHEN ROLE = 'ANALYTICS_ENGINEER'               THEN 'ANALYTICS_ENGINEER'
                    WHEN ROLE = 'DATA_SCIENTIST'                   THEN 'DATA_SCIENTIST'
                    WHEN ROLE = 'BUSINESS_USER'                    THEN 'BUSINESS_USER'
                    WHEN ROLE IN ('VIEWER', 'PLATFORM_USER')       THEN 'VIEWER'
                    WHEN ROLE = 'SYSTEM_AGENT'                     THEN 'SYSTEM_AGENT'
                    ELSE NULL
                  END as platform_role
                FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_USERS
                WHERE GRANTEE_NAME = UPPER(%s)
                  AND DELETED_ON IS NULL
                  AND ROLE IN (
                    'ORG_ADMIN', 'PLATFORM_ADMIN', 'SECURITY_ADMIN',
                    'DATA_ENGINEER', 'ANALYTICS_ENGINEER', 'DATA_SCIENTIST',
                    'BUSINESS_USER', 'VIEWER', 'PLATFORM_USER', 'SYSTEM_AGENT'
                  )
                """,
                (username,),
            )
            rows = cursor.fetchall()
            roles = [row[0] for row in rows if row[0]]
            return roles if roles else ["VIEWER"]
        finally:
            cursor.close()

    def _query_primary_role_sync(self, username: str) -> str:
        """Query primary (highest priority) role for backward compatibility."""
        roles = self._query_role_sync(username)
        priority = ["ORG_ADMIN", "SECURITY_ADMIN", "DATA_ENGINEER", "ANALYTICS_ENGINEER",
                     "DATA_SCIENTIST", "BUSINESS_USER", "VIEWER", "SYSTEM_AGENT"]
        for p in priority:
            if p in roles:
                return p
        return "VIEWER"

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

    async def _run_with_timeout(self, func, *args, timeout: int = 20):
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(_sf_executor, func, *args)
        return await asyncio.wait_for(future, timeout=timeout)

    async def get_user_platform_role(self, username: str) -> str:
        """Get primary platform role for a user (backward compatible)."""
        now = time.monotonic()
        cached = _ROLE_CACHE.get(username)
        if cached and now - cached[1] < _CACHE_TTL:
            return cached[0]

        if not self.settings or not self.settings.snowflake_account:
            logger.warning("Snowflake not configured, using stored role for %s", username)
            return "VIEWER"

        try:
            role = await self._run_with_timeout(
                self._query_primary_role_sync, username, timeout=30
            )
            logger.info("Snowflake primary role for %s: %s", username, role)
        except (TimeoutError, FuturesTimeoutError):
            logger.error("Snowflake role fetch timed out for %s", username)
            role = "VIEWER"
        except Exception as exc:
            logger.error("Snowflake role fetch failed for %s: %s", username, exc)
            role = "VIEWER"

        _ROLE_CACHE[username] = (role, now)
        return role

    async def get_user_all_roles(self, username: str) -> list[str]:
        """Get all platform roles assigned to a user in Snowflake."""
        if not self.settings or not self.settings.snowflake_account:
            return ["VIEWER"]

        try:
            roles = await self._run_with_timeout(
                self._query_role_sync, username, timeout=30
            )
            logger.info("Snowflake roles for %s: %s", username, roles)
            return roles
        except (TimeoutError, FuturesTimeoutError):
            logger.error("Snowflake role fetch timed out for %s", username)
            return ["VIEWER"]
        except Exception as exc:
            logger.error("Snowflake role fetch failed for %s: %s", username, exc)
            return ["VIEWER"]

    async def execute_query(self, query: str) -> dict:
        if not self.settings or not self.settings.snowflake_account:
            raise RuntimeError("Snowflake not configured")
        return await self._run_with_timeout(
            self._execute_query_sync, query, timeout=60
        )

    async def validate_credentials(self, username: str, password: str) -> bool:
        connector = self._load_connector()
        if connector is None:
            return False

        def _try_connect():
            conn = connector.connect(
                user=username,
                password=password,
                account=self.settings.snowflake_account,
                login_timeout=10,
                network_timeout=15,
                insecure_mode=True,
                ocsp_fail_open=True,
            )
            conn.close()
            return True

        try:
            return await self._run_with_timeout(_try_connect, timeout=20)
        except Exception:
            return False

    def is_configured(self) -> bool:
        return bool(self.settings and self.settings.snowflake_account)

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._connected = False
