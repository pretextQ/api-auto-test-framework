import os
import re
import yaml
from pathlib import Path
from utils.logger import Logger

# 环境变量占位符:支持 ${VAR} 与 ${VAR:默认值}
ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)(?::([^}]*))?\}")


class ConfigManager:
    """配置管理器:加载env_config.yaml,按环境选取配置"""

    def __init__(self, env: str = None, config_path: str = None):
        """
        初始化配置管理器

        Args:
            env: 环境名称,为空时读取环境变量TEST_ENV,默认test
            config_path: 配置文件路径,为空时使用项目默认路径(便于单测注入)
        """
        self._env = env or os.getenv("TEST_ENV", "test")
        self.logger = Logger.get_logger(self.__class__.__name__)
        if config_path:
            self._config_path = Path(config_path)
        else:
            self._config_path = Path(__file__).parent.parent / "config" / "env_config.yaml"
        self._config = self._load()

    @property
    def current_env(self) -> str:
        """当前环境名称"""
        return self._env

    def _load(self) -> dict:
        """加载并合并配置"""
        if not self._config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self._config_path}")

        with open(self._config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

        common_config = raw_config.get("common", {})
        env_config = raw_config.get("environments", {}).get(self._env, {})

        if not env_config:
            raise ValueError(f"环境 '{self._env}' 配置不存在")

        merged = {**common_config, **env_config}
        resolved = self._resolve_env_vars(merged)

        self.logger.info(f"已加载环境配置: {self._env}")
        return resolved

    def _resolve_env_vars(self, config: dict) -> dict:
        """解析配置中的环境变量占位符"""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, dict):
                resolved[key] = self._resolve_env_vars(value)
            elif isinstance(value, str):
                resolved[key] = self._replace_env_var(value)
            else:
                resolved[key] = value
        return resolved

    def _replace_env_var(self, value: str) -> str:
        """替换字符串中的环境变量占位符,未设置时使用默认值"""
        def replacer(match):
            var_name, default = match.group(1), match.group(2)
            env_value = os.getenv(var_name)
            if env_value:
                return env_value
            if default is not None:
                return default
            self.logger.warning(f"环境变量 {var_name} 未设置且无默认值")
            return ""

        return ENV_VAR_PATTERN.sub(replacer, value)

    def get(self, key: str, default=None):
        """
        获取配置项

        Args:
            key: 配置键名,支持点号分隔的层级访问
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def get_db_config(self) -> dict:
        """获取数据库配置"""
        db_config = self.get("database", {})
        if not db_config:
            raise ValueError("数据库配置不存在")
        return db_config
