"""
足迹 - 费用追踪 API 蓝图
"""
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from backend.auth import login_required
from backend.helpers import get_record_store, parse_float

expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    """获取费用列表（支持分页）"""
    record_id = request.args.get('record_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    store = get_record_store()
    expenses = store.list_expenses(record_id, g.current_user['user_id'])

    if 'page' in request.args or 'per_page' in request.args:
        from backend.helpers import paginate_list
        result = paginate_list(expenses, page, per_page)
        return jsonify(result)

    return jsonify(expenses)


@expenses_bp.route('/api/expenses', methods=['POST'])
@login_required
def create_expense():
    """创建费用记录"""
    data = request.get_json()
    if not data or not data.get('amount'):
        return jsonify({'error': '缺少金额'}), 400
    
    expense = {
        'id': uuid.uuid4().hex,
        'record_id': data.get('record_id'),
        'mode': data.get('mode', 'travel'),
        'category': data.get('category', '其他'),
        'amount': parse_float(data.get('amount')) or 0,
        'currency': data.get('currency', 'CNY'),
        'description': data.get('description', ''),
        'date': data.get('date') or datetime.now().strftime('%Y-%m-%d'),
    }
    
    store = get_record_store()
    created = store.create_expense(expense, g.current_user['user_id'])
    return jsonify(created), 201


@expenses_bp.route('/api/expenses/<expense_id>', methods=['PUT'])
@login_required
def update_expense(expense_id):
    """更新费用记录"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效的数据'}), 400
    
    expense = {
        'record_id': data.get('record_id'),
        'mode': data.get('mode', 'travel'),
        'category': data.get('category', '其他'),
        'amount': parse_float(data.get('amount')) or 0,
        'currency': data.get('currency', 'CNY'),
        'description': data.get('description', ''),
        'date': data.get('date'),
    }
    
    store = get_record_store()
    updated = store.update_expense(expense_id, expense, g.current_user['user_id'])
    if not updated:
        return jsonify({'error': '费用不存在'}), 404
    return jsonify(updated)


@expenses_bp.route('/api/expenses/<expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    """删除费用记录"""
    store = get_record_store()
    deleted = store.delete_expense(expense_id, g.current_user['user_id'])
    if not deleted:
        return jsonify({'error': '费用不存在'}), 404
    return jsonify({'message': '删除成功'})


@expenses_bp.route('/api/expenses/stats', methods=['GET'])
@login_required
def get_expense_stats():
    """获取费用统计"""
    store = get_record_store()
    stats = store.get_expense_stats(g.current_user['user_id'])
    return jsonify(stats)
