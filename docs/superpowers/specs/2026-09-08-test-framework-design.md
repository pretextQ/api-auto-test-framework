# 基于Pytest的微服务接口自动化测试框架设计文档

**项目名称**：基于Pytest的微服务接口自动化测试框架  
**设计日期**：2026-09-08  
**版本**：v1.1  
**作者**：AI助手

---

## 1. 项目概述

### 1.1 项目背景
针对微服务架构下接口数量多、手工回归效率低、接口上下文依赖复杂等问题，设计并实现基于Python + Pytest的接口自动化测试框架，用于核心业务链路的自动化回归与持续质量巡检。

### 1.2 项目目标
- 实现完整的接口自动化测试框架
- 支持数据驱动测试，提高测试用例复用性
- 解决接口间的数据依赖问题
- 提供详细的测试报告和实时通知
- 支持Docker容器化和CI/CD集成

### 1.3 技术选型
- **编程语言**：Python 3.8+
- **测试框架**：Pytest
- **HTTP客户端**：Requests
- **数据驱动**：YAML
- **数据提取**：JSONPath
- **数据库**：MySQL
- **测试报告**：Allure
- **消息通知**：飞书机器人
- **容器化**：Docker
- **CI/CD**：Jenkins/GitHub Actions

---

## 2. 架构设计

### 2.1 整体架构
采用标准分层架构，分为四层：
1. **API封装层**（api/）：封装HTTP请求与业务接口，提供统一调用方式
2. **核心业务层**（core/）：数据驱动、上下文管理、断言助手等测试能力
3. **数据管理层**（data/）：环境配置、测试数据的管理与访问
4. **工具类层**（utils/）：JSONPath、数据库、日志、Allure报告、飞书通知等通用能力

### 2.2 数据流
```
YAML 测试数据(数据驱动) → 测试用例 → API封装层 → 被测微服务
        │                    │
        │              上下文管理(fixture)
        │                    │
        └──► 核心业务层断言 ◄─┘
                 │
         工具类层(JSONPath / MySQL 双校验)
                 │
          Allure报告 + 飞书通知
```

### 2.3 职责边界（重要约定）
为避免模块职责重复，明确以下归属：
- **数据库访问只保留一处**：`utils/db_helper.py`，供用例及断言使用；`data/` 层不再包含数据库管理器，只负责配置与测试数据。
- **YAML 文件读取只保留一处**：`data/data_manager.py` 负责读取测试数据文件并检索用例；`core/data_driver.py` 负责把用例转换为 pytest 参数（模板渲染、参数化），不再重复实现 YAML 加载。
- **用例生命周期不写在测试基类里**：前置/后置统一由 pytest fixture 承担，测试基类只提供断言方法（详见 3.3.3）。

### 2.4 设计原则
- **单一职责**：每个模块只负责一个功能
- **依赖倒置**：高层模块依赖抽象，不依赖具体实现
- **接口隔离**：通过清晰的方法签名解耦模块
- **开闭原则**：对扩展开放，对修改关闭

---

## 3. 模块详细设计

### 3.1 项目目录结构
```
testai/
├── api/                        # API封装层
│   ├── __init__.py
│   ├── http_client.py          # HTTP客户端（Requests 封装）
│   ├── api_base.py             # 业务API基类（鉴权、统一响应处理）
│   └── user_api.py             # 业务API示例：用户模块
├── core/                       # 核心业务层
│   ├── __init__.py
│   ├── data_driver.py          # 数据驱动：模板渲染 + pytest 参数化
│   ├── context_manager.py      # 上下文管理：接口间数据传递
│   └── test_case_base.py       # 断言助手基类（无生命周期方法）
├── data/                       # 数据管理层
│   ├── __init__.py
│   ├── config_manager.py       # 配置管理器（多环境）
│   └── data_manager.py         # 测试数据管理器（YAML 读取/检索）
├── utils/                      # 工具类层
│   ├── __init__.py
│   ├── jsonpath_extractor.py   # JSONPath 数据提取与校验
│   ├── db_helper.py            # MySQL 数据库工具（唯一DB入口）
│   ├── logger.py               # 日志工具
│   ├── reporter.py             # Allure 报告封装
│   └── feishu_notifier.py      # 飞书通知
├── config/                     # 配置目录
│   ├── env_config.yaml         # 多环境配置（含各环境数据库连接）
│   └── test_data.yaml          # 测试用例数据
├── testcases/                  # 测试用例目录
│   ├── conftest.py             # 公共fixture
│   ├── test_user.py            # 用户模块测试
│   ├── test_order.py           # 订单模块测试
│   ├── test_product.py         # 商品模块测试
│   └── test_payment.py         # 支付模块测试
├── reports/                    # 测试报告目录
│   └── allure/                 # Allure 结果目录
├── logs/                       # 日志目录
├── docs/                       # 项目文档
│   └── superpowers/specs/      # 设计文档
├── requirements.txt            # Python依赖
├── pytest.ini                  # Pytest配置
├── Dockerfile                  # Docker配置
├── docker-compose.yml          # Docker Compose配置
└── README.md                   # 项目说明
```

