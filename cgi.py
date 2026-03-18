"""Compatibility shim for Python 3.13+ where stdlib cgi was removed.

Required by legacy dependencies used by snowflake-connector-python 1.x.
"""

from urllib.parse import parse_qsl


def parse_header(line: str):
    """Parse a Content-type like header.

    Returns (value, params-dict), compatible with old cgi.parse_header.
    """
    if not line:
        return "", {}

    parts = [part.strip() for part in str(line).split(";")]
    key = parts[0].lower()
    params = {}

    for item in parts[1:]:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        k = k.strip().lower()
        v = v.strip().strip('"')
        params[k] = v

    # Maintain compatibility with callers that expect URL-decoded values.
    decoded = dict(parse_qsl("&".join(f"{k}={v}" for k, v in params.items())))
    if decoded:
        params.update(decoded)

    return key, params
