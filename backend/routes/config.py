"""
足迹 - 运行时配置 API 蓝图
"""
from flask import Blueprint, request, jsonify

from backend.helpers import get_runtime_config, save_runtime_config, redact_config, CONFIG_KEYS
from backend.auth import login_required

config_bp = Blueprint('config', __name__)


@config_bp.route('/api/config', methods=['GET', 'POST'])
@login_required
def runtime_config():
    """读取或保存设置页同步的运行时配置。"""
    if request.method == 'GET':
        return jsonify(redact_config(get_runtime_config()))

    if not save_runtime_config:
        return jsonify({'error': '配置模块不可用'}), 500

    data = request.get_json() or {}
    allowed = {key: value for key, value in data.items() if key in CONFIG_KEYS}
    config = save_runtime_config(allowed)
    return jsonify({
        'message': '配置已保存',
        'config': redact_config(config)
    })
