"""Quick smoke test for backend/auth.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

from backend.auth import (
    hash_password, check_password, generate_token, verify_token,
    get_current_user, login_required, optional_auth, SECRET_KEY, EXPIRY_HOURS,
)

print(f"SECRET_KEY length: {len(SECRET_KEY)}")
print(f"EXPIRY_HOURS: {EXPIRY_HOURS}")

# Password hashing
pw = "my_secure_password"
hashed = hash_password(pw)
assert check_password(pw, hashed), "check_password should return True for correct password"
assert not check_password("wrong", hashed), "check_password should return False for wrong password"
print("[OK] hash_password / check_password")

# Token generation and verification
token = generate_token("user-123", "alice")
payload = verify_token(token)
assert payload is not None, "verify_token should return payload"
assert payload["sub"] == "user-123", f"Expected sub=user-123, got {payload['sub']}"
assert payload["username"] == "alice", f"Expected username=alice, got {payload['username']}"
print(f"[OK] generate_token / verify_token (token length={len(token)})")

# Invalid token
bad = verify_token("not.a.valid.token")
assert bad is None, "verify_token should return None for invalid token"
print("[OK] verify_token returns None for invalid token")

# Flask integration test
from flask import Flask, g
app = Flask(__name__)

with app.test_request_context(
    '/test',
    headers={'Authorization': f'Bearer {token}'}
):
    user = get_current_user()
    assert user is not None
    assert user['user_id'] == 'user-123'
    assert user['username'] == 'alice'
    print("[OK] get_current_user with valid Bearer token")

with app.test_request_context('/test'):
    user = get_current_user()
    assert user is None
    print("[OK] get_current_user returns None without token")

with app.test_request_context(
    '/test',
    headers={'Authorization': 'Bearer invalid.token.here'}
):
    user = get_current_user()
    assert user is None
    print("[OK] get_current_user returns None with invalid token")

# Test login_required decorator
with app.test_request_context('/test'):
    @login_required
    def protected():
        return "ok"
    resp, code = protected()
    assert code == 401
    print("[OK] login_required returns 401 without token")

with app.test_request_context(
    '/test',
    headers={'Authorization': f'Bearer {token}'}
):
    @login_required
    def protected2():
        return "ok", 200
    result = protected2()
    assert result == ("ok", 200)
    assert g.current_user['user_id'] == 'user-123'
    print("[OK] login_required passes with valid token")

# Test optional_auth decorator
with app.test_request_context('/test'):
    @optional_auth
    def maybe():
        return g.current_user
    result = maybe()
    assert result is None
    print("[OK] optional_auth sets g.current_user=None without token")

with app.test_request_context(
    '/test',
    headers={'Authorization': f'Bearer {token}'}
):
    @optional_auth
    def maybe2():
        return g.current_user
    result = maybe2()
    assert result['user_id'] == 'user-123'
    print("[OK] optional_auth sets g.current_user with valid token")

print("\n=== ALL TESTS PASSED ===")
