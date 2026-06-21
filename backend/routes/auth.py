"""
足迹 - 认证 API 蓝图
"""
import uuid
from flask import Blueprint, request, jsonify, g

from backend.helpers import get_record_store
from backend.auth import hash_password, check_password, generate_token, login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效的数据'}), 400
    
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    if len(username) < 3 or len(username) > 32:
        return jsonify({'error': '用户名长度应为 3-32 个字符'}), 400
    
    if len(password) < 6:
        return jsonify({'error': '密码长度不能少于 6 个字符'}), 400
    
    store = get_record_store()
    if store.get_user_by_username(username):
        return jsonify({'error': '用户名已存在'}), 409
    
    user_id = uuid.uuid4().hex
    password_hash = hash_password(password)
    user = store.create_user(user_id, username, password_hash)
    token = generate_token(user_id, username)
    
    return jsonify({
        'message': '注册成功',
        'token': token,
        'user': {'id': user_id, 'username': username}
    }), 201


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效的数据'}), 400
    
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    store = get_record_store()
    user = store.get_user_by_username(username)
    
    if not user or not check_password(password, user['password_hash']):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    token = generate_token(user['id'], username)
    return jsonify({
        'token': token,
        'user': {'id': user['id'], 'username': username}
    })


@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def get_me():
    """获取当前用户信息"""
    return jsonify(g.current_user)