### 3.2 API封装层设计

#### 3.2.1 HttpClient类（api/http_client.py）
**职责**：基于 Requests 提供统一的 HTTP 请求能力。

**核心功能**：
- 统一管理 base_url、默认请求头、超时、重试
- 提供 get/post/put/delete 便捷方法
- 请求异常捕获与日志记录

**接口设计**：
```python
class HttpClient:
    def __init__(self, base_url: str, timeout: int = 30,
                 retries: int = 3, headers: dict | None = None):
        """初始化HTTP客户端"""
        self.session = requests.Session()
        self.base_url = base_url.rstrip("/")

    def get(self, url: str, params: dict | None = None, **kwargs) -> requests.Response: ...
    def post(self, url: str, data=None, json=None, **kwargs) -> requests.Response: ...
    def put(self, url: str, data=None, json=None, **kwargs) -> requests.Response: ...
    def delete(self, url: str, **kwargs) -> requests.Response: ...

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """统一请求入口：拼接完整URL、超时/重试、异常处理、日志"""
        ...
```

#### 3.2.2 ApiBase与业务API类
**职责**：业务接口的二次封装基类。测试中直接操作业务 API 对象而非裸 HttpClient，提高可读性。鉴权 token 由 fixture 注入。

**设计说明**：各业务模块在 `api/` 下派生自己的 API 类（如 `user_api.py`），把接口方法与业务语义一一对应。这里不使用"链式调用"，仅做清晰的继承分层。

```python
class ApiBase(HttpClient):
    """业务API基类：负责鉴权头注入与通用响应处理"""
    def __init__(self, base_url: str, token: str | None = None, **kwargs):
        super().__init__(base_url, **kwargs)
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _check_response(self, resp: requests.Response) -> dict:
        """统一处理业务码：非0抛出异常，返回 data 段"""
        ...

# 业务API示例 api/user_api.py
class UserApi(ApiBase):
    def login(self, username: str, password: str) -> dict:
        return self.post("/api/login", json={"username": username, "password": password}).json()

    def get_profile(self, user_id: int) -> dict:
        return self.get(f"/api/users/{user_id}").json()
```

### 3.3 核心业务层设计

#### 3.3.1 数据驱动模块（core/data_driver.py）
**职责**：把 YAML 中的用例数据转换为 pytest 参数，实现真正的数据驱动。

**核心功能**：
- 读取用例文件（委托 DataManager）并参数化
- 模板渲染：支持 `${context.key}` 引用上下文/运行时值
- 用例ID作为 pytest 参数 id，便于 Allure 报告区分

**接口设计**：
```python
class DataDriver:
    @classmethod
    def parametrize(cls, data_file: str):
        """装饰器：从 YAML 读取全部用例并注入参数 case

        用法：
            @DataDriver.parametrize("config/test_data.yaml")
            def test_login(self, case): ...
        """
        cases = DataManager(data_file).get_test_cases()
        return pytest.mark.parametrize(
            "case", cases,
            ids=[c["case_id"] for c in cases]
        )

    @staticmethod
    def render(value, context: dict):
        """递归渲染模板字符串，支持 ${key} 与 ${context.key}"""
        ...
```
> 数据文件读取只发生在 `data_manager.py`；本模块不自行加载 YAML，避免职责重复。

