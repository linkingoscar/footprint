"""
足迹 - 记录 API 蓝图
"""
import re
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from backend.auth import login_required
from backend.helpers import (
    get_record_store, load_records, normalize_record_payload,
    delete_record_assets, parse_float, parse_int, paginate_list
)

records_bp = Blueprint('records', __name__)


@records_bp.route('/api/records', methods=['GET'])
@login_required
def get_records():
    """获取记录列表（支持分页和按模式过滤）"""
    mode = request.args.get('mode')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    keyword = request.args.get('keyword', '').strip()
    year = request.args.get('year', type=int)

    store = get_record_store()
    records = store.list(owner_id=g.current_user['user_id'])
    
    if mode:
        records = [r for r in records if r.get('mode') == mode]
    if keyword:
        records = [r for r in records if keyword.lower() in (r.get('title', '') + r.get('description', '') + r.get('location', '')).lower()]
    if year:
        records = [r for r in records if r.get('date', '').startswith(str(year))]

    if 'page' in request.args or 'per_page' in request.args:
        return jsonify(paginate_list(records, page, per_page))

    # 向后兼容：不传分页参数时返回全部记录列表
    return jsonify(records)


@records_bp.route('/api/records/<record_id>', methods=['GET'])
@login_required
def get_record(record_id):
    """获取单条记录"""
    record = get_record_store().get(record_id, g.current_user['user_id'])
    
    if not record:
        return jsonify({'error': '记录不存在'}), 404
    
    return jsonify(record)


@records_bp.route('/api/records', methods=['POST'])
@login_required
def create_record():
    """创建记录（支持客户端分配稳定 ID 并提供幂等重试保护）"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '无效的数据'}), 400
    
    required_fields = ['mode', 'title']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少字段: {field}'}), 400

    client_id = data.get('id')
    if client_id and isinstance(client_id, str) and 8 <= len(client_id) <= 64 and re.match(r'^[a-zA-Z0-9_-]+$', client_id):
        record_id = client_id
    else:
        record_id = uuid.uuid4().hex

    record = normalize_record_payload(data, record_id)
    store = get_record_store()
    owner_id = g.current_user['user_id']
    
    # 幂等性保障：如果该用户的此记录已存在（例如网络丢响应后的重试），则执行幂等更新并返回 200
    existing = store.get(record_id, owner_id)
    if existing:
        store.update(record_id, record, owner_id)
        return jsonify(record), 200

    store.create(record, owner_id)
    return jsonify(record), 201


@records_bp.route('/api/records/import', methods=['POST'])
@login_required
def import_records():
    """批量导入记录，可选择替换现有数据。"""
    data = request.get_json()
    if isinstance(data, list):
        incoming = data
        replace = False
    elif isinstance(data, dict):
        incoming = data.get('records')
        replace = bool(data.get('replace', False))
    else:
        incoming = None
        replace = False
    if not isinstance(incoming, list):
        return jsonify({'error': '导入数据必须是记录数组'}), 400

    store = get_record_store()
    owner_id = g.current_user['user_id']
    if replace:
        for existing in store.list(owner_id=owner_id):
            delete_record_assets(existing)
            store.delete(existing.get('id'), owner_id)

    imported = []
    for item in incoming:
        if not isinstance(item, dict) or not item.get('title'):
            continue
        record = normalize_record_payload(item)
        if store.get(record['id'], owner_id):
            store.update(record['id'], record, owner_id)
        else:
            store.create(record, owner_id)
        imported.append(record)

    return jsonify({
        'message': '导入成功',
        'count': len(imported),
        'records': imported
    })


@records_bp.route('/api/records', methods=['DELETE'])
@login_required
def delete_records():
    """清空当前用户的全部记录。"""
    store = get_record_store()
    owner_id = g.current_user['user_id']
    records = store.list(owner_id=owner_id)
    for record in records:
        delete_record_assets(record)
        store.delete(record.get('id'), owner_id)
    return jsonify({'message': '清空成功', 'count': len(records)})


@records_bp.route('/api/records/<record_id>', methods=['PUT'])
@login_required
def update_record(record_id):
    """更新记录"""
    data = request.get_json()
    store = get_record_store()
    owner_id = g.current_user['user_id']
    record = store.get(record_id, owner_id)
    
    if not record:
        return jsonify({'error': '记录不存在'}), 404
    
    # 更新字段
    for key in ['mode', 'title', 'description', 'location', 'latitude', 'longitude', 'date', 'images', 'rating', 'price', 'tags', 'metadata']:
        if key in data:
            if key in ('latitude', 'longitude', 'price'):
                record[key] = parse_float(data.get(key))
            elif key == 'rating':
                record[key] = parse_int(data.get(key))
            else:
                record[key] = data[key]
    
    record['updatedAt'] = datetime.now().isoformat()
    store.update(record_id, record, owner_id)
    
    return jsonify(record)


@records_bp.route('/api/records/<record_id>', methods=['DELETE'])
@login_required
def delete_record(record_id):
    """删除记录"""
    store = get_record_store()
    owner_id = g.current_user['user_id']
    record = store.get(record_id, owner_id)
    
    if not record:
        return jsonify({'error': '记录不存在'}), 404
    
    delete_record_assets(record)
    
    store.delete(record_id, owner_id)
    
    return jsonify({'message': '删除成功'})
