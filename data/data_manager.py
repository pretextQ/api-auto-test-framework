import yaml
from pathlib import Path
from utils.logger import Logger


ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class DataManager:
    """测试数据管理器:YAML测试数据文件的唯一读取入口"""

    def __init__(self, data_file: str):
        """
        初始化数据管理器

        Args:
            data_file: 数据文件路径(相对于项目根目录)
        """
        self.logger = Logger.get_logger(self.__class__.__name__)
        self.cases = self._load(data_file)

    def _load(self, data_file: str) -> list:
        """加载YAML数据文件"""
        file_path = Path(__file__).parent.parent / data_file

        if not file_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not isinstance(data, dict):
            raise ValueError("测试数据根节点必须是对象")
        cases = data.get("test_cases", [])
        if not isinstance(cases, list):
            raise ValueError("test_cases 必须是列表")
        self._validate_cases(cases)
        self.logger.info(f"已加载 {len(cases)} 条测试用例")

        return cases

    def _validate_cases(self, cases: list):
        """校验用例结构，并一次性报告全部错误。"""
        errors = []
        seen_ids = set()
        for i, case in enumerate(cases):
            location = f"用例[{i}]"
            if not isinstance(case, dict):
                errors.append(f"{location} 必须是对象")
                continue

            case_id = case.get("case_id")
            if not isinstance(case_id, str) or not case_id.strip():
                errors.append(f"{location} 缺少有效的 case_id")
                case_id = str(case_id or i)
            elif case_id in seen_ids:
                errors.append(f"用例 {case_id} 的 case_id 重复")
            else:
                seen_ids.add(case_id)

            request = case.get("request")
            if not isinstance(request, dict):
                errors.append(f"用例 {case_id} 缺少有效的 request 对象")
            else:
                method = request.get("method")
                if not isinstance(method, str) or method.upper() not in ALLOWED_METHODS:
                    errors.append(f"用例 {case_id} 的 request.method 无效: {method}")
                url = request.get("url")
                if not isinstance(url, str) or not url.strip():
                    errors.append(f"用例 {case_id} 缺少有效的 request.url")

            expected = case.get("expected")
            if not isinstance(expected, dict):
                errors.append(f"用例 {case_id} 缺少有效的 expected 对象")
            elif not isinstance(expected.get("status_code"), int):
                errors.append(f"用例 {case_id} 缺少整数 expected.status_code")

            validation = case.get("validation", {})
            if not isinstance(validation, dict):
                errors.append(f"用例 {case_id} 的 validation 必须是对象")
                continue

            jsonpath = validation.get("jsonpath")
            if jsonpath is not None:
                specs = jsonpath if isinstance(jsonpath, list) else [jsonpath]
                if not specs:
                    errors.append(f"用例 {case_id} 的 validation.jsonpath 不能为空列表")
                for spec in specs:
                    if (
                        not isinstance(spec, dict)
                        or not isinstance(spec.get("expr"), str)
                        or not spec["expr"].strip()
                    ):
                        errors.append(f"用例 {case_id} 的 validation.jsonpath 缺少有效 expr")

            response_time_ms = validation.get("response_time_ms")
            if response_time_ms is not None and (
                not isinstance(response_time_ms, (int, float)) or response_time_ms <= 0
            ):
                errors.append(f"用例 {case_id} 的 validation.response_time_ms 必须为正数")

            database = validation.get("database")
            if database is not None:
                if not isinstance(database, dict):
                    errors.append(f"用例 {case_id} 的 validation.database 必须是对象")
                else:
                    for key in ("table", "conditions", "expected"):
                        if key not in database:
                            errors.append(f"用例 {case_id} 的 validation.database 缺少 {key}")
                    if "conditions" in database and not isinstance(database["conditions"], dict):
                        errors.append(f"用例 {case_id} 的 database.conditions 必须是对象")
                    if "expected" in database and not isinstance(database["expected"], dict):
                        errors.append(f"用例 {case_id} 的 database.expected 必须是对象")

            extract = case.get("extract")
            if extract is not None and (
                not isinstance(extract, dict)
                or not all(isinstance(k, str) and isinstance(v, str) for k, v in extract.items())
            ):
                errors.append(f"用例 {case_id} 的 extract 必须是字符串映射")

        if errors:
            details = "\n- ".join(errors)
            raise ValueError(f"测试数据校验失败:\n- {details}")

    def get_test_cases(self, feature: str = None, story: str = None) -> list:
        """
        获取用例列表,支持按模块/故事过滤

        Args:
            feature: 按模块过滤,为空时不过滤
            story: 按故事过滤,为空时不过滤

        Returns:
            过滤后的用例列表
        """
        result = self.cases
        if feature is not None:
            result = [c for c in result if c.get("feature") == feature]
        if story is not None:
            result = [c for c in result if c.get("story") == story]
        return result

    def get_test_data(self, case_id: str) -> dict:
        """
        按case_id获取用例

        Args:
            case_id: 用例ID

        Returns:
            用例数据
        """
        for case in self.cases:
            if case["case_id"] == case_id:
                return case

        raise ValueError(f"用例 {case_id} 不存在")