#### 3.3.2 上下文管理模块（core/context_manager.py）
**职责**：解决长链路接口间的动态参数依赖。

**核心功能**：
- 每个用例分配独立的 function 级上下文（fixture 提供）
- 用例 A 登录后把 token/user_id 写入上下文，用例 B 通过 `${...}` 读取
- 支持按 key 覆盖与清理

**接口设计**：
```python
class TestContext:
    def set(self, key: str, value): ...          # 写入上下文
    def get(self, key: str, default=None): ...   # 读取上下文
    def render(self, template): ...              # 渲染含 ${key} 的模板
    def clear(self): ...
```

#### 3.3.3 测试基类（core/test_case_base.py）
**职责**：聚合常用断言方法，供用例复用。

**重要约定**：本类**不定义 setup/teardown**（unittest 风格与 pytest fixture 体系冲突）。用例前置/后置统一通过 conftest 的 fixture 完成，本类只做断言封装。

**接口设计**：
```python
class TestCaseBase:
    """断言助手基类：仅聚合断言，不含生命周期钩子"""

    @staticmethod
    def assert_status_code(resp, expected: int = 200): ...
        # 断言 HTTP 状态码，失败时附加响应体便于排查

    @staticmethod
    def assert_jsonpath(data, expr: str, expected) -> list:
        """JSONPath 断言：提取结果与期望比对，返回命中列表"""
        ...

    @staticmethod
    def assert_database(db_helper, table: str, conditions: dict, expected: dict):
        """DB 校验：按 conditions 查库并与 expected 逐字段比对"""
        ...
```

### 3.4 数据管理层设计

#### 3.4.1 配置管理模块（data/config_manager.py）
**职责**：加载 `env_config.yaml`，按 `--env`（或环境变量 `TEST_ENV`）选取环境，提供统一的取值入口。

**核心功能**：
- 自动合并 `common` 段与所选环境的配置
- 支持环境变量占位符 `${DB_USER}` 解析
- 暴露当前环境名，便于日志与报告标注

**接口设计**：
```python
class ConfigManager:
    def __init__(self, env: str | None = None):
        """env 为空时读取环境变量 TEST_ENV，默认 test"""
        self._env = env or os.getenv("TEST_ENV", "test")
        self._config = self._load()      # 合并 common + environments.<env>

    @property
    def current_env(self) -> str: ...

    def get(self, key: str, default=None):
        """取当前环境配置项，如 config.get('base_url')"""
        ...

    def get_db_config(self) -> dict:
        """返回当前环境的 database 配置（已解析环境变量占位符）"""
        ...
```

#### 3.4.2 测试数据模块（data/data_manager.py）
**职责**：YAML 测试数据文件的**唯一读取入口**。

**核心功能**：
- 加载 YAML，校验基础结构（case_id、request 必填）
- 支持按 case_id 检索单个用例 / 返回全部用例
- 供 DataDriver 参数化使用

**接口设计**：
```python
class DataManager:
    def __init__(self, data_file: str):
        self.cases = self._load(data_file)

    def get_test_cases(self) -> list[dict]: ...   # 返回全部用例
    def get_test_data(self, case_id: str) -> dict: ...  # 按ID取用例，不存在则报错
```

### 3.5 工具类层设计

#### 3.5.1 JSONPath工具（utils/jsonpath_extractor.py）
**职责**：基于 `jsonpath-ng` 提供数据提取与校验。

```python
class JsonPathExtractor:
    @staticmethod
    def extract(data, expr: str) -> list:
        """提取所有命中的值"""
        ...
    @staticmethod
    def extract_first(data, expr: str, default=None): ...
    @staticmethod
    def validate(data, expr: str, expected) -> bool:
        """断言表达式命中值与期望一致"""
        ...
```

#### 3.5.2 数据库工具（utils/db_helper.py）【全项目唯一DB入口】
**职责**：封装 MySQL 连接与常用数据校验。

**核心功能**：
- 惰性创建连接、随 fixture 释放
- 参数化 SQL，防注入
- 提供表级数据校验，供 `assert_database` 使用

