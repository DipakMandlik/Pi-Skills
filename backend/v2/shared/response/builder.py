from __future__ import annotations

from fastapi.responses import JSONResponse


def success_response(data: dict | list | None = None, meta: dict | None = None) -> JSONResponse:
    body: dict = {"success": True, "data": data if data is not None else {}}
    if meta is not None:
        body["meta"] = meta
    return JSONResponse(status_code=200, content=body)


def created_response(data: dict | list | None = None) -> JSONResponse:
    body: dict = {"success": True, "data": data if data is not None else {}}
    return JSONResponse(status_code=201, content=body)


def no_content_response() -> JSONResponse:
    return JSONResponse(status_code=204, content=None)


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[str] | None = None,
) -> JSONResponse:
    body: dict = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)
