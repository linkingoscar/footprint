"""
足迹 - 图片上传 API 蓝图
"""
from flask import Blueprint, request, jsonify

from backend.auth import login_required
from backend.helpers import allowed_file, save_upload_file, fetch_image_url_safe

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/api/upload', methods=['POST'])
@login_required
def upload_image():
    """上传单张图片"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型'}), 400
    
    result, error = save_upload_file(file)
    if error:
        return jsonify(error), 400
    return jsonify(result)


@upload_bp.route('/api/upload/batch', methods=['POST'])
@login_required
def upload_batch():
    """批量上传图片"""
    if 'files' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    files = request.files.getlist('files')
    results = []
    
    for file in files:
        if file.filename == '' or not allowed_file(file.filename):
            continue
        
        result, error = save_upload_file(file)
        if not error:
            results.append(result)
    
    return jsonify(results)


@upload_bp.route('/api/validate-url', methods=['POST'])
@login_required
def validate_image_url():
    """验证图片URL是否可用（逐跳复查，防 SSRF）"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': '缺少URL'}), 400
    
    status_code, content_type, final_url, error = fetch_image_url_safe(url)
    if error:
        return jsonify({'valid': False, 'error': error}), 400
    
    if status_code == 200 and 'image' in (content_type or ''):
        return jsonify({
            'valid': True,
            'url': final_url or url,
            'content_type': content_type
        })
    else:
        return jsonify({
            'valid': False,
            'error': 'URL不是有效的图片'
        })