**接口设计**：
```python
class DatabaseHelper:
    def __init__(self, db_config: dict): ...

    def execute_query(self, sql: str, params: tuple = ()) -> tuple:
        """执行查询，返回行元组列表"""
        ...

    def execute_update(self, sql: str, params: tuple = ()) -> int: ...
    def fetch_one(self, table, conditions: dict) -> dict | None: ...
    def validate(self, table, conditions: dict, expected: dict) -> bool: ...
    def close(self): ...
```

#### 3.5.3 日志工具（utils/logger.py）
统一日志格式，同时输出控制台与 `logs/` 文件，日志级别取自配置。

```python
class Logger:
    def __init__(self, name: str, log_file: str | None = None): ...
    def info(self, message): ...
    def error(self, message): ...
    def debug(self, message): ...
    @staticmethod
    def get_logger(name: str) -> logging.Logger: ...   # 模块级便捷获取
```

#### 3.5.4 报告工具（utils/reporter.py）
**职责**：对 Allure 的轻量封装，统一用例中附件/步骤的写法，避免用例直接散落 allure 调用。

```python
class Reporter:
    @staticmethod
    def step(title: str):        # 上下文管理器，如 with Reporter.step("登录"):
        ...
    @staticmethod
    def attach_text(name: str, content: str): ...
    @staticmethod
    def attach_json(name: str, data): ...      # 请求/响应JSON 记录到报告
    @staticmethod
    def attach_log_file(path: str): ...
```

#### 3.5.5 飞书通知（utils/feishu_notifier.py）
**职责**：把测试执行结果推送到飞书群机器人。

**接入点**：不侵入单个用例，而是在 conftest 的 `pytest_sessionfinish` 钩子中统一发送（见 5.3），失败明细附带失败用例与异常摘要。

```python
class FeishuNotifier:
    def __init__(self, webhook_url: str, secret: str | None = None):
        """支持加签机器人：secret 可选"""
        ...

    def send_test_result(self, total: int, passed: int, failed: int,
                         skipped: int, duration: float | None = None, failures: list | None = None):
        """组装卡片消息并推送，失败>0 时附带失败用例列表"""
        ...
```

---

## 4. 配置文件设计

### 4.1 环境配置（config/env_config.yaml）
数据库连接**统一收编在环境配置内**（不再单独维护 db_config.yaml），保证一处修改全局生效；敏感值用 `${ENV_VAR}` 占位，由 ConfigManager 解析。

```yaml
# 通用配置（所有环境共享）
common:
  timeout: 30
  retries: 3
  log_level: "INFO"

environments:
  dev:
    base_url: "http://dev-api.example.com"
    database:
      host: "dev-mysql.example.com"
      port: 3306
      user: "${DB_USER}"
      password: "${DB_PASSWORD}"
      name: "dev_db"
      charset: "utf8mb4"

  test:
    base_url: "http://test-api.example.com"
    database:
      host: "${DB_HOST}"            # 默认指向测试库，可被环境变量覆盖
      port: 3306
      user: "${DB_USER}"
      password: "${DB_PASSWORD}"
      name: "${DB_NAME}"
      charset: "utf8mb4"

  prod:
    base_url: "http://api.example.com"
    database:
      host: "prod-mysql.example.com"
      port: 3306
      user: "${DB_USER}"
      password: "${DB_PASSWORD}"
      name: "prod_db"
      charset: "utf8mb4"
```

### 4.2 测试数据（config/test_data.yaml）
```yaml
test_cases:
  - case_id: "TC001"
    name: "用户登录测试"
    feature: "用户模块"
    story: "用户登录"
    request:
      method: "POST"
      url: "/api/login"
      data:
        username: "testuser"
        password: "testpass"
    expected:
      status_code: 200
    validation:
      jsonpath:
        expr: "$.data.token"
        value: "${TMP_TOKEN}"          # 该用例首个运行时可留空校验非空，或由前置接口注入
      database:
        table: "users"
        conditions:
          username: "testuser"
        expected:
          status: "active"
```

### 4.3 Pytest配置（pytest.ini）
```ini
[pytest]
testpaths = testcases
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --alluredir=reports/allure --env=test
markers =
    smoke: 冒烟测试
    regression: 回归测试
```

