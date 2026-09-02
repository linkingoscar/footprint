"""
pytest 共享 fixtures 配置
"""
import os
import sys
import uuid
import json
import base64
import io
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend import app as app_module
from backend import database as database_module
from backend import helpers as helpers_module

app = app_module.app

PNG_1PX = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


def png_file(filename='test.png'):
    return io.BytesIO(PNG_1PX), filename


def register_user(client, username, password='testpass123'):
    resp = client.post(
        '/api/auth/register',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json'
    )
    assert resp.status_code == 201, f'注册失败: {resp.status_code} {resp.data}'
    token = json.loads(resp.data)['token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """创建测试客户端(每个测试独立 tmp_path 数据库与上传目录)"""
    app.config['TESTING'] = True
    upload_dir = str(tmp_path / 'uploads')

    monkeypatch.setattr(helpers_module, 'METADATA_FILE', str(tmp_path / 'records.json'))
    monkeypatch.setattr(helpers_module, 'UPLOAD_FOLDER', upload_dir)
    monkeypatch.setattr(app_module, 'UPLOAD_FOLDER', upload_dir)

    monkeypatch.setattr(database_module, 'RUNTIME_CONFIG_FILE', str(tmp_path / 'runtime_config.json'))
    monkeypatch.setenv('DB_TYPE', 'sqlite')
    monkeypatch.setenv('DB_NAME', str(tmp_path / 'test.db'))
    os.makedirs(upload_dir, exist_ok=True)

    for limiter in app.extensions.get('limiter', set()):
        limiter.enabled = False

    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_header(client):
    """注册一个独立测试用户并返回认证头。"""
    return register_user(client, f'user_{uuid.uuid4().hex[:12]}')


@pytest.fixture
def sample_record():
    """示例记录数据"""
    return {
        'mode': 'travel',
        'title': '北京旅行',
        'description': '参观了天安门和故宫',
        'location': '北京市天安门广场',
        'latitude': 39.9042,
        'longitude': 116.4074,
        'date': '2024-01-15',
        'images': ['data:image/jpeg;base64,/9j/4AAQSkZJRg==']
    }
