"""
足迹 - 记录你的美好生活
后端API服务
"""

import os
import json
import uuid
import csv
import io
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

from backend.exif_extractor import extract_gps_from_image, get_image_info, extract_datetime_from_image
from backend.database import create_storage, create_record_store, get_storage_config, load_runtime_config, save_runtime_config

app = Flask(__name__)
CORS(app)

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'heic', 'heif'}
METADATA_FILE = os.path.join(BASE_DIR, 'records.json')
STORAGE_PROVIDER = os.environ.get('STORAGE_PROVIDER', 'local')
DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')

# 高德API配置
AMAP_KEY = os.environ.get('AMAP_KEY', '')
MAP_ENV_KEYS = {
    'amap': ('AMAP_KEY', 'amapKey', ''),
    'baidu': ('BAIDU_MAP_KEY', 'baiduKey', ''),
    'tencent': ('TENCENT_MAP_KEY', 'tencentKey', ''),
    'bing': ('BING_MAP_KEY', 'bingKey', ''),
}

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_record_store():
    """获取记录存储实例。"""
    if not create_record_store:
        raise RuntimeError('数据库模块不可用')
    return create_record_store(METADATA_FILE)

def get_runtime_config():
    if not load_runtime_config:
        return {}
    return load_runtime_config()

def get_storage_provider():
    if get_storage_config:
        return get_storage_config().get('provider', STORAGE_PROVIDER)
    return STORAGE_PROVIDER

def get_map_provider():
    runtime = get_runtime_config()
    provider = runtime.get('mapProvider') or os.environ.get('MAP_PROVIDER') or 'amap'
    return provider if provider in MAP_ENV_KEYS else 'amap'

def get_map_key(provider=None):
    provider = provider or get_map_provider()
    env_key, runtime_key, default_value = MAP_ENV_KEYS.get(provider, MAP_ENV_KEYS['amap'])
    runtime = get_runtime_config()
    return os.environ.get(env_key) or runtime.get(runtime_key) or default_value

def map_key_configured(provider=None):
    provider = provider or get_map_provider()
    key = get_map_key(provider)
    return bool(key and key != MAP_ENV_KEYS.get(provider, ('', '', ''))[2])

def load_records(mode=None):
    """加载记录数据"""
    return get_record_store().list(mode)

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_float(value):
    """安全转换浮点数"""
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def parse_int(value):
    """安全转换整数"""
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def save_upload_file(file):
    """保存上传文件，提取图片信息，并按配置写入本地或云存储。"""
    original_name = secure_filename(file.filename or '')
    ext = original_name.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    gps = extract_gps_from_image(filepath) or {}
    image_info = get_image_info(filepath) or {}
    date_taken = extract_datetime_from_image(filepath)
    url = f'/uploads/{filename}'
    storage_key = filename
    storage_provider = get_storage_provider()

    if storage_provider != 'local':
        if not create_storage:
            if os.path.exists(filepath):
                os.remove(filepath)
            return None, {'error': '云存储模块不可用'}
        try:
            storage = create_storage()
            url = storage.upload(filepath, filename)
        except Exception as exc:
            if os.path.exists(filepath):
                os.remove(filepath)
            return None, {'error': f'云存储上传失败: {exc}'}
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    return {
        'url': url,
        'filename': filename,
        'original_name': original_name,
        'storage_provider': storage_provider,
        'storage_key': storage_key,
        'latitude': gps.get('latitude'),
        'longitude': gps.get('longitude'),
        'date_taken': date_taken,
        'exif': gps,
        'image_info': image_info
    }, None

def delete_record_assets(record):
    """删除记录关联的本地或云端图片资源。"""
    for image_url in record.get('images', []):
        if '/uploads/' in image_url:
            filename = image_url.rsplit('/uploads/', 1)[1]
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

    for image_meta in record.get('metadata', {}).get('images', []):
        storage_key = image_meta.get('storage_key') or image_meta.get('filename')
        storage_provider = image_meta.get('storage_provider', 'local')
        if not storage_key or storage_provider == 'local':
            continue
        try:
            if create_storage:
                create_storage(storage_provider).delete(storage_key)
        except Exception:
            # 记录删除不应因远端文件已不存在而失败。
            pass

