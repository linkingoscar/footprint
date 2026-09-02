"""
足迹 - 用户扩展功能数据 API 蓝图
支持行程规划、愿望清单、食材库、纪念日、爱情笔记、约会计划、情侣任务等多端云同步。
"""
from flask import Blueprint, request, jsonify, g
from backend.auth import login_required
from backend.helpers import get_record_store

features_bp = Blueprint('features', __name__)

ALLOWED_FEATURES = {
    'travel_plans',
    'wishes',
    'ingredients',
    'anniversaries',
    'love_notes',
    'date_plans',
    'couple_tasks',
    'packing_list',
    'love_capsules',
}


COUPLE_SHARED_KEYS = {'anniversaries', 'love_notes', 'date_plans', 'couple_tasks', 'wishes', 'love_capsules'}


def _get_effective_owner(feature_key: str, user_id: str, store) -> str:
    """如果用户已配对，且特性属于情侣特性，则使用情侣空间命名空间"""
    if feature_key in COUPLE_SHARED_KEYS:
        status = store.get_couple_status(user_id)
        if status.get('paired') and status.get('couple_space_id'):
            return status['couple_space_id']
    return user_id


@features_bp.route('/api/features', methods=['GET'])
@login_required
def get_all_features():
    """获取当前用户的所有扩展特性数据，已配对则合并情侣空间共享数据"""
    store = get_record_store()
    owner_id = g.current_user['user_id']
    features = store.get_user_features(owner_id)
    status = store.get_couple_status(owner_id)
    if status.get('paired') and status.get('couple_space_id'):
        shared = store.get_user_features(status['couple_space_id'])
        for k in COUPLE_SHARED_KEYS:
            if k in shared:
                features[k] = shared[k]
    return jsonify({
        'features': features,
        'owner_id': owner_id,
        'couple_paired': bool(status.get('paired'))
    })


@features_bp.route('/api/features/<feature_key>', methods=['GET'])
@login_required
def get_single_feature(feature_key: str):
    """获取单个扩展特性的数据"""
    if feature_key not in ALLOWED_FEATURES:
        return jsonify({'error': f'不支持的特性类型: {feature_key}'}), 400

    store = get_record_store()
    user_id = g.current_user['user_id']
    eff_owner = _get_effective_owner(feature_key, user_id, store)
    features = store.get_user_features(eff_owner)
    data = features.get(feature_key, [])
    return jsonify({
        'feature_key': feature_key,
        'data': data,
    })


@features_bp.route('/api/features/<feature_key>', methods=['PUT', 'POST'])
@login_required
def save_feature(feature_key: str):
    """保存/同步单个扩展特性的数据"""
    if feature_key not in ALLOWED_FEATURES:
        return jsonify({'error': f'不支持的特性类型: {feature_key}'}), 400

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({'error': '无效的 JSON 请求体'}), 400

    # 兼容直接传数组或传 {'data': [...]}
    data = body.get('data', body) if isinstance(body, dict) and 'data' in body else body

    store = get_record_store()
    user_id = g.current_user['user_id']
    eff_owner = _get_effective_owner(feature_key, user_id, store)
    store.save_user_feature(eff_owner, feature_key, data)

    return jsonify({
        'success': True,
        'feature_key': feature_key,
        'count': len(data) if isinstance(data, (list, dict)) else 1,
    })


@features_bp.route('/api/features/<feature_key>', methods=['DELETE'])
@login_required
def delete_feature(feature_key: str):
    """删除/清空指定特性的数据"""
    if feature_key not in ALLOWED_FEATURES:
        return jsonify({'error': f'不支持的特性类型: {feature_key}'}), 400

    store = get_record_store()
    user_id = g.current_user['user_id']
    eff_owner = _get_effective_owner(feature_key, user_id, store)
    store.delete_user_feature(eff_owner, feature_key)

    return jsonify({
        'success': True,
        'deleted': feature_key,
    })
