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
    """从环境变量读取 JWT 密钥；未配置时优先从持久化文件读取或生成并保存，防止服务重启后 Token 失效。"""
    key = os.environ.get('JWT_SECRET_KEY', '').strip()
    if key:
        return key

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(base_dir), 'data')
    target_dir = data_dir if os.path.exists(data_dir) else base_dir
    secret_file = os.path.join(target_dir, '.jwt_secret')

    if os.path.exists(secret_file):
        try:
            with open(secret_file, 'r', encoding='utf-8') as f:
                saved = f.read().strip()
                if saved:
                    return saved
        except OSError:
            pass

    fallback = secrets.token_hex(32)
    try:
        with open(secret_file, 'w', encoding='utf-8') as f:
            f.write(fallback)
    except OSError:
        pass

    print(
        "[WARNING] JWT_SECRET_KEY 环境变量未设置，已自动生成持久化密钥。"
        "生产环境建议通过环境变量显式配置固定的 JWT_SECRET_KEY。"
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


def generate_media_token(user_id: str, username: str, expiry_minutes: int = 15, expiry_hours: float | None = None) -> str:
    """生成仅用于媒体资源代理读取的短期受限 Token (scope: media，默认 15 分钟有效期，兼容旧 expiry_hours 参数)。"""
    now = datetime.now(timezone.utc)
    delta = timedelta(hours=expiry_hours) if expiry_hours is not None else timedelta(minutes=expiry_minutes)
    payload = {
        'sub': user_id,
        'username': username,
        'scope': 'media',
        'iat': now,
        'exp': now + delta,
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


def _extract_token_from_query() -> str | None:
    """从查询参数 token= 提取 Token（用于 <img> 等无法携带 Header 的场景）。"""
    token = request.args.get('token', '')
    return token.strip() or None


def get_current_user(allow_query_token: bool = False) -> dict | None:
    """
    从当前 Flask 请求中提取并验证用户 Token。

    参数:
        allow_query_token: 是否允许从查询参数 ?token= 提取（仅用于图片等静态资源场景）。

    返回:
        包含 user_id 和 username 的字典，未认证时返回 None。
    """
    token = _extract_token_from_header()
    from_query = False
    if not token and allow_query_token:
        token = _extract_token_from_query()
        if token:
            from_query = True
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None

    # 安全隔离：URL Query 参数中的 Token 必须是 scope == 'media'
    # Master Token 严禁在 URL Query 中传递使用，防止泄露于访问日志与历史记录
    if from_query and payload.get('scope') != 'media':
        return None

    # 安全隔离：media scope Token 仅允许在静态媒体资源代理场景 (allow_query_token=True) 下使用，
    # 禁止用于任何核心业务 API 操作
    if payload.get('scope') == 'media' and not allow_query_token:
        return None

    return {
        'user_id': payload.get('sub'),
        'username': payload.get('username'),
        'scope': payload.get('scope', 'master'),
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