def normalize_record_payload(data, record_id=None):
    """把前端/导入数据规范化为记录存储结构。"""
    now = datetime.now().isoformat()
    return {
        'id': record_id or data.get('id') or uuid.uuid4().hex,
        'mode': data.get('mode', 'travel'),
        'title': data.get('title', '未命名记录'),
        'description': data.get('description', ''),
        'location': data.get('location'),
        'latitude': parse_float(data.get('latitude')),
        'longitude': parse_float(data.get('longitude')),
        'date': data.get('date') or now[:10],
        'images': data.get('images', []),
        'rating': parse_int(data.get('rating')),
        'price': parse_float(data.get('price')),
        'tags': data.get('tags', []),
        'metadata': data.get('metadata', {}),
        'createdAt': data.get('createdAt') or now,
        'updatedAt': data.get('updatedAt')
    }

# ========== 页面路由 ==========

@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory(FRONTEND_DIR, filename)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """提供上传的图片"""
    return send_from_directory(UPLOAD_FOLDER, filename)

# ========== 记录API ==========

@app.route('/api/records', methods=['GET'])
def get_records():
    """获取记录列表"""
    mode = request.args.get('mode')  # travel, food, love
    return jsonify(load_records(mode))

@app.route('/api/records/<record_id>', methods=['GET'])
def get_record(record_id):
    """获取单条记录"""
    record = get_record_store().get(record_id)
    
    if not record:
        return jsonify({'error': '记录不存在'}), 404
    
    return jsonify(record)

@app.route('/api/records', methods=['POST'])
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

@app.route('/api/records/import', methods=['POST'])
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

@app.route('/api/records', methods=['DELETE'])
def delete_records():
    """清空全部记录。"""
    store = get_record_store()
    records = store.list()
    for record in records:
        delete_record_assets(record)
        store.delete(record.get('id'))
    return jsonify({'message': '清空成功', 'count': len(records)})

@app.route('/api/records/<record_id>', methods=['PUT'])
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

@app.route('/api/records/<record_id>', methods=['DELETE'])
def delete_record(record_id):
    """删除记录"""
    store = get_record_store()
    record = store.get(record_id)
    
    if not record:
        return jsonify({'error': '记录不存在'}), 404
    
    delete_record_assets(record)
    
    store.delete(record_id)
    
    return jsonify({'message': '删除成功'})

# ========== 图片上传API ==========

@app.route('/api/upload', methods=['POST'])
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

@app.route('/api/upload/batch', methods=['POST'])
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

# ========== 图床URL验证 ==========

