from __future__ import annotations

from backend.v2.shared.utils import generate_id, sanitize_string, safe_json_dumps, safe_json_loads


def test_generate_id_is_uuid():
    import uuid
    id_val = generate_id()
    uuid.UUID(id_val)


def test_generate_id_unique():
    assert generate_id() != generate_id()


def test_sanitize_string_strips():
    assert sanitize_string("  hello  ") == "hello"


def test_sanitize_string_truncates():
    long_string = "a" * 6000
    result = sanitize_string(long_string)
    assert len(result) == 5000


def test_safe_json_dumps():
    assert safe_json_dumps({"key": "value"}) == '{"key": "value"}'


def test_safe_json_loads():
    assert safe_json_loads('{"key": "value"}') == {"key": "value"}


def test_safe_json_roundtrip():
    original = {"nested": {"list": [1, 2, 3]}}
    assert safe_json_loads(safe_json_dumps(original)) == original
