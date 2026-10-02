import os
import time

import pytest
from api.user_api import UserApi
from core.context_manager import TestContext
from data.config_manager import ConfigManager
from utils.db_helper import DatabaseHelper
from utils.feishu_notifier import FeishuNotifier

_START_TIME = time.time()


def pytest_addoption(parser):
    parser.addoption("--env", action="store", default=os.getenv("TEST_ENV", "test"),
                     help="选择测试环境: test/dev")


@pytest.fixture(scope="session")
def config(request):
    return ConfigManager(env=request.config.getoption("--env"))


@pytest.fixture(scope="session")
def api_client(config):
    """未鉴权业务API对象"""
    return UserApi(
        base_url=config.get("base_url"),
        timeout=config.get("timeout"),
        retries=config.get("retries")
    )


@pytest.fixture(scope="session")
def chain_context():
    """session级链路上下文:承载登录后的token/user_id与下单后的order_id"""
    return TestContext()


@pytest.fixture(scope="session")
def auth_client(config, chain_context):
    """带鉴权的业务API对象

    优先复用登录用例写入链路上下文的token;单独运行后续用例时,
    通过API对象层登录完成前置造数,保证用例可独立执行。
    """
    client = UserApi(
        base_url=config.get("base_url"),
        timeout=config.get("timeout"),
        retries=config.get("retries")
    )
    token = chain_context.get("token")
    if not token:
        data = client.login("testuser", "testpass")
        token = data["token"]
        chain_context.set("token", token)
        chain_context.set("user_id", data["user_id"])
    client.set_token(token)
    return client


@pytest.fixture(scope="session")
def db_helper(config):
    """数据库助手"""
    helper = DatabaseHelper(config.get_db_config())
    yield helper
    helper.close()


@pytest.fixture(scope="session", autouse=True)
def reset_test_data(db_helper):
    """会话开始重置被测数据,保证执行结果可重复"""
    db_helper.execute_update("DELETE FROM orders")
    db_helper.execute_update("UPDATE products SET stock = 100 WHERE product_id = 1001")
    db_helper.execute_update("UPDATE products SET stock = 50 WHERE product_id = 1002")


def pytest_sessionfinish(session, exitstatus):
    """执行结束:汇总结果推送到飞书"""
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        return

    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    stats = reporter.stats if reporter else {}
    passed = len(stats.get("passed", []))
    failed = len(stats.get("failed", []))
    skipped = len(stats.get("skipped", []))
    error = len(stats.get("error", []))
    total = passed + failed + skipped + error

    failures = [report.nodeid for report in stats.get("failed", [])]

    FeishuNotifier(webhook).send_test_result(
        total=total, passed=passed, failed=failed, skipped=skipped,
        duration=round(time.time() - _START_TIME, 2),
        failures=failures
    )
