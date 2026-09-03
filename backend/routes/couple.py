"""
足迹 - 情侣空间双人配对与协同 API 蓝图
支持生成专属 6 位配对邀请码、双人空间绑定、协同状态查询与解绑。
"""
import uuid
import string
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from backend.auth import login_required
from backend.helpers import get_record_store

couple_bp = Blueprint('couple', __name__)


def _generate_invite_code(length=6) -> str:
    """生成易读且浪漫的配对码 (如 LOVE88, CP6699)"""
    chars = string.ascii_uppercase + string.digits
    # 过滤易混淆字符
    clean_chars = ''.join(c for c in chars if c not in '0O1I')
    random_part = ''.join(secrets.choice(clean_chars) for _ in range(length))
    return f"CP{random_part[:4]}"


@couple_bp.route('/api/couple/status', methods=['GET'])
@login_required
def get_couple_status():
    """获取当前用户的双人空间配对状态与伴侣信息"""
    store = get_record_store()
    user_id = g.current_user['user_id']
    status = store.get_couple_status(user_id)
    return jsonify(status)


@couple_bp.route('/api/couple/invite', methods=['POST'])
@login_required
def create_couple_invite():
    """生成 6 位双人配对邀请码，默认 24 小时有效"""
    store = get_record_store()
    user_id = g.current_user['user_id']

    # 检查是否已完成配对
    status = store.get_couple_status(user_id)
    if status.get('paired'):
        return jsonify({
            'error': '您已与伴侣绑定情侣空间，如需重新配对请先解绑',
            'partner': status.get('partner')
        }), 400

    code = _generate_invite_code()
    # 碰撞重试防重
    for _ in range(5):
        if not store.get_couple_invite(code):
            break
        code = _generate_invite_code()

    expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
    invite = store.create_couple_invite(user_id, code, expires_at)

    return jsonify({
        'success': True,
        'invite_code': code,
        'expires_at': expires_at,
        'message': '配对码已生成，将它发给你的另一半即可开启双人足迹空间！'
    })


@couple_bp.route('/api/couple/pair', methods=['POST'])
@couple_bp.route('/api/couple/bind', methods=['POST'])
@login_required
def pair_couple():
    """使用配对码绑定另一半，共建双人足迹空间"""
    store = get_record_store()
    current_user_id = g.current_user['user_id']

    # 检查自身是否已配对
    current_status = store.get_couple_status(current_user_id)
    if current_status.get('paired'):
        return jsonify({'error': '您当前已在情侣空间中，无法重复绑定'}), 400

    body = request.get_json(silent=True) or {}
    code = (body.get('invite_code') or body.get('code') or '').strip().upper()
    if not code:
        return jsonify({'error': '请输入 6 位配对邀请码'}), 400

    invite = store.get_couple_invite(code)
    if not invite:
        return jsonify({'error': '配对码不存在或已过期失效，请让伴侣重新生成'}), 404

    inviter_id = invite['owner_id']
    if inviter_id == current_user_id:
        return jsonify({'error': '不能与自己配对哦，请把配对码发给你的伴侣'}), 400

    # 检查邀请者是否已经被其他人配对
    inviter_status = store.get_couple_status(inviter_id)
    if inviter_status.get('paired'):
        return jsonify({'error': '该配对码对应的伴侣已被其他空间绑定'}), 400

    # 开启双人配对空间
    space_id = f"space_{uuid.uuid4().hex[:12]}"
    space = store.bind_couple_space(inviter_id, current_user_id, space_id)

    inviter_user = store.get_user_by_id(inviter_id) or {}
    partner_info = {
        'id': inviter_id,
        'username': inviter_user.get('username', '伴侣')
    }

    return jsonify({
        'success': True,
        'message': '🎉 恭喜！双人浪漫足迹空间已成功绑定！',
        'couple_space_id': space_id,
        'partner': partner_info
    })


@couple_bp.route('/api/couple/unbind', methods=['POST'])
@login_required
def unbind_couple():
    """解除情侣空间绑定"""
    store = get_record_store()
    user_id = g.current_user['user_id']
    status = store.get_couple_status(user_id)

    if not status.get('paired'):
        return jsonify({'error': '当前未绑定任何情侣空间'}), 400

    store.unbind_couple_space(user_id)
    return jsonify({
        'success': True,
        'message': '已成功解除情侣空间绑定'
    })
