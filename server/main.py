from __future__ import annotations

import json
import logging
import threading
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import load_settings, validate_required_env
from .security import ValidationError, sanitize_error
from .snowflake_client import SnowflakeClient, SnowflakeClientUnavailableError
from .tool_registry import ToolRegistry

settings = load_settings()
logging.basicConfig(level=getattr(logging, settings.mcp_log_level.upper(), logging.INFO))
logger = logging.getLogger("snowflake-mcp")


def _configure_third_party_logging() -> None:
    level = getattr(logging, settings.snowflake_log_level.upper(), logging.ERROR)
    logging.getLogger("snowflake").setLevel(level)
    logging.getLogger("snowflake.connector").setLevel(level)
    logging.getLogger("snowflake.connector.connection").setLevel(level)
    logging.getLogger("snowflake.connector.vendored.urllib3").setLevel(level)
    logging.getLogger("snowflake.connector.vendored.urllib3.connectionpool").setLevel(level)
    logging.getLogger("urllib3.connectionpool").setLevel(level)
    logging.getLogger("botocore").setLevel(level)


_configure_third_party_logging()

app = FastAPI(title="Snowflake MCP Bridge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.mcp_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
registry = ToolRegistry(settings=settings, sf=SnowflakeClient(settings))


class ToolCallRequest(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


@app.on_event("startup")
def warmup_snowflake_connection() -> None:
    def _warmup() -> None:
        try:
            registry.sf.execute_query("SELECT 1")
            logger.info("snowflake_warmup_success")
        except Exception as exc:
            logger.warning("snowflake_warmup_failed: %s", sanitize_error(exc))

    threading.Thread(target=_warmup, daemon=True).start()


@app.get("/health")
def health() -> dict[str, Any]:
    missing = validate_required_env(settings)
    connector_ready = True
    connector_message = None
    try:
        registry.sf._load_connector()
    except SnowflakeClientUnavailableError as exc:
        connector_ready = False
        connector_message = str(exc)

    return {
        "status": "ok" if (not missing and connector_ready) else "degraded",
        "missing_env": missing,
        "sql_safety_mode": settings.sql_safety_mode,
        "snowflake_connector_ready": connector_ready,
        "snowflake_connector_message": connector_message,
    }


@app.get("/mcp/tools")
def list_tools() -> dict[str, Any]:
    tools = []
    for tool in registry.list_tools():
        tools.append(
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "outputSchema": tool.output_schema,
            }
        )
    return {"tools": tools}


@app.post("/mcp/call")
def call_tool(request: ToolCallRequest) -> dict[str, Any]:
    try:
        result = registry.run_tool(request.name, request.arguments)
        logger.info("tool_call_success name=%s", request.name)
        return {"ok": True, "name": request.name, "result": result}
    except ValidationError as exc:
        logger.warning("tool_call_validation_error name=%s error=%s", request.name, exc)
        raise HTTPException(status_code=400, detail=sanitize_error(exc)) from exc
    except Exception as exc:
        logger.exception("tool_call_failed name=%s", request.name)
        raise HTTPException(status_code=500, detail=sanitize_error(exc)) from exc


@app.get("/mcp/events")
def mcp_events() -> StreamingResponse:
    def event_stream():
        payload = {
            "event": "server_ready",
            "tools": [t.name for t in registry.list_tools()],
            "sql_safety_mode": settings.sql_safety_mode,
        }
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def run() -> None:
    uvicorn.run(
        "server.main:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=False,
        log_level=settings.mcp_log_level.lower(),
    )


if __name__ == "__main__":
    run()
