import pytest

from data.config_manager import ConfigManager

pytestmark = pytest.mark.unit

CONFIG_YAML = """
common:
  timeout: 10
environments:
  test:
    base_url: "http://localhost:8000"
    token: "${TEST_TOKEN:default-token}"
    password: "${TEST_PASSWORD}"
  prod:
    base_url: "http://prod.example.com"
"""


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "env_config.yaml"
    path.write_text(CONFIG_YAML, encoding="utf-8")
    return str(path)


class TestConfigManager:
    def test_merges_common_and_env_sections(self, config_file):
        cfg = ConfigManager(env="test", config_path=config_file)
        assert cfg.get("timeout") == 10
        assert cfg.get("base_url") == "http://localhost:8000"

    def test_env_var_default_used_when_missing(self, config_file, monkeypatch):
        monkeypatch.delenv("TEST_TOKEN", raising=False)
        cfg = ConfigManager(env="test", config_path=config_file)
        assert cfg.get("token") == "default-token"

    def test_env_var_used_when_set(self, config_file, monkeypatch):
        monkeypatch.setenv("TEST_TOKEN", "real-token")
        cfg = ConfigManager(env="test", config_path=config_file)
        assert cfg.get("token") == "real-token"

    def test_missing_var_without_default_resolves_to_empty(self, config_file, monkeypatch):
        monkeypatch.delenv("TEST_PASSWORD", raising=False)
        cfg = ConfigManager(env="test", config_path=config_file)
        assert cfg.get("password") == ""

    def test_unknown_env_raises(self, config_file):
        with pytest.raises(ValueError):
            ConfigManager(env="uat", config_path=config_file)

    def test_missing_config_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ConfigManager(env="test", config_path=str(tmp_path / "nope.yaml"))

    def test_get_nested_key_returns_default_when_absent(self, config_file):
        cfg = ConfigManager(env="test", config_path=config_file)
        assert cfg.get("database.host", "1.2.3.4") == "1.2.3.4"

    def test_current_env_recorded(self, config_file):
        assert ConfigManager(env="prod", config_path=config_file).current_env == "prod"
