import json
import allure
from contextlib import contextmanager


class Reporter:
    """报告工具：对Allure的轻量封装"""

    @staticmethod
    @contextmanager
    def step(title: str):
        """
        Allure步骤上下文管理器
        
        Args:
            title: 步骤标题
            
        用法：
            with Reporter.step("登录"):
                resp = api_client.login(...)
        """
        with allure.step(title):
            yield

    @staticmethod
    def attach_text(name: str, content: str):
        """
        附加文本附件
        
        Args:
            name: 附件名称
            content: 文本内容
        """
        allure.attach(content, name=name, attachment_type=allure.attachment_type.TEXT)

    @staticmethod
    def attach_json(name: str, data):
        """
        附加JSON附件
        
        Args:
            name: 附件名称
            data: 数据
        """
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        allure.attach(json_str, name=name, attachment_type=allure.attachment_type.JSON)

    @staticmethod
    def attach_log_file(path: str):
        """
        附加日志文件
        
        Args:
            path: 日志文件路径
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            allure.attach(content, name="日志文件", attachment_type=allure.attachment_type.TEXT)
        except Exception:
            pass
