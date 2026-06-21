"""
足迹 - 记录 API 蓝图
"""
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

from backend.helpers import (
    get_record_store, load_records, normalize_record_payload,
    delete_record_assets, parse_float, parse_int, paginate_list
)

records_bp = Blueprint('records', __name__)


@records_bp.route('/api/records', methods=['GET'])
def get_records():
    """获取记录列表（支持分页和按模式过滤）"""
    mode = request.args.get('mode')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    records = load_records(mode)

    # 如果请求中指定了分页参数，返回分页格式
    if 'page' in request.args or 'per_page' in request.args:
        result = paginate_list(records, page, per_page)
        return jsonify(result)

    # 向后兼容：不传分页参数时返回全部记录（原行为）
    return jsonify(records)


@records_bp.route('/api/records/<record_id>', methods=['GET'])
def get_record(record_id):
    """获取单条记录"""
    record = get_record_store().get(record_id)
    
    if not record:
        return jsonify({'error': '记录不存在'}), 404
    
    return jsonify(record)


@records_bp.route('/api/records', methods=['POST'])
def create_record():
    """创建记录"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '无效的数据'}), 400
    
    required_fields = ['mode', 'title']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少字段: {field}'}), 400

    record = normalize_record_payload(data, uuid.uuid4().hex)
    
    get_record_store().create(record)
    
    return jsonify(record), 201


@records_bp.route('/api/records/import', methods=['POST'])
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
    if replace:
        for existing in store.list():
            delete_record_assets(existing)
            store.delete(existing.get('id'))

    imported = []
    for item in incoming:
        if not isinstance(item, dict) or not item.get('title'):
            continue
        record = normalize_record_payload(item)
        if store.get(record['id']):
            store.update(record['id'], record)
        else:
            store.create(record)
        imported.append(record)

    return jsonify({
        'message': '导入成功',
        'count': len(imported),
        'records': imported
    })


@records_bp.route('/api/records', methods=['DELETE'])
def delete_records():
    """清空全部记录。"""
    store = get_record_store()
    records = store.list()
    for record in records:
        delete_record_assets(record)
        store.delete(record.get('id'))
    return jsonify({'message': '清空成功', 'count': len(records)})


@records_bp.route('/api/records/<record_id>', methods=['PUT'])
def update_record(record_id):
    """更新记录"""
    data = request.get_json()
    store = get_record_store()
    record = store.get(record_id)
    
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
    store.update(record_id, record)
    
    return jsonify(record)


@records_bp.route('/api/records/<record_id>', methods=['DELETE'])
def delete_record(record_id):
    """删除记录"""
    store = get_record_store()
    record = store.get(record_id)
    
    if not record:
        return jsonify({'error': '记录不存在'}), 404
    
    delete_record_assets(record)
    
    store.delete(record_id)
    
    return jsonify({'message': '删除成功'})
