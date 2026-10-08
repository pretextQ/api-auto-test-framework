import pytest

from utils.sanitizer import MASK, sanitize_data


pytestmark = pytest.mark.unit


def test_recursively_masks_default_sensitive_fields_without_mutating_source():
    source = {
        "username": "alice",
        "password": "plain-text",
        "nested": [{"token": "secret-token", "value": 1}],
        "Authorization": "Bearer abc.def.ghi",
    }

    result = sanitize_data(source)

    assert result == {
        "username": "alice",
        "password": MASK,
        "nested": [{"token": MASK, "value": 1}],
        "Authorization": MASK,
    }
    assert source["password"] == "plain-text"


def test_masks_custom_field_case_insensitively():
    assert sanitize_data({"ID_CARD": "123"}, ["id_card"]) == {"ID_CARD": MASK}


def test_masks_jwt_and_bearer_values_embedded_in_text():
    value = "token=eyJabc.def.ghi Authorization: Bearer opaque-token"
    sanitized = sanitize_data(value)
    assert "eyJabc.def.ghi" not in sanitized
    assert "opaque-token" not in sanitized


def test_preserves_non_sensitive_values_and_tuple_shape():
    assert sanitize_data((1, {"name": "demo"})) == (1, {"name": "demo"})


def test_masks_sensitive_query_parameters_in_urls():
    result = sanitize_data("https://example.test/callback?token=plain&state=ok")
    assert "plain" not in result
    assert "token=%2A%2A%2A" in result
    assert "state=ok" in result
