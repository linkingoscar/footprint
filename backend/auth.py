"""
足迹 - JWT 认证模块
提供基于 PyJWT 的 Token 生成、验证，以及 Flask 装饰器。
"""

import os
import secrets
import functools
from datetime import datetime, timedelta, timezone

import jwt
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash


# ========== 配置 ==========

def _get_secret_key() -> str:
    """从环境变量读取 JWT 密钥；未配置时生成随机密钥并打印警告。"""
    key = os.environ.get('JWT_SECRET_KEY', '')
    if key:
        return key
    fallback = secrets.token_hex(32)
    print(
        "[WARNING] JWT_SECRET_KEY 环境变量未设置，已自动生成随机密钥。"
        "请在生产环境中设置固定密钥，否则重启后所有 Token 将失效。"
    )
    return fallback


SECRET_KEY: str = _get_secret_key()
EXPIRY_HOURS: int = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))


# ========== 密码工具 ==========

def hash_password(password: str) -> str:
    """对明文密码进行哈希，返回哈希字符串。"""
    return generate_password_hash(password)


def check_password(password: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    return check_password_hash(hashed, password)


# ========== Token 工具 ==========

def generate_token(user_id: str, username: str) -> str:
    """
    生成 JWT Token。

    Claims:
        - sub: 用户 ID
        - username: 用户名
        - exp: 过期时间
        - iat: 签发时间
    """
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,
        'username': username,
        'iat': now,
        'exp': now + timedelta(hours=EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def verify_token(token: str) -> dict | None:
    """
    解码并验证 JWT Token。

    返回:
        解码后的 payload 字典，验证失败时返回 None。
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ========== 请求辅助 ==========

def _extract_token_from_header() -> str | None:
    """从 Authorization 请求头提取 Bearer Token。"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    return None


def get_current_user() -> dict | None:
    """
    从当前 Flask 请求中提取并验证用户 Token。

    返回:
        包含 user_id 和 username 的字典，未认证时返回 None。
    """
    token = _extract_token_from_header()
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    return {
        'user_id': payload.get('sub'),
        'username': payload.get('username'),
    }


# ========== Flask 装饰器 ==========

def login_required(f):
    """
    装饰器：要求请求携带有效 JWT Token。
    验证通过后将用户信息写入 flask.g.current_user。
    验证失败时返回 401 JSON 响应。

    用法::

        @app.route('/api/protected')
        @login_required
        def protected():
            user = g.current_user
            return jsonify(user)
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': '未认证，请先登录', 'code': 401}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """
    装饰器：可选认证。
    如果请求携带有效 Token，则将用户信息写入 flask.g.current_user；
    如果未携带或 Token 无效，不阻止请求继续执行（g.current_user 为 None）。

    用法::

        @app.route('/api/maybe-protected')
        @optional_auth
        def maybe_protected():
            user = g.current_user  # 可能为 None
            return jsonify({'user': user})
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        g.current_user = get_current_user()
        return f(*args, **kwargs)
    return decorated
