import pytest

from utils.jsonpath_extractor import JsonPathExtractor

pytestmark = pytest.mark.unit

DATA = {"data": {"user": {"id": 7}, "list": [1, 2]}}


class TestJsonPathExtractor:
    def test_extract_returns_all_matches(self):
        assert JsonPathExtractor.extract(DATA, "$.data.list[*]") == [1, 2]

    def test_extract_first(self):
        assert JsonPathExtractor.extract_first(DATA, "$.data.user.id") == 7

    def test_extract_first_returns_default_when_no_match(self):
        assert JsonPathExtractor.extract_first(DATA, "$.data.none", "dft") == "dft"

    def test_invalid_expr_returns_empty_list(self):
        assert JsonPathExtractor.extract(DATA, "not a jsonpath!!") == []

    def test_no_match_returns_empty_list(self):
        assert JsonPathExtractor.extract(DATA, "$.data.missing") == []

    def test_validate_compares_first_match(self):
        assert JsonPathExtractor.validate(DATA, "$.data.user.id", 7) is True
        assert JsonPathExtractor.validate(DATA, "$.data.user.id", 8) is False
