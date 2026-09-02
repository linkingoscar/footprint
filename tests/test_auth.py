"""
足迹 - 认证模块单元测试 (pytest 规范)
运行方式: pytest tests/test_auth.py -v
"""
import os
import sys
import pytest
from flask import Flask, g

# 添加父目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.auth import (
    hash_password, check_password, generate_token, verify_token,
    get_current_user, login_required, optional_auth, SECRET_KEY, EXPIRY_HOURS,
)


@pytest.fixture
def app():
    """轻量测试 Flask 应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


def test_secret_key_and_expiry_configured():
    """验证密钥与过期时间已有效配置"""
    assert len(SECRET_KEY) >= 32
    assert isinstance(EXPIRY_HOURS, int)
    assert EXPIRY_HOURS > 0


def test_password_hashing():
    """验证密码哈希与校验功能"""
    pw = "my_secure_password"
    hashed = hash_password(pw)
    assert hashed != pw
    assert check_password(pw, hashed) is True
    assert check_password("wrong_password", hashed) is False


def test_token_generation_and_verification():
    """验证 JWT Token 签发与解密验证"""
    user_id = "user-123"
    username = "alice"
    token = generate_token(user_id, username)
    assert isinstance(token, str)
    assert len(token) > 20

    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["username"] == username
    assert "exp" in payload
    assert "iat" in payload


def test_invalid_token():
    """验证非法或畸变 Token 返回 None"""
    assert verify_token("not.a.valid.token") is None
    assert verify_token("") is None
    assert verify_token("Bearer xxx") is None


def test_get_current_user_with_context(app):
    """测试在不同请求上下文中的 get_current_user 表现"""
    token = generate_token("user-123", "alice")

    with app.test_request_context('/test', headers={'Authorization': f'Bearer {token}'}):
        user = get_current_user()
        assert user is not None
        assert user['user_id'] == 'user-123'
        assert user['username'] == 'alice'

    with app.test_request_context('/test'):
        user = get_current_user()
        assert user is None

    with app.test_request_context('/test', headers={'Authorization': 'Bearer invalid.token.here'}):
        user = get_current_user()
        assert user is None

    # 测试 allow_query_token=True 支持 URL 参数 ?token=
    with app.test_request_context(f'/uploads/pic.png?token={token}'):
        user_query = get_current_user(allow_query_token=True)
        assert user_query is not None
        assert user_query['user_id'] == 'user-123'


def test_login_required_decorator(app):
    """测试 login_required 装饰器拦截与放行"""
    token = generate_token("user-123", "alice")

    @login_required
    def protected():
        return {"status": "ok"}, 200

    # 未认证情况拦截并返回 401
    with app.test_request_context('/test'):
        resp, code = protected()
        assert code == 401
        data = resp.get_json() if hasattr(resp, 'get_json') else resp
        assert 'error' in data

    # 携带有效 token 放行
    with app.test_request_context('/test', headers={'Authorization': f'Bearer {token}'}):
        result, code = protected()
        assert code == 200
        assert result == {"status": "ok"}
        assert g.current_user['user_id'] == 'user-123'


def test_optional_auth_decorator(app):
    """测试 optional_auth 装饰器"""
    token = generate_token("user-123", "alice")

    @optional_auth
    def maybe():
        return g.current_user

    # 无 token 时 g.current_user 应为 None
    with app.test_request_context('/test'):
        result = maybe()
        assert result is None

    # 有 token 时应注入 g.current_user
    with app.test_request_context('/test', headers={'Authorization': f'Bearer {token}'}):
        result = maybe()
        assert result is not None
        assert result['user_id'] == 'user-123'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
