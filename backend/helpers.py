"""
足迹 - 共享辅助函数与常量
从 backend/app.py 提取，供各路由蓝图共用。
"""

import os
import uuid
import ipaddress
import urllib.parse
from datetime import datetime
from werkzeug.utils import secure_filename

from backend.exif_extractor import extract_gps_from_image, get_image_info, extract_datetime_from_image
from backend.database import create_storage, create_record_store, get_storage_config, load_runtime_config, save_runtime_config

# ────────────────── 常量 ──────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'heic', 'heif'}
METADATA_FILE = os.path.join(BASE_DIR, 'records.json')
STORAGE_PROVIDER = os.environ.get('STORAGE_PROVIDER', 'local')
DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')

AMAP_KEY = os.environ.get('AMAP_KEY', '')
MAP_ENV_KEYS = {
    'amap': ('AMAP_KEY', 'amapKey', ''),
    'baidu': ('BAIDU_MAP_KEY', 'baiduKey', ''),
    'tencent': ('TENCENT_MAP_KEY', 'tencentKey', ''),
    'bing': ('BING_MAP_KEY', 'bingKey', ''),
}

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

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ────────────────── 存储 & 配置 ──────────────────

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


# ────────────────── 分页 ──────────────────

def paginate_list(items: list, page: int = 1, per_page: int = 20) -> dict:
    """对列表进行分页，返回分页结果字典。"""
    total = len(items)
    per_page = min(per_page, 100)  # 最大100条
    per_page = max(per_page, 1)
    page = max(page, 1)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    start = (page - 1) * per_page
    end = start + per_page
    return {
        'items': items[start:end],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        }
    }


# ────────────────── 记录操作 ──────────────────

def load_records(mode=None, owner_id=None):
    """加载记录数据（可按用户过滤）"""
    return get_record_store().list(mode, owner_id)


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


# ────────────────── 配置脱敏 ──────────────────

def redact_config(config):
    """返回不泄漏密钥值的配置摘要。"""
    redacted = {}
    for key, value in config.items():
        if key in SECRET_KEYS and value:
            redacted[key] = '***'
        else:
            redacted[key] = value
    return redacted


# ────────────────── 安全 ──────────────────

def _is_safe_url(url: str) -> bool:
    """检查 URL 是否安全（非内网地址）。

    同时检查主机名与解析出的 IP（防 DNS 反查绕过）：
    - 拒绝私有、回环、链路本地、保留、组播地址；
    - 拒绝指向上述地址的域名解析结果。
    """
    import socket
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # 禁止常见内网主机名
        blocked_hosts = {'localhost', '127.0.0.1', '0.0.0.0', '[::1]', 'metadata.google.internal'}
        if hostname.lower() in blocked_hosts:
            return False

        def _ip_unsafe(ip_str: str) -> bool:
            try:
                ip = ipaddress.ip_address(ip_str.split('%')[0])
                return (ip.is_private or ip.is_loopback or ip.is_link_local
                        or ip.is_reserved or ip.is_multicast or ip.is_unspecified)
            except ValueError:
                return False

        # 主机名本身就是 IP：直接检查
        try:
            ip = ipaddress.ip_address(hostname)
            return not _ip_unsafe(hostname)
        except ValueError:
            pass

        # 域名：解析全部 A/AAAA 记录，任一命中内网地址即拒绝
        try:
            infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        except OSError:
            return False
        if not infos:
            return False
        for info in infos:
            if _ip_unsafe(info[4][0]):
                return False
        return True
    except Exception:
        return False


def fetch_image_url_safe(url: str, timeout: int = 8, max_redirects: int = 5):
    """按安全规则请求图片 URL，手动跟随重定向并逐跳复查目标。

    返回 (status_code, content_type, final_url, error)；error 非空表示拒绝/失败。
    相比 requests 自动跟随，这里会在每一跳后重新执行 _is_safe_url 检查，
    防止重定向链被用于 SSRF。
    """
    import requests as http_requests
    current_url = url
    session = http_requests.Session()
    session.max_redirects = 0
    for _ in range(max_redirects + 1):
        if not _is_safe_url(current_url):
            return None, None, None, '不允许访问内网地址'
        try:
            resp = session.get(
                current_url,
                timeout=timeout,
                stream=True,
                allow_redirects=False,
                headers={'User-Agent': 'Mozilla/5.0 (Footprint)'}
            )
        except http_requests.Timeout:
            return None, None, None, '请求超时'
        except http_requests.ConnectionError:
            return None, None, None, '无法连接到目标地址'
        except Exception:
            return None, None, None, '验证失败'
        if resp.is_redirect:
            location = resp.headers.get('Location')
            if not location:
                return None, None, None, '无效的重定向响应'
            current_url = urllib.parse.urljoin(current_url, location)
            resp.close()
            continue
        content_type = resp.headers.get('Content-Type', '')
        return resp.status_code, content_type, current_url, None
    return None, None, None, '重定向次数过多'
