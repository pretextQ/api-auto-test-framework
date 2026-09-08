import yaml
from pathlib import Path
from utils.logger import Logger


class DataManager:
    """测试数据管理器：YAML测试数据文件的唯一读取入口"""

    def __init__(self, data_file: str):
        """
        初始化数据管理器
        
        Args:
            data_file: 数据文件路径（相对于项目根目录）
        """
        self.logger = Logger.get_logger(self.__class__.__name__)
        self.cases = self._load(data_file)

    def _load(self, data_file: str) -> list:
        """加载YAML数据文件"""
        file_path = Path(__file__).parent.parent / data_file
        
        if not file_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        cases = data.get("test_cases", [])
        self._validate_cases(cases)
        self.logger.info(f"已加载 {len(cases)} 条测试用例")
        
        return cases

    def _validate_cases(self, cases: list):
        """校验用例基础结构"""
        for i, case in enumerate(cases):
            if "case_id" not in case:
                raise ValueError(f"用例 {i} 缺少 case_id 字段")
            if "request" not in case:
                raise ValueError(f"用例 {case.get('case_id', i)} 缺少 request 字段")

    def get_test_cases(self) -> list:
        """获取全部用例"""
        return self.cases

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
