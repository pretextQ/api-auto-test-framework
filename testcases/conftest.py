import os
import platform
import time
from pathlib import Path

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


@pytest.fixture(scope="session", autouse=True)
def allure_environment(config, request):
    """向Allure结果目录写入不含凭据的环境信息。"""
    report_dir = getattr(request.config.option, "allure_report_dir", None)
    if not report_dir:
        return
    output = Path(report_dir)
    output.mkdir(parents=True, exist_ok=True)
    properties = {
        "Environment": config.current_env,
        "API.BaseURL": config.get("base_url"),
        "Python": platform.python_version(),
        "Platform": platform.platform(),
    }
    content = "\n".join(f"{key}={value}" for key, value in properties.items()) + "\n"
    (output / "environment.properties").write_text(content, encoding="utf-8")


@pytest.fixture(scope="session")
def api_client(config):
    """未鉴权业务API对象"""
    return UserApi(
        base_url=config.get("base_url"),
        timeout=config.get("timeout"),
        retries=config.get("retries"),
        sensitive_fields=config.get("reporting.sensitive_fields", [])
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
        retries=config.get("retries"),
        sensitive_fields=config.get("reporting.sensitive_fields", [])
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


@pytest.fixture
def order_sandbox(db_helper, auth_client, chain_context):
    """隔离单条订单测试，只清理本测试创建的订单并恢复相关库存。"""
    user_id = chain_context.get("user_id")
    before_rows = db_helper.execute_query(
        "SELECT order_id FROM orders WHERE user_id = %s", (user_id,)
    )
    before_ids = {row["order_id"] for row in before_rows}
    product = db_helper.fetch_one("products", {"product_id": 1002})
    original_stock = product["stock"]
    if original_stock < 2:
        db_helper.execute_update(
            "UPDATE products SET stock = %s WHERE product_id = %s", (50, 1002)
        )

    yield

    after_rows = db_helper.execute_query(
        "SELECT order_id FROM orders WHERE user_id = %s", (user_id,)
    )
    new_ids = [row["order_id"] for row in after_rows if row["order_id"] not in before_ids]
    for order_id in new_ids:
        db_helper.execute_update("DELETE FROM orders WHERE order_id = %s", (order_id,))
    db_helper.execute_update(
        "UPDATE products SET stock = %s WHERE product_id = %s", (original_stock, 1002)
    )


@pytest.fixture
def created_order(auth_client, chain_context, order_sandbox):
    """为查询类测试创建一条可自动回收的订单。"""
    response = auth_client.post("/api/orders", json={
        "user_id": chain_context.get("user_id"),
        "product_id": 1002,
        "quantity": 2,
    })
    result = response.json()
    if response.status_code != 200 or result.get("code") != 0:
        pytest.fail(f"订单前置数据创建失败: {result}")
    return result["data"]


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
    failures.extend(report.nodeid for report in stats.get("error", []))

    FeishuNotifier(webhook, secret=os.getenv("FEISHU_SECRET")).send_test_result(
        total=total, passed=passed, failed=failed, skipped=skipped,
        errors=error,
        duration=round(time.time() - _START_TIME, 2),
        failures=failures,
        run_url=os.getenv("CI_RUN_URL"),
        report_url=os.getenv("ALLURE_REPORT_URL")
    )
