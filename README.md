# 基于Pytest的微服务接口自动化测试框架

## 项目简介

这是一个完整的接口自动化测试框架，用于微服务架构下的接口回归测试与持续质量巡检。

## 技术栈

- Python 3.8+
- Pytest
- Requests
- YAML
- JSONPath
- MySQL
- Allure
- 飞书通知
- Docker

## 项目结构

```
testai/
├── api/                    # API封装层
│   ├── http_client.py      # HTTP客户端基类
│   ├── api_base.py         # 业务API基类
│   └── user_api.py         # 用户模块API
├── core/                   # 核心业务层
│   ├── data_driver.py      # 数据驱动模块
│   ├── context_manager.py  # 上下文管理模块
│   └── test_case_base.py   # 测试基类
├── data/                   # 数据管理层
│   ├── config_manager.py   # 配置管理器
│   └── data_manager.py     # 测试数据管理器
├── utils/                  # 工具类层
│   ├── jsonpath_extractor.py
│   ├── db_helper.py        # 数据库工具
│   ├── logger.py           # 日志工具
│   ├── reporter.py         # 报告工具
│   └── feishu_notifier.py  # 飞书通知
├── config/                 # 配置目录
│   ├── env_config.yaml     # 环境配置
│   └── test_data.yaml      # 测试数据
├── testcases/              # 测试用例
│   ├── conftest.py         # 公共fixture
│   ├── test_user.py        # 用户模块测试
│   └── test_order.py       # 订单模块测试
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export TEST_ENV=test
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=password
export DB_NAME=test_db
export FEISHU_WEBHOOK=https://open.feishu.cn/...
```

### 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行冒烟测试
pytest -m smoke

# 指定环境
pytest --env=dev

# 生成Allure报告
pytest --alluredir=reports/allure
allure serve reports/allure
```

### 4. Docker运行

```bash
docker-compose up -d
```

## 架构特点

1. **分层架构**：四层结构职责单一、依赖清晰
2. **数据驱动**：YAML数据与代码解耦，一条方法跑完全部用例
3. **上下文管理**：解决长链路接口动态参数依赖
4. **双重验证**：JSONPath响应断言 + MySQL落库断言
5. **工程化闭环**：Docker + CI/CD + Allure + 飞书通知

## 配置说明

### 环境配置

在 `config/env_config.yaml` 中配置多环境参数，支持环境变量注入。

### 测试数据

在 `config/test_data.yaml` 中编写测试用例数据。

### Pytest配置

在 `pytest.ini` 中配置测试路径、标记等。

## CI/CD

项目已配置GitHub Actions，支持：
- push/PR触发
- 定时执行
- Allure报告生成与部署

## 许可证

MIT
