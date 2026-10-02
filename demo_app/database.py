"""演示服务数据库层:连接管理、建表与种子数据初始化(幂等,可重复执行)"""
import os
import time
import hashlib

import pymysql

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "test_user"),
    "password": os.getenv("DB_PASSWORD", "test_password"),
    "database": os.getenv("DB_NAME", "test_db"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
      user_id INT AUTO_INCREMENT PRIMARY KEY,
      username VARCHAR(50) NOT NULL UNIQUE,
      password_hash VARCHAR(64) NOT NULL,
      email VARCHAR(100) NOT NULL DEFAULT '',
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
      product_id INT PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      price DECIMAL(10, 2) NOT NULL,
      stock INT NOT NULL DEFAULT 0,
      status VARCHAR(20) NOT NULL DEFAULT 'on_sale'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
      order_id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT NOT NULL,
      product_id INT NOT NULL,
      quantity INT NOT NULL,
      amount DECIMAL(10, 2) NOT NULL,
      status VARCHAR(20) NOT NULL DEFAULT 'created',
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def wait_and_init(retries: int = 15, delay: int = 2):
    """等待数据库可用后建表并写入种子数据,全部操作幂等"""
    conn = None
    for attempt in range(1, retries + 1):
        try:
            conn = get_connection()
            break
        except Exception as e:
            print(f"数据库连接失败({attempt}/{retries}): {e}")
            time.sleep(delay)
    if conn is None:
        raise RuntimeError("数据库连接失败,演示服务无法启动")

    try:
        with conn.cursor() as cursor:
            for stmt in TABLES:
                cursor.execute(stmt)

            cursor.execute("SELECT COUNT(*) AS total FROM users")
            if cursor.fetchone()["total"] == 0:
                cursor.executemany(
                    "INSERT INTO users (username, password_hash, email, status) VALUES (%s, %s, %s, %s)",
                    [
                        ("testuser", hash_password("testpass"), "testuser@example.com", "active"),
                        ("lockeduser", hash_password("testpass"), "locked@example.com", "disabled"),
                    ],
                )

            cursor.execute("SELECT COUNT(*) AS total FROM products")
            if cursor.fetchone()["total"] == 0:
                cursor.executemany(
                    "INSERT INTO products (product_id, name, price, stock, status) VALUES (%s, %s, %s, %s, %s)",
                    [
                        (1001, "机械键盘", "199.00", 100, "on_sale"),
                        (1002, "无线鼠标", "79.00", 50, "on_sale"),
                    ],
                )
        conn.commit()
        print("数据库初始化完成")
    finally:
        conn.close()