@app.route('/api/validate-url', methods=['POST'])
def validate_image_url():
    """验证图片URL是否可用"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': '缺少URL'}), 400
    
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code in (403, 405) or not response.headers.get('Content-Type'):
            response = requests.get(url, timeout=8, stream=True)
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
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        })

# ========== 运行时配置API ==========

CONFIG_KEYS = {
    'apiBase',
    'mapProvider', 'amapKey', 'baiduKey', 'tencentKey', 'bingKey',
    'storageProvider',
    'aliyunAccessKey', 'aliyunSecretKey', 'aliyunBucket', 'aliyunEndpoint', 'aliyunDomain',
    'tencentSecretId', 'tencentSecretKey', 'tencentBucket', 'tencentRegion', 'tencentDomain',
    'qiniuAccessKey', 'qiniuSecretKey', 'qiniuBucket', 'qiniuDomain',
    'awsAccessKey', 'awsSecretKey', 'awsBucket', 'awsRegion', 'awsDomain',
    'gcpProjectId', 'gcpBucket', 'gcpCredentials',
    'azureAccountName', 'azureAccountKey', 'azureContainer',
}

SECRET_KEYS = {
    'amapKey', 'baiduKey', 'tencentKey', 'bingKey',
    'aliyunAccessKey', 'aliyunSecretKey',
    'tencentSecretId', 'tencentSecretKey',
    'qiniuAccessKey', 'qiniuSecretKey',
    'awsAccessKey', 'awsSecretKey',
    'gcpCredentials',
    'azureAccountKey',
}

def redact_config(config):
    """返回不泄漏密钥值的配置摘要。"""
    redacted = {}
    for key, value in config.items():
        if key in SECRET_KEYS and value:
            redacted[key] = '***'
        else:
            redacted[key] = value
    return redacted

@app.route('/api/config', methods=['GET', 'POST'])
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

# ========== 地理编码API ==========

@app.route('/api/geocode', methods=['GET'])
def geocode():
    """地理编码：地址 -> 坐标"""
    address = request.args.get('address')
    if not address:
        return jsonify({'error': '缺少地址参数'}), 400

    provider = get_map_provider()
    key = get_map_key(provider)
    if not map_key_configured(provider):
        return jsonify({'success': False, 'error': f'{provider} 地图 API Key 未配置'}), 400

    try:
        if provider == 'baidu':
            response = requests.get('https://api.map.baidu.com/geocoding/v3/', params={
                'ak': key,
                'address': address,
                'output': 'json'
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0 and data.get('result'):
                result = data['result']
                location = result['location']
                return jsonify({
                    'success': True,
                    'provider': provider,
                    'latitude': float(location['lat']),
                    'longitude': float(location['lng']),
                    'formatted_address': result.get('formatted_address') or address,
                    'province': '',
                    'city': '',
                    'district': ''
                })
            return jsonify({'success': False, 'provider': provider, 'error': data.get('message') or '未找到结果'})

        if provider == 'tencent':
            response = requests.get('https://apis.map.qq.com/ws/geocoder/v1/', params={
                'key': key,
                'address': address
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0 and data.get('result'):
                result = data['result']
                location = result['location']
                components = result.get('address_components', {})
                return jsonify({
                    'success': True,
                    'provider': provider,
                    'latitude': float(location['lat']),
                    'longitude': float(location['lng']),
                    'formatted_address': result.get('title') or address,
                    'province': components.get('province', ''),
                    'city': components.get('city', ''),
                    'district': components.get('district', '')
                })
            return jsonify({'success': False, 'provider': provider, 'error': data.get('message') or '未找到结果'})

        if provider == 'bing':
            response = requests.get('https://dev.virtualearth.net/REST/v1/Locations', params={
                'key': key,
                'q': address,
                'maxResults': 1
            }, timeout=5)
            data = response.json()
            resources = data.get('resourceSets', [{}])[0].get('resources', [])
            if resources:
                result = resources[0]
                lat, lng = result['point']['coordinates']
                addr = result.get('address', {})
                return jsonify({
                    'success': True,
                    'provider': provider,
                    'latitude': float(lat),
                    'longitude': float(lng),
                    'formatted_address': addr.get('formattedAddress') or result.get('name') or address,
                    'province': addr.get('adminDistrict', ''),
                    'city': addr.get('locality', ''),
                    'district': addr.get('adminDistrict2', '')
                })
            return jsonify({'success': False, 'provider': provider, 'error': '未找到结果'})

        url = 'https://restapi.amap.com/v3/geocode/geo'
        params = {
            'key': key,
            'address': address,
            'output': 'JSON'
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data['status'] == '1' and data['geocodes']:
            geocode = data['geocodes'][0]
            location = geocode['location'].split(',')
            return jsonify({
                'success': True,
                'provider': provider,
                'latitude': float(location[1]),
                'longitude': float(location[0]),
                'formatted_address': geocode['formatted_address'],
                'province': geocode.get('province', ''),
                'city': geocode.get('city', ''),
                'district': geocode.get('district', '')
            })
        else:
            return jsonify({'success': False, 'provider': provider, 'error': '未找到结果'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reverse-geocode', methods=['GET'])
def reverse_geocode():
    """逆地理编码：坐标 -> 地址"""
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    
    if not lat or not lng:
        return jsonify({'error': '缺少坐标参数'}), 400
    
    provider = get_map_provider()
    key = get_map_key(provider)
    if not map_key_configured(provider):
        return jsonify({'success': False, 'error': f'{provider} 地图 API Key 未配置'}), 400

    try:
        if provider == 'baidu':
            response = requests.get('https://api.map.baidu.com/reverse_geocoding/v3/', params={
                'ak': key,
                'location': f'{lat},{lng}',
                'output': 'json'
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0 and data.get('result'):
                result = data['result']
                components = result.get('addressComponent', {})
                return jsonify({
                    'success': True,
                    'provider': provider,
                    'formatted_address': result.get('formatted_address', ''),
                    'province': components.get('province', ''),
                    'city': components.get('city', ''),
                    'district': components.get('district', '')
                })
            return jsonify({'success': False, 'provider': provider, 'error': data.get('message') or '未找到结果'})

        if provider == 'tencent':
            response = requests.get('https://apis.map.qq.com/ws/geocoder/v1/', params={
                'key': key,
                'location': f'{lat},{lng}'
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0 and data.get('result'):
                result = data['result']
                components = result.get('address_component', {})
                return jsonify({
                    'success': True,
                    'provider': provider,
                    'formatted_address': result.get('address', ''),
                    'province': components.get('province', ''),
                    'city': components.get('city', ''),
                    'district': components.get('district', '')
                })
            return jsonify({'success': False, 'provider': provider, 'error': data.get('message') or '未找到结果'})

        if provider == 'bing':
            response = requests.get(f'https://dev.virtualearth.net/REST/v1/Locations/{lat},{lng}', params={
                'key': key,
                'maxResults': 1
            }, timeout=5)
            data = response.json()
            resources = data.get('resourceSets', [{}])[0].get('resources', [])
            if resources:
                addr = resources[0].get('address', {})
                return jsonify({
                    'success': True,
                    'provider': provider,
                    'formatted_address': addr.get('formattedAddress', ''),
                    'province': addr.get('adminDistrict', ''),
                    'city': addr.get('locality', ''),
                    'district': addr.get('adminDistrict2', '')
                })
            return jsonify({'success': False, 'provider': provider, 'error': '未找到结果'})

        url = 'https://restapi.amap.com/v3/geocode/regeo'
        params = {
            'key': key,
            'location': f'{lng},{lat}',
            'output': 'JSON'
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data['status'] == '1':
            regeocode = data['regeocode']
            return jsonify({
                'success': True,
                'provider': provider,
                'formatted_address': regeocode['formatted_address'],
                'province': regeocode['addressComponent'].get('province', ''),
                'city': regeocode['addressComponent'].get('city', ''),
                'district': regeocode['addressComponent'].get('district', '')
            })
        else:
            return jsonify({'success': False, 'provider': provider, 'error': '未找到结果'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search-poi', methods=['GET'])
def search_poi():
    """搜索POI兴趣点"""
    keywords = request.args.get('keywords')
    city = request.args.get('city', '')
    
    if not keywords:
        return jsonify({'error': '缺少搜索关键词'}), 400
    
    provider = get_map_provider()
    key = get_map_key(provider)
    if not map_key_configured(provider):
        return jsonify({'success': False, 'error': f'{provider} 地图 API Key 未配置'}), 400

    try:
        if provider == 'baidu':
            response = requests.get('https://api.map.baidu.com/place/v2/search', params={
                'ak': key,
                'query': keywords,
                'region': city or '全国',
                'output': 'json',
                'page_size': 10
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0:
                pois = []
                for poi in data.get('results', []):
                    location = poi.get('location') or {}
                    if 'lat' not in location or 'lng' not in location:
                        continue
                    pois.append({
                        'name': poi.get('name', ''),
                        'address': poi.get('address', ''),
                        'latitude': float(location['lat']),
                        'longitude': float(location['lng']),
                        'type': poi.get('tag', '')
                    })
                return jsonify({'success': True, 'provider': provider, 'pois': pois})
            return jsonify({'success': False, 'provider': provider, 'error': data.get('message') or '未找到结果'})

        if provider == 'tencent':
            response = requests.get('https://apis.map.qq.com/ws/place/v1/search', params={
                'key': key,
                'keyword': keywords,
                'boundary': f"region({city or '全国'},0)",
                'page_size': 10
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0:
                pois = []
                for poi in data.get('data', []):
                    location = poi.get('location') or {}
                    if 'lat' not in location or 'lng' not in location:
                        continue
                    pois.append({
                        'name': poi.get('title', ''),
                        'address': poi.get('address', ''),
                        'latitude': float(location['lat']),
                        'longitude': float(location['lng']),
                        'type': poi.get('category', '')
                    })
                return jsonify({'success': True, 'provider': provider, 'pois': pois})
            return jsonify({'success': False, 'provider': provider, 'error': data.get('message') or '未找到结果'})

        if provider == 'bing':
            response = requests.get('https://dev.virtualearth.net/REST/v1/Locations', params={
                'key': key,
                'q': keywords,
                'maxResults': 10
            }, timeout=5)
            data = response.json()
            pois = []
            for item in data.get('resourceSets', [{}])[0].get('resources', []):
                coordinates = item.get('point', {}).get('coordinates')
                if not coordinates or len(coordinates) < 2:
                    continue
                addr = item.get('address', {})
                pois.append({
                    'name': item.get('name', ''),
                    'address': addr.get('formattedAddress', ''),
                    'latitude': float(coordinates[0]),
                    'longitude': float(coordinates[1]),
                    'type': item.get('entityType', '')
                })
            return jsonify({'success': True, 'provider': provider, 'pois': pois})

        url = 'https://restapi.amap.com/v3/place/text'
        params = {
            'key': key,
            'keywords': keywords,
            'city': city,
            'output': 'JSON',
            'offset': 10
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data['status'] == '1':
            pois = []
            for poi in data.get('pois', []):
                location = poi['location'].split(',')
                pois.append({
                    'name': poi['name'],
                    'address': poi.get('address', ''),
                    'latitude': float(location[1]),
                    'longitude': float(location[0]),
                    'type': poi.get('type', '')
                })
            return jsonify({'success': True, 'provider': provider, 'pois': pois})
        else:
            return jsonify({'success': False, 'provider': provider, 'error': '未找到结果'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== 统计API ==========

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    records = load_records()
    
    monthly = {}
    places = sorted(set(r.get('location') for r in records if r.get('location')))
    for record in records:
        date = record.get('date') or record.get('createdAt', '')[:10]
        if date:
            month = date[:7]
            monthly[month] = monthly.get(month, 0) + 1

    return jsonify({
        'total_records': len(records),
        'travel_count': len([r for r in records if r.get('mode') == 'travel']),
        'food_count': len([r for r in records if r.get('mode') == 'food']),
        'love_count': len([r for r in records if r.get('mode') == 'love']),
        'total_photos': sum(len(r.get('images', [])) for r in records),
        'total_places': len(places),
        'places': places,
        'monthly_trend': monthly,
        'storage_provider': get_storage_provider()
    })

# ========== 健康检查 ==========

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'map_provider': get_map_provider(),
        'map_configured': map_key_configured(),
        'storage_provider': get_storage_provider(),
        'db_type': os.environ.get('DB_TYPE', DB_TYPE)
    })

# ========== 数据导出 API ==========

@app.route('/api/export/gpx', methods=['GET'])
def export_gpx():
    """导出GPX格式轨迹"""
    records = load_records()
    located = [r for r in records if r.get('latitude') and r.get('longitude')]
    located.sort(key=lambda r: r.get('date', '') or r.get('createdAt', ''))
    
    gpx_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    gpx_parts.append('<gpx version="1.1" creator="足迹 - 记录你的美好生活">')
    gpx_parts.append(f'  <metadata><name>足迹导出</name><time>{datetime.now().isoformat()}</time></metadata>')
    gpx_parts.append('  <trk><name>旅行轨迹</name><trkseg>')
    for r in located:
        date = r.get('date', '')
        title = (r.get('title', '') or '').replace('&', '&amp;').replace('<', '&lt;')
        gpx_parts.append(f'    <trkpt lat="{r["latitude"]}" lon="{r["longitude"]}"><time>{date}</time><name>{title}</name></trkpt>')
    gpx_parts.append('  </trkseg></trk>')
    gpx_parts.append('</gpx>')
    
    content = '\n'.join(gpx_parts)
    return Response(content, mimetype='application/gpx+xml',
                    headers={'Content-Disposition': f'attachment; filename=footprint_{datetime.now().strftime("%Y%m%d")}.gpx'})

@app.route('/api/export/geojson', methods=['GET'])
def export_geojson():
    """导出GeoJSON格式"""
    records = load_records()
    features = []
    for r in records:
        if r.get('latitude') and r.get('longitude'):
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [r['longitude'], r['latitude']]},
                'properties': {
                    'id': r.get('id'),
                    'title': r.get('title', ''),
                    'description': r.get('description', ''),
                    'location': r.get('location', ''),
                    'date': r.get('date', ''),
                    'mode': r.get('mode', ''),
                    'rating': r.get('rating'),
                    'image_count': len(r.get('images', []))
                }
            })
    
    geojson = {'type': 'FeatureCollection', 'features': features}
    content = json.dumps(geojson, ensure_ascii=False, indent=2)
    return Response(content, mimetype='application/geo+json',
                    headers={'Content-Disposition': f'attachment; filename=footprint_{datetime.now().strftime("%Y%m%d")}.geojson'})

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """导出CSV格式"""
    records = load_records()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'mode', 'title', 'description', 'location', 'latitude', 'longitude', 'date', 'rating', 'price', 'image_count', 'created_at'])
    for r in records:
        writer.writerow([
            r.get('id', ''),
            r.get('mode', ''),
            r.get('title', ''),
            r.get('description', ''),
            r.get('location', ''),
            r.get('latitude', ''),
            r.get('longitude', ''),
            r.get('date', ''),
            r.get('rating', ''),
            r.get('price', ''),
            len(r.get('images', [])),
            r.get('createdAt', '')
        ])
    
    content = output.getvalue()
    return Response(content, mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=footprint_{datetime.now().strftime("%Y%m%d")}.csv'})

# ========== 费用追踪 API ==========

EXPENSES_FILE = os.path.join(BASE_DIR, 'expenses.json')

def _load_expenses():
    if os.path.exists(EXPENSES_FILE):
        try:
            with open(EXPENSES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return []
    return []

def _save_expenses(expenses):
    with open(EXPENSES_FILE, 'w', encoding='utf-8') as f:
        json.dump(expenses, f, ensure_ascii=False, indent=2)

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """获取费用列表"""
    expenses = _load_expenses()
    record_id = request.args.get('record_id')
    if record_id:
        expenses = [e for e in expenses if e.get('record_id') == record_id]
    return jsonify(expenses)

@app.route('/api/expenses', methods=['POST'])
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
        'createdAt': datetime.now().isoformat()
    }
    
    expenses = _load_expenses()
    expenses.insert(0, expense)
    _save_expenses(expenses)
    return jsonify(expense), 201

@app.route('/api/expenses/<expense_id>', methods=['PUT'])
def update_expense(expense_id):
    """更新费用记录"""
    data = request.get_json()
    expenses = _load_expenses()
    for i, e in enumerate(expenses):
        if e.get('id') == expense_id:
            for key in ['category', 'amount', 'description', 'date', 'currency', 'mode', 'record_id']:
                if key in data:
                    expenses[i][key] = data[key] if key != 'amount' else (parse_float(data[key]) or 0)
            _save_expenses(expenses)
            return jsonify(expenses[i])
    return jsonify({'error': '费用不存在'}), 404

@app.route('/api/expenses/<expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    """删除费用记录"""
    expenses = _load_expenses()
    expenses = [e for e in expenses if e.get('id') != expense_id]
    _save_expenses(expenses)
    return jsonify({'message': '删除成功'})

@app.route('/api/expenses/stats', methods=['GET'])
def get_expense_stats():
    """获取费用统计"""
    expenses = _load_expenses()
    total = sum(e.get('amount', 0) for e in expenses)
    
    by_category = {}
    for e in expenses:
        cat = e.get('category', '其他')
        by_category[cat] = by_category.get(cat, 0) + e.get('amount', 0)
    
    by_month = {}
    for e in expenses:
        month = (e.get('date', '') or '')[:7]
        if month:
            by_month[month] = by_month.get(month, 0) + e.get('amount', 0)
    
    by_mode = {}
    for e in expenses:
        mode = e.get('mode', 'travel')
        by_mode[mode] = by_mode.get(mode, 0) + e.get('amount', 0)
    
    return jsonify({
        'total': total,
        'count': len(expenses),
        'by_category': [{'category': k, 'amount': v} for k, v in sorted(by_category.items(), key=lambda x: -x[1])],
        'by_month': [{'month': k, 'amount': v} for k, v in sorted(by_month.items())],
        'by_mode': [{'mode': k, 'amount': v} for k, v in by_mode.items()]
    })

# ========== 城市统计 API ==========

@app.route('/api/cities', methods=['GET'])
def get_cities():
    """从记录中提取城市统计"""
    records = load_records()
    cities = {}
    for r in records:
        loc = r.get('location', '')
        if not loc:
            continue
        # 简单提取城市名
        city = loc
        for sep in ['省', '市', '区', '县', '镇']:
            idx = loc.find(sep)
            if idx > 0:
                city = loc[:idx + len(sep)]
                break
        if city:
            cities[city] = cities.get(city, 0) + 1
    
    return jsonify({
        'cities': [{'name': k, 'count': v} for k, v in sorted(cities.items(), key=lambda x: -x[1])],
        'total_cities': len(cities)
    })

# ========== AI 故事生成 API ==========

@app.route('/api/ai/story', methods=['POST'])
def generate_story():
    """基于记录生成旅行故事（模板方式）"""
    data = request.get_json() or {}
    record_ids = data.get('record_ids', [])
    style = data.get('style', 'travel')
    
    store = get_record_store()
    if record_ids:
        records = [store.get(rid) for rid in record_ids if store.get(rid)]
    else:
        records = load_records()[:10]
    
    if not records:
        return jsonify({'error': '没有记录'}), 400
    
    story_parts = []
    places = [r.get('location', '') for r in records if r.get('location')]
    dates = [r.get('date', '') for r in records if r.get('date')]
    
    if style == 'travel':
        story_parts.append(f'🗺️ 这是一段关于 {len(records)} 个足迹的旅行故事。')
        if dates:
            story_parts.append(f'从 {min(dates)} 到 {max(dates)}，')
        if places:
            story_parts.append(f'足迹遍布 {"、".join(places[:5])} 等地。\n')
        for r in records[:8]:
            if r.get('title'):
                loc = r.get('location', '这里')
                desc = r.get('description', '') or '留下了美好的回忆'
                story_parts.append(f'📍 {r.get("date", "")} · {loc}')
                story_parts.append(f'   {r.get("title")} — {desc}\n')
    elif style == 'romantic':
        story_parts.append(f'💕 这是一段 {len(records)} 个甜蜜瞬间的爱情故事。\n')
        for r in records[:8]:
            if r.get('title'):
                story_parts.append(f'📅 {r.get("date", "")} · {r.get("location", "")}')
                story_parts.append(f'   {r.get("description", r.get("title"))}\n')
    elif style == 'foodie':
        story_parts.append(f'🍜 {len(records)} 道美食的味蕾之旅。\n')
        for r in records[:8]:
            if r.get('title'):
                rating = '⭐' * (r.get('rating', 0) or 0)
                price = f'¥{r.get("price", "")}' if r.get('price') else ''
                story_parts.append(f'🍽️ {r.get("title")} {rating} {price}')
                story_parts.append(f'   {r.get("description", "")}\n')
    
    return jsonify({'story': '\n'.join(story_parts)})

# ========== 批量照片导入 API ==========

@app.route('/api/upload/batch-photos', methods=['POST'])
def upload_batch_photos():
    """批量上传照片并自动提取EXIF"""
    if 'files' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    files = request.files.getlist('files')
    mode = request.form.get('mode', 'travel')
    title = request.form.get('title', '批量导入')
    
    results = []
    for file in files:
        if file.filename == '' or not allowed_file(file.filename):
            continue
        result, error = save_upload_file(file)
        if not error:
            results.append(result)
    
    # 有GPS数据的自动创建记录
    located = [r for r in results if r.get('latitude')]
    record = None
    if located:
        record = {
            'id': uuid.uuid4().hex,
            'mode': mode,
            'title': title,
            'description': f'批量导入 {len(results)} 张照片',
            'latitude': sum(r['latitude'] for r in located) / len(located),
            'longitude': sum(r['longitude'] for r in located) / len(located),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'images': [r['url'] for r in results],
            'tags': [],
            'metadata': {'images': results}
        }
        get_record_store().create(record)
    
    return jsonify({
        'total': len(results),
        'located': len(located),
        'record_created': record is not None,
        'record': record,
        'files': results
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    print("=" * 50)
    print("Footprint - 记录你的美好生活")
    print("=" * 50)
    print(f"访问 http://localhost:{port} 打开应用")
    print(f"地图服务: {get_map_provider()} ({'已配置' if map_key_configured() else '未配置'})")
    print("=" * 50)
    app.run(debug=debug, port=port, use_reloader=False)
