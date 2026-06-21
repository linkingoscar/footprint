"""
足迹 - 图片上传 API 蓝图
"""
import requests as http_requests
from flask import Blueprint, request, jsonify

from backend.helpers import allowed_file, save_upload_file, _is_safe_url

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/api/upload', methods=['POST'])
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
        return jsonify(error), 500
    return jsonify(result)


@upload_bp.route('/api/upload/batch', methods=['POST'])
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
def validate_image_url():
    """验证图片URL是否可用"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': '缺少URL'}), 400
    
    if not _is_safe_url(url):
        return jsonify({'valid': False, 'error': '不允许访问内网地址'}), 400
    
    try:
        response = http_requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code in (403, 405) or not response.headers.get('Content-Type'):
            response = http_requests.get(url, timeout=8, stream=True)
        content_type = response.headers.get('Content-Type', '')
        
        if response.status_code == 200 and 'image' in content_type:
            return jsonify({
                'valid': True,
                'url': url,
                'content_type': content_type
            })
        else:
            return jsonify({
                'valid': False,
                'error': 'URL不是有效的图片'
            })
    except http_requests.Timeout:
        return jsonify({'valid': False, 'error': '请求超时'})
    except http_requests.ConnectionError:
        return jsonify({'valid': False, 'error': '无法连接到目标地址'})
    except Exception:
        return jsonify({'valid': False, 'error': '验证失败'})
