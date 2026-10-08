# 项目维护手册

> 最后更新：2026-10-07
>
> 适用分支：`main`

本文档面向后续维护者，记录项目当前事实、关键约定和变更检查项。它不是需求草稿；历史规划与后续工作见[升级路线图](升级计划书.md)。

## 1. 项目定位

这是一个可独立运行的接口自动化测试示例项目，目标是演示一条完整而可验证的工程链路：

```text
YAML 用例 → Pytest 参数化 → HTTP 请求 → 响应/业务码断言
                               └→ MySQL 落库断言
测试结果 → Allure 报告 → GitHub Pages / 飞书通知
```

仓库同时包含测试框架和被测演示服务。演示服务用于保证项目可以复现，不代表生产业务系统的完整安全设计。

## 2. 当前技术基线

| 领域 | 实现 |
|------|------|
| 语言与测试 | Python 3.11、Pytest |
| HTTP | Requests、Session、幂等请求重试 |
| 数据驱动 | YAML、收集阶段参数化 |
| 数据提取 | jsonpath-ng |
| 数据库 | MySQL 8、PyMySQL |
| 被测服务 | FastAPI、JWT |
| 报告与通知 | Allure、飞书群机器人 |
| 工程化 | Docker Compose、GitHub Actions |

当前仓库包含 6 条 YAML 数据用例、4 条 API 对象/安全边界用例和 72 条框架单元测试。

## 3. 目录职责

```text
api/             HTTP 客户端与业务 API 对象
core/            数据驱动、上下文和统一用例执行流程
data/            环境配置与 YAML 用例加载
utils/           JSONPath、数据库、日志、报告和通知工具
testcases/       需要演示服务与 MySQL 的冒烟测试
unit_tests/      不依赖外部服务的框架单元测试
config/          环境配置和测试数据
demo_app/        FastAPI 被测演示服务
docs/            设计、维护与路线图文档
```

数据库配置统一位于 `config/env_config.yaml`，项目不存在独立的 `db_config.yaml`。测试用例文件按业务模块拆分，文件名前缀只用于保持默认展示顺序，不应作为依赖管理机制。

## 4. 核心执行链路

1. `DataDriver.parametrize` 在测试收集阶段读取并过滤 YAML 用例。
2. `TestCaseBase.perform_request` 用 `TestContext` 渲染请求中的占位符。
3. `HttpClient` 发送请求，并统一应用超时和幂等方法重试策略。
4. `TestCaseBase.run_data_driven_case` 依次执行 HTTP 状态码、业务码、JSONPath 和数据库断言。
5. 成功响应可通过 `extract` 把字段写入链路上下文，供后续请求引用。
6. Pytest 会话结束后生成 Allure 结果，并在配置 Webhook 时发送飞书通知。

占位符支持 `${key}` 与 `${context.key}`。当整个字符串只有一个占位符时，渲染结果保留原始类型；嵌入普通字符串时转换为文本。

## 5. 配置约定

环境由 `--env` 或 `TEST_ENV` 选择，默认值为 `test`：

```powershell
pytest --env=test
$env:TEST_ENV = "dev"
pytest
```

连接信息优先从环境变量读取：

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `API_BASE_URL` | `http://localhost:8000` | 被测服务地址 |
| `DB_HOST` | `localhost` | MySQL 主机 |
| `DB_PORT` | `3307` | 宿主机 MySQL 端口 |
| `DB_USER` | `test_user` | 数据库用户 |
| `DB_PASSWORD` | `test_password` | 数据库密码 |
| `DB_NAME` | `test_db` | 数据库名称 |
| `JWT_SECRET` | 本地演示密钥 | 演示服务 JWT 签名；共享环境必须覆盖 |
| `FEISHU_WEBHOOK` | 空 | 飞书机器人地址；为空时不通知 |
| `FEISHU_SECRET` | 空 | 飞书加签密钥；启用机器人加签时配置 |

默认凭据只服务于本地演示，不应用于共享或生产环境。

## 6. 常用维护命令

```powershell
# 仅运行无外部依赖的单元测试
pytest -m unit

# 启动被测服务和数据库
docker compose up -d --build mysql demo-app

# 运行冒烟链路
pytest -m smoke

# 运行全部测试并输出覆盖率
pytest -m "unit or smoke" --cov=core --cov=data --cov=utils --cov-report=term-missing

# 在容器中执行测试
docker compose run --rm test-runner
```

PowerShell 中建议使用 `$env:NAME = "value"` 设置临时环境变量。CI 使用 Linux shell，环境变量语法不同。

## 7. 修改检查清单

### 新增接口

- 在 `demo_app/` 或真实被测服务中明确鉴权和业务错误语义；
- 需要流程编排时在 `api/` 增加业务 API 对象；
- 在 YAML 中增加成功、参数错误和权限错误用例；
- 对状态变化同时增加响应断言和数据库断言；
- 检查请求与响应附件是否包含密码、Token 或个人数据。

### 新增 YAML 字段

- 更新 `DataManager` 的结构校验；
- 更新 `TestCaseBase` 的执行逻辑；
- 增加单元测试，至少覆盖正常值、缺失值和非法值；
- 同步更新设计说明中的用例模型。

### 修改配置

- 保持本地、Docker Compose 和 GitHub Actions 三种运行方式一致；
- 不在仓库中提交真实凭据；
- 新环境必须显式配置，禁止默认连接生产环境。

### 提交前

```powershell
pytest -m unit
python -m compileall -q api core data demo_app testcases unit_tests utils
git diff --check
```

涉及服务、数据库或工作流的变更，还必须运行冒烟测试。

## 8. 当前已知边界

- 订单用例已实现独立造数和回收，但多 worker 共享同一个 MySQL 实例的并行隔离尚未经过集成验证。
- 演示服务已经补充资源归属校验和原子库存扣减；密码存储与默认演示密钥仍只适用于本地演示。
- Allure 附件已对内置及自定义敏感字段脱敏，但业务接入时仍需维护自定义字段列表。
- `constraints.txt` 固定直接依赖，传递依赖尚未生成完整哈希锁文件。
- Python 与 MySQL 镜像已固定 digest；升级 digest 时必须重新运行 Compose smoke 测试。

这些事项的优先级和验收条件记录在[升级路线图](升级计划书.md)。

## 9. 关键设计决策

| 决策 | 原因 |
|------|------|
| POST 默认不重试 | 避免创建订单等非幂等操作重复执行 |
| YAML 在收集阶段过滤 | 避免先生成全部组合再运行时跳过 |
| API 对象与数据驱动并存 | 分别承载流程编排和参数覆盖 |
| 数据库配置并入环境配置 | 避免多份配置漂移 |
| 内置演示服务 | 让仓库不依赖不可控的外部 API |
| 不提供生产环境默认配置 | 降低误连生产环境的风险 |

## 10. 文档维护规则

- 根目录 `README.md` 只保留用户首次运行所需内容；
- 设计变化写入设计说明，运维约定写入本文档，未来事项写入升级路线图；
- 文档中只陈述仓库能够验证的数字与能力；
- 规划项必须使用“计划”“待完成”等明确措辞，不得写成已实现能力。