### 4.4 Python依赖（requirements.txt）
仅保留实际使用依赖；pytest-html / pytest-ordering 等未使用项不再引入。
```
# 核心依赖
pytest>=7.0.0
requests>=2.28.0
PyYAML>=6.0
jsonpath-ng>=1.5.0
PyMySQL>=1.0.0
allure-pytest>=2.13.2

# 可选（CI 并行提速 / 随机顺序）
pytest-xdist>=3.0.0
pytest-random-order>=1.1.0
```

---

## 5. 测试用例设计

### 5.1 用例文件按业务模块划分（与 3.1 目录一致）
```
testcases/
├── conftest.py              # 公共fixture
├── test_user.py             # 用户模块
├── test_order.py            # 订单模块
├── test_product.py          # 商品模块
└── test_payment.py          # 支付模块
```

### 5.2 数据驱动用例编写规范（核心示例）
用例**全部来自 YAML**，一个 `@DataDriver.parametrize` 即可跑完该文件内所有用例，真正实现数据与代码解耦。

```python
import allure
from core.data_driver import DataDriver
from core.test_case_base import TestCaseBase


@allure.feature("用户模块")
@allure.story("用户登录")
class TestUserLogin(TestCaseBase):

    @DataDriver.parametrize("config/test_data.yaml")
    @pytest.mark.smoke
    def test_login(self, api_client, db_helper, case):
        """YAML 数据驱动：一条方法 = N 条用例"""
        request = case["request"]
        expected = case["expected"]
        validation = case.get("validation", {})

        with allure.step("发送登录请求"):
            resp = api_client.post(request["url"], json=request["data"])

        with allure.step("校验 HTTP 状态码"):
            self.assert_status_code(resp, expected["status_code"])

        with allure.step("校验响应数据"):
            jp = validation["jsonpath"]
            self.assert_jsonpath(resp.json(), jp["expr"], jp["value"])

        with allure.step("校验数据库落库"):
            db = validation["database"]
            self.assert_database(db_helper, db["table"], db["conditions"], db["expected"])
```

**长链路依赖示例**（解决"登录拿 token → 下单"的上下文问题）：
```python
def test_order_flow(self, api_client, test_context, case):
    # 前置用例已把 token 写入 test_context
    user_id = test_context.get("user_id")
    order = api_client.post("/api/orders", json={"user_id": user_id, ...})
    assert order.status_code == 200
    test_context.set("order_id", order.json()["data"]["order_id"])   # 供后续用例使用
```

### 5.3 conftest.py（公共 fixture + 环境切换 + 飞书通知钩子）
环境通过 `--env` 参数或 `TEST_ENV` 环境变量切换，不再硬编码。

```python
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
    """业务API对象：UserApi 由 ApiBase 派生，按环境注入 base_url"""
    return UserApi(base_url=config.get("base_url"),
                   timeout=config.get("timeout"),
                   retries=config.get("retries"))


@pytest.fixture(scope="session")
def db_helper(config):
    helper = DatabaseHelper(config.get_db_config())
    yield helper
    helper.close()


@pytest.fixture
def test_context():
    """function 级上下文，保证用例间隔离"""
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
    FeishuNotifier(webhook).send_test_result(
        total=total, passed=passed, failed=failed, skipped=skipped
    )
```

---

## 6. 部署与配置设计

### 6.1 Docker配置

#### 6.1.1 Dockerfile
```dockerfile
# 基础镜像
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖（PyMySQL 为纯Python，无需编译；此处仅保留通用工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p reports/allure logs

ENV PYTHONPATH=/app
ENV TEST_ENV=test

# 运行测试（环境由 TEST_ENV 注入，报告输出到 reports/allure）
CMD ["pytest", "-m", "smoke"]
```

