"""演示服务接口层:统一响应包 {code, message, data},业务错误 code != 0 且 HTTP 状态码为 200"""
import time
from typing import Optional

import jwt
import uvicorn
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel

from demo_app import database

JWT_SECRET = "demo-secret"
TOKEN_EXPIRE_SECONDS = 3600

app = FastAPI(title="Demo API", description="接口自动化测试框架的被测演示服务")


@app.on_event("startup")
def startup():
    database.wait_and_init()


def ok(data=None):
    return {"code": 0, "message": "success", "data": data}


def fail(code: int, message: str):
    return {"code": code, "message": message, "data": None}


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    status: Optional[str] = None


class OrderRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int


def create_token(user_id: int) -> str:
    payload = {"user_id": user_id, "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def current_user_id(request: Request) -> Optional[int]:
    """解析 Bearer Token,无效或过期返回 None"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(auth[len("Bearer "):], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return payload.get("user_id")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginRequest):
    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (payload.username,))
            user = cursor.fetchone()
        conn.commit()
    finally:
        conn.close()

    if user is None or user["password_hash"] != database.hash_password(payload.password):
        return fail(1001, "用户名或密码错误")
    if user["status"] != "active":
        return fail(1002, "账号已被禁用")
    return ok({"token": create_token(user["user_id"]), "user_id": user["user_id"],
               "username": user["username"]})


@app.get("/api/users/{user_id}")
def get_user(user_id: int, request: Request):
    uid = current_user_id(request)
    if uid is None:
        return fail(401, "未登录或凭证已过期")

    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
        conn.commit()
    finally:
        conn.close()

    if user is None:
        return fail(2001, "用户不存在")
    return ok({"user_id": user["user_id"], "username": user["username"],
               "email": user["email"], "status": user["status"]})


@app.put("/api/users/{user_id}")
def update_user(user_id: int, payload: UpdateUserRequest, request: Request):
    uid = current_user_id(request)
    if uid is None:
        return fail(401, "未登录或凭证已过期")
    if uid != user_id:
        return fail(403, "无权修改他人信息")
    if payload.status is not None and payload.status not in ("active", "disabled"):
        return fail(2002, "参数不合法")

    fields, params = [], []
    if payload.email is not None:
        fields.append("email = %s")
        params.append(payload.email)
    if payload.status is not None:
        fields.append("status = %s")
        params.append(payload.status)
    if not fields:
        return fail(2002, "参数不合法")

    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s",
                           (*params, user_id))
        conn.commit()
    finally:
        conn.close()
    return get_user(user_id, request)


@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
        conn.commit()
    finally:
        conn.close()

    if product is None:
        return fail(3001, "商品不存在")
    return ok({"product_id": product["product_id"], "name": product["name"],
               "price": float(product["price"]), "stock": product["stock"],
               "status": product["status"]})


@app.post("/api/orders")
def create_order(payload: OrderRequest, request: Request):
    uid = current_user_id(request)
    if uid is None:
        return fail(401, "未登录或凭证已过期")
    if payload.quantity < 1:
        return fail(3002, "购买数量不合法")

    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE product_id = %s", (payload.product_id,))
            product = cursor.fetchone()
            if product is None:
                conn.rollback()
                return fail(3001, "商品不存在")
            if product["status"] != "on_sale":
                conn.rollback()
                return fail(3004, "商品已下架")
            if product["stock"] < payload.quantity:
                conn.rollback()
                return fail(3005, "库存不足")

            amount = float(product["price"]) * payload.quantity
            cursor.execute(
                "INSERT INTO orders (user_id, product_id, quantity, amount, status) VALUES (%s, %s, %s, %s, %s)",
                (payload.user_id, payload.product_id, payload.quantity, amount, "created"),
            )
            order_id = cursor.lastrowid
            cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s",
                           (payload.quantity, payload.product_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return ok({"order_id": order_id, "product_id": payload.product_id,
               "quantity": payload.quantity, "amount": amount, "status": "created"})


@app.get("/api/orders")
def list_orders(user_id: int = Query(...), request: Request = None):
    uid = current_user_id(request)
    if uid is None:
        return fail(401, "未登录或凭证已过期")
    if uid != user_id:
        return fail(403, "无权查看他人订单")

    conn = database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE user_id = %s", (user_id,))
            total = cursor.fetchone()["total"]
            cursor.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY order_id DESC", (user_id,))
            items = cursor.fetchall()
        conn.commit()
    finally:
        conn.close()

    return ok({"total": total,
               "items": [{"order_id": i["order_id"], "product_id": i["product_id"],
                          "quantity": i["quantity"], "amount": float(i["amount"]),
                          "status": i["status"]} for i in items]})


if __name__ == "__main__":
    uvicorn.run("demo_app.main:app", host="0.0.0.0", port=8000)
