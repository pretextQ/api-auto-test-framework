import re

import pymysql
from utils.logger import Logger


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseHelper:
    """MySQL数据库工具：全项目唯一DB入口"""

    def __init__(self, db_config: dict):
        """
        初始化数据库助手
        
        Args:
            db_config: 数据库配置字典
        """
        self.logger = Logger.get_logger(self.__class__.__name__)
        self.config = db_config
        self._connection = None

    def _get_connection(self):
        """获取数据库连接（惰性创建）"""
        if self._connection is not None and self._connection.open:
            try:
                if hasattr(self._connection, "ping"):
                    self._connection.ping()
                return self._connection
            except Exception:
                self.logger.warning("数据库连接已失效，正在重连")
                try:
                    self._connection.close()
                except Exception:
                    pass
                self._connection = None

        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(
                host=self.config.get("host"),
                port=int(self.config.get("port", 3306)),
                user=self.config.get("user"),
                password=self.config.get("password"),
                database=self.config.get("name"),
                charset=self.config.get("charset", "utf8mb4"),
                cursorclass=pymysql.cursors.DictCursor
            )
            self.logger.info("数据库连接已建立")
        return self._connection

    @staticmethod
    def _validate_identifier(identifier: str, kind: str):
        if not isinstance(identifier, str) or not IDENTIFIER_PATTERN.fullmatch(identifier):
            raise ValueError(f"非法{kind}: {identifier!r}")

    def execute_query(self, sql: str, params: tuple = ()) -> list:
        """
        执行查询
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            查询结果列表
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                self.logger.debug(f"执行SQL: {sql}, 参数: {params}")
                cursor.execute(sql, params)
                results = cursor.fetchall()
                # 结束MySQL默认Repeatable Read下的只读事务，确保下一次查询看到最新提交。
                conn.commit()
                self.logger.debug(f"查询返回 {len(results)} 条记录")
                return results
        except Exception as e:
            conn.rollback()
            self.logger.error(f"查询失败: {e}")
            raise

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """
        执行更新
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            影响行数
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                self.logger.debug(f"执行SQL: {sql}, 参数: {params}")
                affected = cursor.execute(sql, params)
                conn.commit()
                self.logger.debug(f"更新影响 {affected} 行")
                return affected
        except Exception as e:
            conn.rollback()
            self.logger.error(f"更新失败: {e}")
            raise

    def fetch_one(self, table: str, conditions: dict) -> dict:
        """
        按条件查询单条记录
        
        Args:
            table: 表名
            conditions: 查询条件
            
        Returns:
            记录字典或None
        """
        self._validate_identifier(table, "表名")
        if not isinstance(conditions, dict) or not conditions:
            raise ValueError("conditions 必须是非空对象")
        for column in conditions:
            self._validate_identifier(column, "列名")

        where_parts = [f"{k} = %s" for k in conditions.keys()]
        where_clause = " AND ".join(where_parts)
        sql = f"SELECT * FROM {table} WHERE {where_clause} LIMIT 1"
        params = tuple(conditions.values())
        
        results = self.execute_query(sql, params)
        return results[0] if results else None

    def validate(self, table: str, conditions: dict, expected: dict) -> bool:
        """
        校验数据库记录
        
        Args:
            table: 表名
            conditions: 查询条件
            expected: 期望数据
            
        Returns:
            是否一致
        """
        if not isinstance(expected, dict) or not expected:
            raise ValueError("expected 必须是非空对象")
        actual = self.fetch_one(table, conditions)
        if actual is None:
            return False

        for key, expected_value in expected.items():
            self._validate_identifier(key, "列名")
            if actual.get(key) != expected_value:
                return False
        return True

    def close(self):
        """关闭数据库连接"""
        if self._connection and self._connection.open:
            self._connection.close()
            self.logger.info("数据库连接已关闭")