#### 6.1.2 docker-compose.yml
```yaml
version: '3.8'

services:
  test-runner:
    build: .
    volumes:
      - ./reports:/app/reports
      - ./logs:/app/logs
    environment:
      - TEST_ENV=${TEST_ENV:-test}
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_USER=test_user
      - DB_PASSWORD=test_password
      - DB_NAME=test_db
      - FEISHU_WEBHOOK=${FEISHU_WEBHOOK}      # 从宿主机环境变量透传
    depends_on:
      - mysql
    networks: [test-network]

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=test_db
      - MYSQL_USER=test_user
      - MYSQL_PASSWORD=test_password
    ports: ["3306:3306"]
    volumes:
      - mysql_data:/var/lib/mysql
    networks: [test-network]

volumes:
  mysql_data:

networks:
  test-network:
    driver: bridge
```
> Allure 结果由 test-runner 挂载的 `./reports/allure` 落盘，再由宿主机侧的 `allure serve` 或 CI 上传工具生成 HTML 报告。

### 6.2 CI/CD集成（.github/workflows/test.yml）
```yaml
name: 自动化测试

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 8 * * 1-5'    # 工作日每天8点(UTC)执行

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.9'

      - name: 安装依赖
        run: |
          pip install -U pip
          pip install -r requirements.txt

      - name: 运行测试
        env:
          TEST_ENV: test
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          DB_NAME: ${{ secrets.DB_NAME }}
          FEISHU_WEBHOOK: ${{ secrets.FEISHU_WEBHOOK }}
        run: pytest --alluredir=reports/allure

      - name: 生成 Allure 报告
        uses: simple-elf/allure-report-action@master
        if: always()
        with:
          allure_results: reports/allure

      - name: 部署报告到 Github Pages
        if: always()
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_branch: gh-pages
          publish_dir: allure-history
```

---

## 7. 项目总结

### 7.1 技术亮点
1. **分层架构**：四层结构职责单一、依赖清晰；DB 与 YAML 读取**单点收敛**，无重复实现
2. **数据驱动**：一条方法经 `@DataDriver.parametrize` 跑完文件内全部用例，数据与代码彻底解耦
3. **上下文管理**：function 级 fixture 提供用例上下文，解决长链路接口动态参数依赖
4. **双重验证**：JSONPath 响应断言 + MySQL 落库断言，双维度验证数据一致性
5. **工程化闭环**：Docker 容器化 + CI 定时执行 + Allure 报告 + 飞书通知

### 7.2 代码规模
- 核心代码量：约 800~1000 行
- 业务API示例 + 核心模块：8 个
- 数据驱动用例示例：10+（YAML 中按需扩展）
- 配置文件：5 个

### 7.3 实施计划
1. **第一阶段**：搭建目录与基础环境（requirements / pytest.ini / env_config.yaml / logger）
2. **第二阶段**：API层（HttpClient → ApiBase → UserApi）
3. **第三阶段**：核心层与数据层（ConfigManager / DataManager / DataDriver / TestContext / TestCaseBase）
4. **第四阶段**：工具层（JsonPathExtractor / DatabaseHelper / Reporter / FeishuNotifier）
5. **第五阶段**：用例与 fixture（conftest.py + 4 个模块用例 + YAML 数据）
6. **第六阶段**：工程化（Docker / CI / README）

---

## 8. 附录

### 8.1 参考文档
- Pytest：https://docs.pytest.org/
- Requests：https://requests.readthedocs.io/
- Allure：https://docs.qameta.io/allure/
- JSONPath：https://goessner.net/articles/JsonPath/
- 飞书自定义机器人：https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot

### 8.2 版本历史
- **v1.0**（2026-09-08）：初版
- **v1.1**（2026-09-08）：审查修复
  - 移除 data/db_manager.py 与 utils/db_helper.py 的重复职责，DB 访问收敛到 db_helper.py
  - 移除 DataDriver.load_yaml 与 DataManager 的重复，YAML 读取收敛到 data_manager.py
  - 飞书通知落位 utils/feishu_notifier.py，并说明 conftest 钩子接入方式
  - 测试用例基类去除 setup/teardown（unittest 风格），改为纯断言助手，生命周期由 fixture 承担
  - 用例示例改为真正数据驱动（@DataDriver.parametrize），覆盖 Allure 步骤与 DB 校验
  - 配置统一：删除独立 db_config.yaml，数据库连接并入 env_config.yaml；新增 --env/TEST_ENV 环境切换
  - 清理 ApiBase"链式调用"描述并给出 UserApi 派生示例；精简未使用依赖
