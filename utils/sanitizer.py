import re
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


MASK = "***"
DEFAULT_SENSITIVE_FIELDS = frozenset({
    "password", "passwd", "pwd", "token", "access_token", "refresh_token",
    "authorization", "proxy-authorization", "cookie", "set-cookie", "secret",
    "api_key", "apikey", "client_secret",
})

_JWT_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
)
_BEARER_PATTERN = re.compile(r"(?i)(Bearer\s+)[^\s,;]+")


def sanitize_data(value, extra_sensitive_fields=None):
    """递归复制并脱敏报告数据，不修改原对象。"""
    sensitive_fields = set(DEFAULT_SENSITIVE_FIELDS)
    if extra_sensitive_fields:
        sensitive_fields.update(str(field).lower() for field in extra_sensitive_fields)

    return _sanitize(value, sensitive_fields)


def _sanitize(value, sensitive_fields):
    if isinstance(value, Mapping):
        return {
            key: MASK if str(key).lower() in sensitive_fields else _sanitize(item, sensitive_fields)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item, sensitive_fields) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize(item, sensitive_fields) for item in value)
    if isinstance(value, str):
        value = _BEARER_PATTERN.sub(r"\1***", value)
        value = _JWT_PATTERN.sub(MASK, value)
        if "?" in value and (value.startswith(("http://", "https://", "/"))):
            parts = urlsplit(value)
            query = [
                (key, MASK if key.lower() in sensitive_fields else item)
                for key, item in parse_qsl(parts.query, keep_blank_values=True)
            ]
            value = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        return value
    return value
