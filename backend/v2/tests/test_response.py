from __future__ import annotations

from backend.v2.shared.response import error_response, success_response, created_response


def test_success_response_with_data():
    resp = success_response({"key": "value"})
    assert resp.status_code == 200
    body = resp.body.decode()
    assert '"success": true' in body
    assert '"key": "value"' in body


def test_success_response_with_meta():
    resp = success_response({"items": []}, {"page": 1, "total": 0})
    body = resp.body.decode()
    assert '"page": 1' in body
    assert '"total": 0' in body


def test_success_response_no_data():
    resp = success_response()
    body = resp.body.decode()
    assert '"data": {}' in body


def test_created_response():
    resp = created_response({"id": "123"})
    assert resp.status_code == 201


def test_error_response():
    resp = error_response(400, "VALIDATION_ERROR", "Invalid input", ["email required"])
    assert resp.status_code == 400
    body = resp.body.decode()
    assert '"success": false' in body
    assert '"code": "VALIDATION_ERROR"' in body
    assert '"message": "Invalid input"' in body
    assert '"email required"' in body


def test_error_response_no_details():
    resp = error_response(404, "NOT_FOUND", "Not found")
    body = resp.body.decode()
    assert '"details"' not in body
