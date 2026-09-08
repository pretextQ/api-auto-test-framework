import os
import pytest
from api.user_api import UserApi
from core.context_manager import TestContext
from data.config_manager import ConfigManager
from utils.db_helper import DatabaseHelper
from utils.feishu_notifier import FeishuNotifier


def pytest_addoption(parser):
    parser.addoption("--env", action="store", default=os.getenv("TEST_ENV", "test"),
                     help="选择测试环境: dev/test/prod")


@pytest.fixture(scope="session")
def config(request):
    return ConfigManager(env=request.config.getoption("--env"))


@pytest.fixture(scope="session")
def api_client(config):
    """业务API对象"""
    return UserApi(
        base_url=config.get("base_url"),
        timeout=config.get("timeout"),
        retries=config.get("retries")
    )


@pytest.fixture(scope="session")
def db_helper(config):
    """数据库助手"""
    helper = DatabaseHelper(config.get_db_config())
    yield helper
    helper.close()


@pytest.fixture
def test_context():
    """function级上下文，保证用例间隔离"""
    ctx = TestContext()
    yield ctx
    ctx.clear()


def pytest_sessionfinish(session, exitstatus):
    """执行结束：汇总结果推送到飞书"""
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        return
    
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    stats = reporter.stats if reporter else {}
    passed = len(stats.get("passed", []))
    failed = len(stats.get("failed", []))
    skipped = len(stats.get("skipped", []))
    total = passed + failed + skipped + len(stats.get("error", []))
    
    failures = []
    if failed > 0:
        for report in stats.get("failed", []):
            failures.append(report.nodeid)
    
    FeishuNotifier(webhook).send_test_result(
        total=total, passed=passed, failed=failed, skipped=skipped,
        failures=failures
    )
